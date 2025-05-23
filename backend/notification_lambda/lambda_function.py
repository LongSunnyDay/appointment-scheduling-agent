import json
import logging
import os
# import boto3 # Not strictly needed for stubbed notifications

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# APPOINTMENTS_TABLE_NAME = os.environ.get('APPOINTMENTS_TABLE_NAME') # Not used for now, as SQS message is self-contained

# --- Stubbed Notification Sending Function ---
def stub_send_notification(recipient_contact, subject, body):
    """
    Stub function to simulate sending a notification.
    Logs the recipient, subject, and body.
    """
    logger.info(f"[STUB_NOTIFICATION] Sending notification to: {recipient_contact}")
    logger.info(f"[STUB_NOTIFICATION] Subject: {subject}")
    logger.info(f"[STUB_NOTIFICATION] Body: {body}")
    # In a real scenario, this would use boto3 to send email via SES, SMS via SNS, or other methods.
    return True # Simulate successful send

# --- Notification Formatting and Dispatch Logic ---
def format_and_send_notification(notification_type, message_details, booking_id_log_ctx):
    """
    Formats notification content based on notificationType and calls the stub sender.
    """
    subject = ""
    body = ""
    recipient_contact = message_details.get('recipient') # General recipient field from SQS

    if not recipient_contact:
        logger.error(f"[{booking_id_log_ctx}] Recipient contact missing in message_details. Cannot send notification.")
        return False

    client_name = message_details.get('clientName', 'Valued Client')
    service_name = message_details.get('serviceName', 'your selected service')
    start_time = message_details.get('startTime', 'the scheduled time')
    location_name = message_details.get('locationName', 'our location')
    # reason = message_details.get('reason', 'as per our records') # For cancellation/rejection

    if notification_type == "BOOKING_CONFIRMED":
        subject = f"Booking Confirmed: Your Appointment for {service_name}"
        body = (
            f"Dear {client_name},\n\n"
            f"This email confirms your booking for {service_name} at {location_name} on {start_time}.\n\n"
            f"We look forward to seeing you!\n\n"
            f"Booking ID: {booking_id_log_ctx}"
        )
    elif notification_type == "BOOKING_CANCELLED":
        subject = f"Booking Cancellation Notice: {service_name}"
        body = (
            f"Dear {client_name},\n\n"
            f"This email confirms the cancellation of your booking for {service_name} at {location_name} scheduled for {start_time}.\n\n"
            f"If you did not request this cancellation, or if you have any questions, please contact us.\n\n"
            f"Booking ID: {booking_id_log_ctx}"
        )
    elif notification_type == "BOOKING_REJECTED":
        rejection_reason = message_details.get('reason', "Unfortunately, we are unable to confirm your requested appointment at this time.")
        subject = f"Regarding Your Booking Request for {service_name}"
        body = (
            f"Dear {client_name},\n\n"
            f"Regarding your provisional booking request for {service_name} at {location_name} for {start_time}.\n\n"
            f"{rejection_reason}\n\n"
            f"Please contact us if you would like to discuss alternative options.\n\n"
            f"Booking ID: {booking_id_log_ctx}"
        )
    elif notification_type == "PROVISIONAL_BOOKING_CREATED":
        # Client notification
        subject = f"Provisional Booking Received: {service_name}"
        body = (
            f"Dear {client_name},\n\n"
            f"We have received your provisional booking request for {service_name} at {location_name} for {start_time}.\n"
            f"Our team will review the details and confirm your appointment shortly.\n\n"
            f"Booking ID: {booking_id_log_ctx}"
        )
        # Optional: Staff notification (can be added here or by sending another SQS message from originator)
        # staff_recipient = "staff-alerts@example.com" # Example
        # staff_subject = f"New Provisional Booking: {booking_id_log_ctx} for {service_name}"
        # staff_body = f"A new provisional booking (ID: {booking_id_log_ctx}) for {service_name} by {client_name} ({recipient_contact}) at {location_name} for {start_time} requires review."
        # stub_send_notification(staff_recipient, staff_subject, staff_body)
        # logger.info(f"[{booking_id_log_ctx}] Staff notification also sent for PROVISIONAL_BOOKING_CREATED.")

    else:
        logger.warning(f"[{booking_id_log_ctx}] Unknown notification_type: {notification_type}. Cannot format message.")
        return False

    return stub_send_notification(recipient_contact, subject, body)


def lambda_handler(event, context):
    """
    Handles incoming SQS messages to format and "send" notifications.
    """
    lambda_name = "NotificationLambda"
    logger.info(f"Received event for {lambda_name}: {json.dumps(event)}")

    processed_messages = 0
    successful_sends = 0
    failed_sends = 0

    for record in event.get('Records', []):
        message_id = record.get('messageId', 'UnknownMessageID')
        booking_id_log_ctx = f"MessageId: {message_id}" # Default logging context

        try:
            logger.info(f"Processing SQS record: {message_id}")
            message_body_str = record.get('body')
            if not message_body_str:
                logger.warning(f"[{booking_id_log_ctx}] SQS record has no body. Skipping.")
                failed_sends +=1
                continue

            message_body = json.loads(message_body_str)
            logger.info(f"[{booking_id_log_ctx}] Parsed message body: {json.dumps(message_body)}")

            # Update logging context if bookingId is available
            booking_id_from_msg = message_body.get('bookingId', 'UnknownBookingID')
            booking_id_log_ctx = f"BookingId: {booking_id_from_msg} (MsgId: {message_id})"


            notification_type = message_body.get('notificationType')
            message_details = message_body.get('messageDetails') # This should contain all necessary data

            if not notification_type or not isinstance(message_details, dict):
                logger.error(
                    f"[{booking_id_log_ctx}] Missing 'notificationType' or 'messageDetails' (must be a dictionary) in message body. "
                    f"Message: {message_body_str}"
                )
                failed_sends += 1
                continue
            
            if format_and_send_notification(notification_type, message_details, booking_id_log_ctx):
                successful_sends += 1
            else:
                failed_sends += 1
            
            processed_messages += 1

        except json.JSONDecodeError as json_e:
            logger.error(f"[{booking_id_log_ctx}] Failed to parse JSON from SQS record body: {json_e}. Body was: {message_body_str}", exc_info=True)
            failed_sends += 1
        except Exception as e:
            logger.error(f"[{booking_id_log_ctx}] Unexpected error processing SQS record: {e}", exc_info=True)
            failed_sends += 1
            
    logger.info(f"Finished processing. Total records processed in this invocation: {processed_messages}, Successful sends: {successful_sends}, Failed sends: {failed_sends}")
    
    # For SQS, Lambda's success/failure is for the batch. Individual message failures are logged.
    # Configure DLQ on the SQS queue for persistent message failures.
    return {
        "status": "completed",
        "messages_processed_in_invocation": processed_messages,
        "successful_sends_in_invocation": successful_sends,
        "failed_sends_in_invocation": failed_sends
    }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Example SQS events for different notification types

    test_event_confirmed = {
        "Records": [
            {
                "messageId": "msg-confirmed-001",
                "body": json.dumps({
                    "bookingId": "booking123",
                    "notificationType": "BOOKING_CONFIRMED",
                    "messageDetails": {
                        "recipient": "client.confirmed@example.com",
                        "clientName": "Alice Wonderland",
                        "serviceName": "Teeth Cleaning",
                        "startTime": "2024-10-15 at 2:00 PM",
                        "locationName": "Downtown Dental Clinic"
                    }
                })
            }
        ]
    }
    print("\n--- Testing BOOKING_CONFIRMED Notification ---")
    response = lambda_handler(test_event_confirmed, {})
    print(json.dumps(response, indent=2))

    test_event_cancelled = {
        "Records": [
            {
                "messageId": "msg-cancelled-001",
                "body": json.dumps({
                    "bookingId": "booking456",
                    "notificationType": "BOOKING_CANCELLED",
                    "messageDetails": {
                        "recipient": "client.cancelled@example.com",
                        "clientName": "Bob The Builder",
                        "serviceName": "Annual Checkup",
                        "startTime": "2024-11-01 at 10:00 AM",
                        "locationName": "City General Hospital"
                        # "reason" could be added here if available from cancellation source
                    }
                })
            }
        ]
    }
    print("\n--- Testing BOOKING_CANCELLED Notification ---")
    response = lambda_handler(test_event_cancelled, {})
    print(json.dumps(response, indent=2))

    test_event_rejected = {
        "Records": [
            {
                "messageId": "msg-rejected-001",
                "body": json.dumps({
                    "bookingId": "booking789-provisional",
                    "notificationType": "BOOKING_REJECTED",
                    "messageDetails": {
                        "recipient": "client.rejected@example.com",
                        "clientName": "Charlie Brown",
                        "serviceName": "Specialist Consultation",
                        "startTime": "2024-12-05 at 3:30 PM",
                        "locationName": "Specialty Clinic North",
                        "reason": "The specialist is unfortunately unavailable at your requested time. Please try an alternative slot."
                    }
                })
            }
        ]
    }
    print("\n--- Testing BOOKING_REJECTED Notification ---")
    response = lambda_handler(test_event_rejected, {})
    print(json.dumps(response, indent=2))

    test_event_provisional = {
        "Records": [
            {
                "messageId": "msg-provisional-001",
                "body": json.dumps({
                    "bookingId": "bookingABC-provisional",
                    "notificationType": "PROVISIONAL_BOOKING_CREATED",
                    "messageDetails": {
                        "recipient": "client.provisional@example.com",
                        "clientName": "Diana Prince",
                        "serviceName": "Advanced Screening",
                        "startTime": "2025-01-20 at 9:00 AM",
                        "locationName": "Metropolis Health Services"
                    }
                })
            }
        ]
    }
    print("\n--- Testing PROVISIONAL_BOOKING_CREATED Notification ---")
    response = lambda_handler(test_event_provisional, {})
    print(json.dumps(response, indent=2))
    
    test_event_unknown_type = {
        "Records": [
            {
                "messageId": "msg-unknown-001",
                "body": json.dumps({
                    "bookingId": "bookingXYZ",
                    "notificationType": "SOME_NEW_UNHANDLED_TYPE",
                    "messageDetails": {"recipient": "client.unknown@example.com", "clientName": "Mystery Guest"}
                })
            }
        ]
    }
    print("\n--- Testing UNKNOWN_NOTIFICATION_TYPE ---")
    response = lambda_handler(test_event_unknown_type, {})
    print(json.dumps(response, indent=2))

    test_event_missing_details = {
        "Records": [
            {
                "messageId": "msg-missing-001",
                "body": json.dumps({
                    "bookingId": "bookingOops",
                    "notificationType": "BOOKING_CONFIRMED"
                    # messageDetails is missing
                })
            }
        ]
    }
    print("\n--- Testing Missing messageDetails ---")
    response = lambda_handler(test_event_missing_details, {})
    print(json.dumps(response, indent=2))

    test_event_invalid_json = {
        "Records": [
            {
                "messageId": "msg-invalidjson-001",
                "body": "This is definitely not JSON { bookingId: nope },"
            }
        ]
    }
    print("\n--- Testing Invalid JSON Body ---")
    response = lambda_handler(test_event_invalid_json, {})
    print(json.dumps(response, indent=2))
