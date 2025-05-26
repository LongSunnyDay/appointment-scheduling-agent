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
google_calendar_sync_sqs_url = os.environ.get('GOOGLE_CALENDAR_SYNC_SQS_URL') # Added for Google Calendar integration

def lambda_handler(event, context):
    """
    Handles incoming requests for the HandleCancellationLambda.
    Triggered by API Gateway (e.g., POST /bookings/{id}/cancel).
    """
    lambda_name = "HandleCancellationLambda"
    logger.info(f"Received event for {lambda_name}: {json.dumps(event)}")

    # Check for required environment variables
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
        
        logger.info(f"Attempting to cancel booking: {booking_id}")

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
        if current_status in ['cancelled', 'rejected', 'completed']: # Add other terminal statuses as needed
            logger.warning(f"Booking {booking_id} is already in a terminal status: '{current_status}'. Cannot cancel again.")
            return {
                "statusCode": 409, # Conflict
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Booking {booking_id} cannot be cancelled. Current status: {current_status}."})
            }
        
        # 4. Update the booking status to 'cancelled'
        # For now, status is always 'cancelled'. If logic for 'rejected' vs 'cancelled' is needed based on event body:
        # new_status = "cancelled" 
        # if 'body' in event and event['body']:
        #    try:
        #        body = json.loads(event['body'])
        #        if body.get('action') == 'reject':
        #            new_status = 'rejected'
        #    except json.JSONDecodeError:
        #        logger.warning("Could not parse body for action field.")
        new_status = "cancelled" # As per instruction, stick to 'cancelled'
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
                    ':status_val': new_status,
                    ':updatedAt_val': updated_at
                },
                ReturnValues="ALL_NEW" 
            )
            cancelled_booking = update_response.get('Attributes', {})
            logger.info(f"Booking {booking_id} status updated to {new_status}. Details: {json.dumps(cancelled_booking)}")
        except Exception as e:
            logger.error(f"Error updating booking {booking_id} status in DynamoDB: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to update booking status."})
            }

        # 5. If synced with Google Calendar, send message to delete the event
        google_calendar_event_id = booking_item.get('googleCalendarEventId')
        if google_calendar_event_id:
            calendar_message_body = {
                "bookingId": booking_id,
                "googleCalendarEventId": google_calendar_event_id,
                "action": "DELETE_EVENT" 
            }
            try:
                sqs.send_message(
                    QueueUrl=google_calendar_sync_sqs_url,
                    MessageBody=json.dumps(calendar_message_body)
                )
                logger.info(f"Sent message to Google Calendar Sync SQS for booking {booking_id} to delete event {google_calendar_event_id}: {json.dumps(calendar_message_body)}")
            except Exception as e:
                logger.error(f"Error sending message to Google Calendar Sync SQS for booking {booking_id}: {e}", exc_info=True)
                # Log error, but don't fail the whole cancellation if this SQS message fails.
                # Consider a retry mechanism or dead-letter queue for this.

        # 6. Send a notification to the client about the cancellation
        client_details = booking_item.get("clientDetails", {})
        notification_message_body = {
            "bookingId": booking_id,
            "notificationType": "BOOKING_CANCELLED", # Or "BOOKING_REJECTED" if new_status logic is expanded
            "recipient": client_details.get("email"), # Or phone, depending on notification preferences
            "messageDetails": {
                "clientName": client_details.get("name"),
                "serviceName": booking_item.get("serviceName", "the service"), 
                "startTime": booking_item.get("proposedStartTime"),
                "reason": "Your booking has been cancelled." # Generic reason
            }
        }
        if client_details.get("email"): # Only send if email is available
            try:
                sqs.send_message(
                    QueueUrl=notification_sqs_url,
                    MessageBody=json.dumps(notification_message_body)
                )
                logger.info(f"Sent message to Notification SQS for booking {booking_id}: {json.dumps(notification_message_body)}")
            except Exception as e:
                logger.error(f"Error sending message to Notification SQS for booking {booking_id}: {e}", exc_info=True)
                # Log error, but booking is already cancelled in DB.
        else:
            logger.warning(f"No recipient email found for booking {booking_id}, skipping cancellation notification.")


        # 7. Return success response
        logger.info(f"Booking {booking_id} cancelled successfully.")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": f"Booking {booking_id} cancelled successfully.",
                "booking": cancelled_booking
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
    
    test_event_api_gateway = {
        "httpMethod": "POST",
        "path": "/bookings/booking123/cancel",
        "pathParameters": {
            "id": "booking123"
        },
        "headers": {
            "Content-Type": "application/json"
        }
        # No body needed if ID is in path
    }
    
    test_context = {}
    
    response = lambda_handler(test_event_api_gateway, test_context)
    print("\nLambda Response (API Gateway Trigger):")
    print(json.dumps(response, indent=2))
