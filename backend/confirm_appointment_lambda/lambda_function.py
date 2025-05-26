import json
import logging
import os
import boto3

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

import datetime

# Initialize Boto3 clients
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

appointments_table_name = os.environ.get('APPOINTMENTS_TABLE_NAME')
notification_sqs_url = os.environ.get('NOTIFICATION_SQS_URL')
google_calendar_sync_sqs_url = os.environ.get('GOOGLE_CALENDAR_SYNC_SQS_URL')

def lambda_handler(event, context):
    """
    Handles incoming requests for the ConfirmAppointmentLambda.
    Triggered by an API Gateway (POST /bookings/{id}/confirm).
    """
    lambda_name = "ConfirmAppointmentLambda"
    logger.info(f"Received event for {lambda_name}: {json.dumps(event)}")

    if not all([appointments_table_name, notification_sqs_url, google_calendar_sync_sqs_url]):
        logger.error("Missing one or more environment variables: APPOINTMENTS_TABLE_NAME, NOTIFICATION_SQS_URL, GOOGLE_CALENDAR_SYNC_SQS_URL")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Configuration error in {lambda_name}."})
        }
    
    appointments_table = dynamodb.Table(appointments_table_name)

    try:
        # 1. Extract bookingId
        if 'pathParameters' in event and event['pathParameters'] and 'id' in event['pathParameters']:
            booking_id = event['pathParameters']['id']
        else:
            logger.warning("Booking ID not found in event pathParameters.")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing booking ID in request path."})
            }
        
        logger.info(f"Attempting to confirm booking: {booking_id}")

        # 2. Fetch the booking from DynamoDB
        try:
            response = appointments_table.get_item(Key={'bookingId': booking_id})
            booking_item = response.get('Item')
        except Exception as e:
            logger.error(f"Error fetching booking {booking_id} from DynamoDB: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to fetch booking details."})
            }

        # 3. Validate the booking
        if not booking_item:
            logger.warning(f"Booking {booking_id} not found.")
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Booking {booking_id} not found."})
            }

        current_status = booking_item.get('status')
        if current_status != 'pending_confirmation':
            logger.warning(f"Booking {booking_id} status is '{current_status}', not 'pending_confirmation'. Cannot confirm.")
            return {
                "statusCode": 409, # Conflict
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Booking {booking_id} cannot be confirmed. Current status: {current_status}."})
            }

        # 4. Update the booking status to 'confirmed'
        updated_at = datetime.datetime.utcnow().isoformat()
        try:
            update_response = appointments_table.update_item(
                Key={'bookingId': booking_id},
                UpdateExpression="SET #status = :status_val, #updatedAt = :updatedAt_val",
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#updatedAt': 'updatedAt'
                },
                ExpressionAttributeValues={
                    ':status_val': 'confirmed',
                    ':updatedAt_val': updated_at
                },
                ReturnValues="ALL_NEW" 
            )
            confirmed_booking = update_response.get('Attributes', {})
            logger.info(f"Booking {booking_id} status updated to confirmed. Details: {json.dumps(confirmed_booking)}")
        except Exception as e:
            logger.error(f"Error updating booking {booking_id} status in DynamoDB: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to update booking status."})
            }

        # 5. Send a message to GOOGLE_CALENDAR_SYNC_SQS_URL
        calendar_message_body = {
            "bookingId": booking_id,
            "action": "CREATE_EVENT", # Indicate action for Google Calendar Sync Lambda
            "serviceId": booking_item.get("serviceId"),
            "locationId": booking_item.get("locationId"),
            "proposedStartTime": booking_item.get("proposedStartTime"),
            "proposedEndTime": booking_item.get("proposedEndTime"),
            "clientName": booking_item.get("clientDetails", {}).get("name"), # Assuming clientDetails structure
            "clientEmail": booking_item.get("clientDetails", {}).get("email") # Assuming clientDetails structure
        }
        try:
            sqs.send_message(
                QueueUrl=google_calendar_sync_sqs_url,
                MessageBody=json.dumps(calendar_message_body)
            )
            logger.info(f"Sent message to Google Calendar Sync SQS for booking {booking_id}: {json.dumps(calendar_message_body)}")
        except Exception as e:
            logger.error(f"Error sending message to Google Calendar Sync SQS for booking {booking_id}: {e}", exc_info=True)
            # Non-critical error, proceed with client notification but log it.
            # Potentially add to a dead-letter queue or retry mechanism for this SQS message later.

        # 6. Send a message to NOTIFICATION_SQS_URL
        notification_message_body = {
            "bookingId": booking_id,
            "notificationType": "BOOKING_CONFIRMED",
            "recipient": booking_item.get("clientDetails", {}).get("email"), # Or phone, depending on notification prefs
            "messageDetails": {
                "clientName": booking_item.get("clientDetails", {}).get("name"),
                "serviceName": booking_item.get("serviceName", "the service"), # Placeholder if not available
                "startTime": booking_item.get("proposedStartTime"),
                "locationName": booking_item.get("locationName", "our location") # Placeholder
            }
        }
        try:
            sqs.send_message(
                QueueUrl=notification_sqs_url,
                MessageBody=json.dumps(notification_message_body)
            )
            logger.info(f"Sent message to Notification SQS for booking {booking_id}: {json.dumps(notification_message_body)}")
        except Exception as e:
            logger.error(f"Error sending message to Notification SQS for booking {booking_id}: {e}", exc_info=True)
            # Non-critical error, booking is confirmed. Log it.

        # 7. Return success response
        logger.info(f"Booking {booking_id} confirmed successfully.")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": f"Booking {booking_id} confirmed successfully.",
                "booking": confirmed_booking # Send back the updated booking item
            })
        }

    except Exception as e: # Catch-all for any other unexpected errors
        logger.error(f"Unexpected error in {lambda_name} for bookingId {event.get('pathParameters',{}).get('id', 'N/A')}: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": f"An internal server error occurred in {lambda_name}."
            })
        }

if __name__ == '__main__':
    # Example usage for local testing
    logging.basicConfig(level=logging.INFO)
    
    test_event_api = {
        "httpMethod": "POST",
        "path": "/bookings/booking456/confirm",
        "pathParameters": {
            "id": "booking456"
        },
        "headers": {
            "Content-Type": "application/json"
        }
    }
    
    test_context = {}
    
    response = lambda_handler(test_event_api, test_context)
    print("\nLambda Response (API Trigger):")
    print(json.dumps(response, indent=2))

    test_event_sqs = {
        "Records": [
            {
                "body": json.dumps({
                    "bookingId": "booking789",
                    "confirmationToken": "tokenXYZ"
                })
            }
        ]
    }
    # response_sqs = lambda_handler(test_event_sqs, test_context) # Adapt handler for SQS if needed
    # print("\nLambda Response (SQS Trigger - conceptual):")
    # print(json.dumps(response_sqs, indent=2))
