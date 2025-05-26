import json
import logging
import os
import boto3
import datetime
import uuid # For generating dummy event IDs

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize Boto3 clients
dynamodb = boto3.resource('dynamodb')

# Environment variables for table names
APPOINTMENTS_TABLE_NAME = os.environ.get('APPOINTMENTS_TABLE_NAME')
SERVICES_TABLE_NAME = os.environ.get('SERVICES_TABLE_NAME')
LOCATIONS_TABLE_NAME = os.environ.get('LOCATIONS_TABLE_NAME')

# --- Stubbed Google Calendar API Functions ---
def stub_create_google_calendar_event(calendar_id, event_title, event_description, start_time_iso, end_time_iso):
    """
    Stub function to simulate creating a Google Calendar event.
    Logs parameters and returns a dummy event ID.
    """
    logger.info(f"[STUB] Creating Google Calendar event in calendar '{calendar_id}'")
    logger.info(f"[STUB] Event Title: {event_title}")
    logger.info(f"[STUB] Event Description: {event_description}")
    logger.info(f"[STUB] Start Time: {start_time_iso}")
    logger.info(f"[STUB] End Time: {end_time_iso}")
    
    # Simulate API call delay (optional)
    # import time
    # time.sleep(0.1) 
    
    dummy_event_id = f"stub_event_{uuid.uuid4()}"
    logger.info(f"[STUB] Google Calendar event created successfully. Event ID: {dummy_event_id}")
    return dummy_event_id

def stub_delete_google_calendar_event(calendar_id, event_id):
    """
    Stub function to simulate deleting a Google Calendar event.
    Logs parameters and returns a success status.
    """
    logger.info(f"[STUB] Deleting Google Calendar event '{event_id}' from calendar '{calendar_id}'")
    # Simulate API call delay (optional)
    # import time
    # time.sleep(0.1)
    logger.info(f"[STUB] Google Calendar event '{event_id}' deleted successfully.")
    return True
# --- End Stubbed Functions ---

def handle_create_event_sqs(message_data):
    """
    Handles the CREATE_EVENT action from an SQS message.
    """
    lambda_name = "GoogleCalendarSyncLambda"
    booking_id = message_data.get('bookingId')
    logger.info(f"[{lambda_name}-CREATE_EVENT] Processing for bookingId: {booking_id}")

    required_fields = ['serviceId', 'locationId', 'proposedStartTime', 'proposedEndTime', 
                       'clientName', 'clientEmail'] # clientContact renamed to clientEmail for clarity
    for field in required_fields:
        if field not in message_data:
            logger.error(f"[{lambda_name}-CREATE_EVENT] Missing required field '{field}' in message for bookingId: {booking_id}")
            raise ValueError(f"Missing required field: {field}")

    service_id = message_data['serviceId']
    location_id = message_data['locationId']
    proposed_start_time = message_data['proposedStartTime']
    proposed_end_time = message_data['proposedEndTime']
    client_name = message_data['clientName']
    client_email = message_data['clientEmail'] # Assuming clientContact is email
    notes = message_data.get('notes', '') # Optional field

    # 1. Fetch service details
    try:
        services_table = dynamodb.Table(SERVICES_TABLE_NAME)
        service_response = services_table.get_item(Key={'serviceId': service_id})
        service_item = service_response.get('Item')
        if not service_item:
            logger.error(f"[{lambda_name}-CREATE_EVENT] Service {service_id} not found for bookingId: {booking_id}.")
            raise ValueError(f"Service details not found for serviceId: {service_id}")
        service_name = service_item.get('serviceName', 'Unknown Service')
    except Exception as e:
        logger.error(f"[{lambda_name}-CREATE_EVENT] Error fetching service {service_id} for booking {booking_id}: {e}", exc_info=True)
        raise

    # 2. Fetch location details
    try:
        locations_table = dynamodb.Table(LOCATIONS_TABLE_NAME)
        location_response = locations_table.get_item(Key={'locationId': location_id})
        location_item = location_response.get('Item')
        if not location_item:
            logger.error(f"[{lambda_name}-CREATE_EVENT] Location {location_id} not found for bookingId: {booking_id}.")
            raise ValueError(f"Location details not found for locationId: {location_id}")
        location_name = location_item.get('locationName', 'Unknown Location')
        google_calendar_id_for_location = location_item.get('googleCalendarId')
        if not google_calendar_id_for_location:
            logger.error(f"[{lambda_name}-CREATE_EVENT] googleCalendarId not configured for location {location_id} (booking {booking_id}).")
            raise ValueError(f"googleCalendarId missing for location: {location_id}")
    except Exception as e:
        logger.error(f"[{lambda_name}-CREATE_EVENT] Error fetching location {location_id} for booking {booking_id}: {e}", exc_info=True)
        raise

    # 3. Construct event details
    event_title = f"Appointment: {service_name} for {client_name}"
    event_description = (
        f"Service: {service_name}\n"
        f"Client: {client_name}\n"
        f"Email: {client_email}\n"
        f"Location: {location_name}\n"
        f"Notes: {notes if notes else 'N/A'}\n"
        f"Booking ID: {booking_id}"
    )

    # 4. Call (stubbed) Google Calendar API to create event
    try:
        google_event_id = stub_create_google_calendar_event(
            calendar_id=google_calendar_id_for_location,
            event_title=event_title,
            event_description=event_description,
            start_time_iso=proposed_start_time,
            end_time_iso=proposed_end_time
        )
    except Exception as e: # Catch errors from the stub, though unlikely for a simple stub
        logger.error(f"[{lambda_name}-CREATE_EVENT] Error creating Google Calendar event (stub) for booking {booking_id}: {e}", exc_info=True)
        raise

    # 5. Update AppointmentsTable with googleCalendarEventId
    if google_event_id:
        try:
            appointments_table = dynamodb.Table(APPOINTMENTS_TABLE_NAME)
            updated_at = datetime.datetime.utcnow().isoformat()
            appointments_table.update_item(
                Key={'bookingId': booking_id},
                UpdateExpression="SET googleCalendarEventId = :gcal_id, updatedAt = :ua",
                ExpressionAttributeValues={
                    ':gcal_id': google_event_id,
                    ':ua': updated_at
                }
            )
            logger.info(f"[{lambda_name}-CREATE_EVENT] Booking {booking_id} updated with googleCalendarEventId: {google_event_id}")
        except Exception as e:
            logger.error(f"[{lambda_name}-CREATE_EVENT] Error updating booking {booking_id} with googleCalendarEventId: {e}", exc_info=True)
            # This is a critical error if the event was created but not linked. Consider retry or DLQ.
            raise
    else:
        # Should not happen with the current stub, but good practice for real API
        logger.error(f"[{lambda_name}-CREATE_EVENT] Failed to get googleCalendarEventId for booking {booking_id} from stub.")
        raise Exception("Failed to obtain Google Calendar Event ID from stub.")


def handle_delete_event_sqs(message_data):
    """
    Handles the DELETE_EVENT action from an SQS message.
    """
    lambda_name = "GoogleCalendarSyncLambda"
    booking_id = message_data.get('bookingId') # For logging
    logger.info(f"[{lambda_name}-DELETE_EVENT] Processing for bookingId: {booking_id}")

    required_fields = ['googleCalendarEventId', 'locationId']
    for field in required_fields:
        if field not in message_data:
            logger.error(f"[{lambda_name}-DELETE_EVENT] Missing required field '{field}' in message for bookingId: {booking_id}")
            raise ValueError(f"Missing required field: {field}")

    google_event_id_to_delete = message_data['googleCalendarEventId']
    location_id = message_data['locationId']

    # 1. Fetch location details for googleCalendarId
    try:
        locations_table = dynamodb.Table(LOCATIONS_TABLE_NAME)
        location_response = locations_table.get_item(Key={'locationId': location_id})
        location_item = location_response.get('Item')
        if not location_item:
            logger.error(f"[{lambda_name}-DELETE_EVENT] Location {location_id} not found for bookingId: {booking_id}.")
            raise ValueError(f"Location details not found for locationId: {location_id}")
        google_calendar_id_for_location = location_item.get('googleCalendarId')
        if not google_calendar_id_for_location:
            logger.error(f"[{lambda_name}-DELETE_EVENT] googleCalendarId not configured for location {location_id} (booking {booking_id}).")
            raise ValueError(f"googleCalendarId missing for location: {location_id}")
    except Exception as e:
        logger.error(f"[{lambda_name}-DELETE_EVENT] Error fetching location {location_id} for booking {booking_id}: {e}", exc_info=True)
        raise

    # 2. Call (stubbed) Google Calendar API to delete event
    try:
        stub_delete_google_calendar_event(
            calendar_id=google_calendar_id_for_location,
            event_id=google_event_id_to_delete
        )
        logger.info(f"[{lambda_name}-DELETE_EVENT] Successfully processed delete for event {google_event_id_to_delete} in booking {booking_id}.")
    except Exception as e: # Catch errors from the stub
        logger.error(f"[{lambda_name}-DELETE_EVENT] Error deleting Google Calendar event (stub) {google_event_id_to_delete} for booking {booking_id}: {e}", exc_info=True)
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler for Google Calendar synchronization from SQS.
    Processes messages from an SQS queue.
    """
    lambda_name = "GoogleCalendarSyncLambda"
    logger.info(f"Received SQS event for {lambda_name}: {json.dumps(event)}")

    if not all([APPOINTMENTS_TABLE_NAME, SERVICES_TABLE_NAME, LOCATIONS_TABLE_NAME]):
        logger.fatal(f"[{lambda_name}] Missing one or more critical environment variables for table names. Exiting.")
        # This is a configuration error, returning error to SQS might cause infinite retries if not handled by DLQ.
        # For Lambda, raising an exception after logging is often the best way to signal failure.
        raise EnvironmentError("Missing critical table name environment variables.")

    processed_messages = 0
    failed_messages = 0

    for record in event.get('Records', []):
        try:
            message_body_str = record.get('body')
            if not message_body_str:
                logger.error(f"[{lambda_name}] SQS record missing 'body'. Record: {record}")
                failed_messages += 1
                continue 
            
            logger.info(f"[{lambda_name}] Raw SQS message body: {message_body_str}")
            message_data = json.loads(message_body_str)
            
            action = message_data.get('action')
            booking_id_log = message_data.get('bookingId', 'UnknownBookingID') # For logging before action dispatch

            logger.info(f"[{lambda_name}] Processing action '{action}' for bookingId: {booking_id_log}")

            if action == 'CREATE_EVENT':
                handle_create_event_sqs(message_data)
            elif action == 'DELETE_EVENT':
                handle_delete_event_sqs(message_data)
            else:
                logger.warning(f"[{lambda_name}] Unknown action '{action}' in SQS message for bookingId {booking_id_log}. Message: {json.dumps(message_data)}")
                failed_messages += 1
                continue # Skip to next message
            
            processed_messages += 1
            # If partial batch processing fails, SQS will retry the whole batch by default.
            # Successful messages in a batch should ideally be idempotent or handled carefully.

        except json.JSONDecodeError as e:
            logger.error(f"[{lambda_name}] Failed to decode JSON from SQS message body: {message_body_str}. Error: {e}", exc_info=True)
            failed_messages += 1
        except ValueError as e: # For missing fields or data validation errors
            logger.error(f"[{lambda_name}] Data validation error processing SQS message: {e}. Message body: {message_body_str}", exc_info=True)
            failed_messages += 1
        except Exception as e: # Catch-all for other unexpected errors during processing of a single message
            logger.error(f"[{lambda_name}] Unexpected error processing SQS message: {e}. Message body: {message_body_str}", exc_info=True)
            failed_messages += 1
            # Depending on SQS configuration, this might lead to retries for the message.

    logger.info(f"[{lambda_name}] Processing complete. Processed: {processed_messages}, Failed: {failed_messages}.")

    # For SQS, if any message fails, you might want the Lambda invocation to fail to leverage SQS retry/DLQ.
    # However, standard behavior is that if the handler completes without an exception, SQS considers the batch successful.
    # To signal SQS to retry the entire batch (if ReportBatchItemFailures is not configured on the event source mapping),
    # an exception should be raised if failed_messages > 0.
    # If ReportBatchItemFailures is enabled, then failed messages are returned in a specific format.
    # For simplicity here, we'll log failures. The SQS trigger configuration (batch size, retries, DLQ) is key.
    
    # This lambda currently doesn't return a body, which is fine for SQS triggers if no batch item failure reporting is used.
    # If batch item failure reporting *is* used, the return value needs to be:
    # { "batchItemFailures": [ { "itemIdentifier": "messageIdOfFailedMessage" }, ... ] }
    # For now, assuming no batch item failure reporting or that DLQ handles persistent errors.
    return {
        "status": "completed",
        "processed_messages": processed_messages,
        "failed_messages": failed_messages
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Setup mock environment variables for local testing
    os.environ['APPOINTMENTS_TABLE_NAME'] = "MockAppointmentsTable"
    os.environ['SERVICES_TABLE_NAME'] = "MockServicesTable"
    os.environ['LOCATIONS_TABLE_NAME'] = "MockLocationsTable"

    # Mock Boto3 resources/tables for local testing
    class MockDynamoDBTable:
        def __init__(self, table_name):
            self.table_name = table_name
            self.mock_data = {} # Store mock data here if needed for get_item

        def get_item(self, Key):
            logger.info(f"[MockDynamoDBTable-{self.table_name}] get_item called with Key: {Key}")
            if self.table_name == "MockServicesTable" and Key['serviceId'] == "service123":
                return {"Item": {"serviceId": "service123", "serviceName": "Test Service", "durationMinutes": 60}}
            if self.table_name == "MockLocationsTable" and Key['locationId'] == "locationABC":
                return {"Item": {"locationId": "locationABC", "locationName": "Main Street Clinic", "googleCalendarId": "clinic_main_st@group.calendar.google.com"}}
            if self.table_name == "MockLocationsTable" and Key['locationId'] == "locationXYZ_no_gcal":
                 return {"Item": {"locationId": "locationXYZ_no_gcal", "locationName": "Downtown Branch"}} # No googleCalendarId
            return {"Item": None} # Default to not found

        def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
            logger.info(f"[MockDynamoDBTable-{self.table_name}] update_item called for Key: {Key} with Updates: {ExpressionAttributeValues}")
            return {"Attributes": {"bookingId": Key['bookingId'], **ExpressionAttributeValues}}

    # Monkey patch boto3.resource for local testing
    _original_boto3_resource = boto3.resource
    def mock_boto3_resource(service_name):
        if service_name == 'dynamodb':
            class MockDynamoDBResource:
                def Table(self, table_name):
                    return MockDynamoDBTable(table_name)
            return MockDynamoDBResource()
        return _original_boto3_resource(service_name)
    boto3.resource = mock_boto3_resource
    # Re-initialize global dynamodb client with mock after patching
    dynamodb = boto3.resource('dynamodb')


    # Test SQS CREATE_EVENT
    test_sqs_event_create = {
        "Records": [
            {
                "messageId": "msg1",
                "receiptHandle": "handle1",
                "body": json.dumps({
                    "action": "CREATE_EVENT",
                    "bookingId": "booking789",
                    "serviceId": "service123",
                    "locationId": "locationABC",
                    "proposedStartTime": "2024-09-01T10:00:00Z",
                    "proposedEndTime": "2024-09-01T11:00:00Z",
                    "clientName": "John Doe",
                    "clientEmail": "john.doe@example.com",
                    "notes": "Prefers morning appointments."
                }),
                "attributes": {}, "messageAttributes": {}, "md5OfBody": "", "eventSource": "aws:sqs", "eventSourceARN": "", "awsRegion": "us-east-1"
            }
        ]
    }
    print("\n--- Testing SQS CREATE_EVENT ---")
    response = lambda_handler(test_sqs_event_create, {})
    print(json.dumps(response, indent=2))

    # Test SQS DELETE_EVENT
    test_sqs_event_delete = {
        "Records": [
            {
                "messageId": "msg2",
                "receiptHandle": "handle2",
                "body": json.dumps({
                    "action": "DELETE_EVENT",
                    "bookingId": "booking456", # For logging context
                    "googleCalendarEventId": "evt_some_google_id_to_delete",
                    "locationId": "locationABC"
                }),
                "attributes": {}, "messageAttributes": {}, "md5OfBody": "", "eventSource": "aws:sqs", "eventSourceARN": "", "awsRegion": "us-east-1"
            }
        ]
    }
    print("\n--- Testing SQS DELETE_EVENT ---")
    response = lambda_handler(test_sqs_event_delete, {})
    print(json.dumps(response, indent=2))

    # Test SQS UNKNOWN_ACTION
    test_sqs_event_unknown = {
         "Records": [
            {
                "messageId": "msg3",
                "body": json.dumps({"action": "SOME_OTHER_ACTION", "bookingId": "booking111"}),
            }
        ]
    }
    print("\n--- Testing SQS UNKNOWN_ACTION ---")
    response = lambda_handler(test_sqs_event_unknown, {})
    print(json.dumps(response, indent=2))
    
    # Test SQS message with missing required field for CREATE_EVENT
    test_sqs_create_missing_field = {
        "Records": [
            {
                "messageId": "msg4",
                "body": json.dumps({
                    "action": "CREATE_EVENT", # Missing serviceId
                    "bookingId": "booking000",
                    "locationId": "locationABC",
                    "proposedStartTime": "2024-09-01T10:00:00Z",
                    "proposedEndTime": "2024-09-01T11:00:00Z",
                    "clientName": "Jane Doe",
                    "clientEmail": "jane.doe@example.com"
                }),
            }
        ]
    }
    print("\n--- Testing SQS CREATE_EVENT (Missing Field) ---")
    response = lambda_handler(test_sqs_create_missing_field, {})
    print(json.dumps(response, indent=2))

    # Test SQS message with location missing googleCalendarId for CREATE_EVENT
    test_sqs_create_missing_gcal_id = {
        "Records": [
            {
                "messageId": "msg5",
                "body": json.dumps({
                    "action": "CREATE_EVENT",
                    "bookingId": "booking001",
                    "serviceId": "service123",
                    "locationId": "locationXYZ_no_gcal", # This location mock has no googleCalendarId
                    "proposedStartTime": "2024-09-01T10:00:00Z",
                    "proposedEndTime": "2024-09-01T11:00:00Z",
                    "clientName": "Jim Doe",
                    "clientEmail": "jim.doe@example.com"
                }),
            }
        ]
    }
    print("\n--- Testing SQS CREATE_EVENT (Location missing googleCalendarId) ---")
    response = lambda_handler(test_sqs_create_missing_gcal_id, {})
    print(json.dumps(response, indent=2))

    # Restore original boto3.resource
    boto3.resource = _original_boto3_resource
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"An internal server error occurred in {lambda_name}."})
        }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test events
    test_event_create = {
        "action": "create_event",
        "data": {
            "calendarId": "primary",
            "eventBody": {
                "summary": "Test Event from Lambda",
                "description": "This is a test event.",
                "start": {"dateTime": "2024-09-01T10:00:00-07:00", "timeZone": "America/Los_Angeles"},
                "end": {"dateTime": "2024-09-01T11:00:00-07:00", "timeZone": "America/Los_Angeles"}
            }
        }
    }
    print("\n--- Testing create_event ---")
    response = lambda_handler(test_event_create, {})
    print(json.dumps(response, indent=2))

    test_event_check = {
        "action": "check_availability",
        "data": {
            "calendarId": "primary",
            "timeMin": "2024-09-01T00:00:00Z",
            "timeMax": "2024-09-02T00:00:00Z"
        }
    }
    print("\n--- Testing check_availability ---")
    response = lambda_handler(test_event_check, {})
    print(json.dumps(response, indent=2))

    test_event_delete = {
        "action": "delete_event",
        "data": {
            "calendarId": "primary",
            "eventId": "some_dummy_event_id_to_delete"
        }
    }
    print("\n--- Testing delete_event ---")
    response = lambda_handler(test_event_delete, {})
    print(json.dumps(response, indent=2))

    test_event_unknown = {
        "action": "unknown_action",
        "data": {}
    }
    print("\n--- Testing unknown_action ---")
    response = lambda_handler(test_event_unknown, {})
    print(json.dumps(response, indent=2))
