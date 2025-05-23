import json
import logging
import os
import boto3

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize Boto3 client for SNS outside the handler for potential reuse
# This is generally recommended for performance in Lambda.
# sns_client = boto3.client('sns')

# Environment variables for SNS Topic ARNs (can be set in Lambda configuration)
# CLIENT_NOTIFICATION_TOPIC_ARN = os.environ.get('CLIENT_NOTIFICATION_TOPIC_ARN')
# STAFF_NOTIFICATION_TOPIC_ARN = os.environ.get('STAFF_NOTIFICATION_TOPIC_ARN')

def lambda_handler(event, context):
    """
    Handles incoming SQS messages to send notifications via SNS.
    """
    lambda_name = "NotificationLambda"
    logger.info(f"Received event for {lambda_name}: {json.dumps(event)}")

    processed_messages = 0
    successful_sends = 0
    failed_sends = 0

    # TODO: Initialize SNS client (if not done globally or if specific region needed)
    sns_client = boto3.client('sns') # Initializing here for clarity per instruction

    for record in event.get('Records', []):
        processed_messages += 1
        try:
            logger.info(f"Processing SQS record: {record.get('messageId')}")
            message_body_str = record.get('body')
            if not message_body_str:
                logger.warning(f"SQS record {record.get('messageId')} has no body. Skipping.")
                failed_sends +=1
                continue

            message_body = json.loads(message_body_str)
            logger.info(f"Parsed message body: {json.dumps(message_body)}")

            # Extract details from the message body
            message_content = message_body.get('message_content')
            recipient_type = message_body.get('recipient_type') # e.g., "client", "staff"
            contact_info = message_body.get('contact_info')     # e.g., phone, email (might not be directly used if publishing to generic topic)
            notification_type = message_body.get('notification_type') # e.g., "booking_confirmation", "cancellation_notice", "hitl_alert"

            if not all([message_content, recipient_type, notification_type]):
                logger.error(
                    f"Missing one or more required fields in message body for record {record.get('messageId')}: "
                    f"message_content, recipient_type, notification_type. Message: {message_body_str}"
                )
                failed_sends += 1
                continue

            # Determine the target SNS Topic ARN
            # This is a simplified logic; real-world might involve more complex routing or direct ARN from message.
            target_topic_arn = None
            if recipient_type == "client":
                target_topic_arn = os.environ.get('CLIENT_NOTIFICATION_TOPIC_ARN', "arn:aws:sns:us-east-1:000000000000:ClientNotificationTopic") # Placeholder
            elif recipient_type == "staff":
                target_topic_arn = os.environ.get('STAFF_NOTIFICATION_TOPIC_ARN', "arn:aws:sns:us-east-1:000000000000:StaffNotificationTopic") # Placeholder
            else:
                logger.warning(f"Unknown recipient_type: {recipient_type} for record {record.get('messageId')}. Cannot determine SNS topic.")
                failed_sends += 1
                continue
            
            logger.info(f"Target SNS Topic ARN determined: {target_topic_arn}")

            # Construct the message to publish to SNS
            # SNS message attributes can be used for filtering by subscribers if needed
            sns_message_attributes = {
                'notification_type': {
                    'DataType': 'String',
                    'StringValue': notification_type
                },
                'recipient_type': {
                    'DataType': 'String',
                    'StringValue': recipient_type
                }
            }
            if contact_info: # Optional: pass contact_info if subscribers need it (e.g. for direct SMS from SNS if not using a secondary lambda)
                 sns_message_attributes['contact_info'] = {
                    'DataType': 'String',
                    'StringValue': str(contact_info) # Ensure it's a string
                }


            # TODO: Publish message to the appropriate SNS topic
            try:
                publish_response = sns_client.publish(
                    TopicArn=target_topic_arn,
                    Message=message_content, # For direct subscribers like email, SQS. For SMS, this is the body.
                    Subject=f"Notification: {notification_type.replace('_', ' ').title()}", # Used by email subscribers
                    MessageAttributes=sns_message_attributes
                )
                logger.info(f"Message published to SNS topic {target_topic_arn} for record {record.get('messageId')}. Message ID: {publish_response.get('MessageId')}")
                successful_sends += 1
            except Exception as sns_e:
                logger.error(f"Failed to publish message to SNS topic {target_topic_arn} for record {record.get('messageId')}: {sns_e}", exc_info=True)
                failed_sends += 1

        except json.JSONDecodeError as json_e:
            logger.error(f"Failed to parse JSON from SQS record body for record {record.get('messageId')}: {json_e}. Body was: {message_body_str}", exc_info=True)
            failed_sends += 1
        except Exception as e:
            logger.error(f"Unexpected error processing SQS record {record.get('messageId')}: {e}", exc_info=True)
            failed_sends += 1
            
    logger.info(f"Finished processing. Total records: {processed_messages}, Successful sends: {successful_sends}, Failed sends: {failed_sends}")
    
    return {
        "statusCode": 200, # SQS processes messages in batches, a 200 indicates successful invocation of Lambda, not necessarily all messages processed.
        "body": json.dumps({
            "status": "success",
            "messages_processed": processed_messages,
            "successful_sends": successful_sends,
            "failed_sends": failed_sends
        })
    }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Mock environment variables for local testing
    os.environ['CLIENT_NOTIFICATION_TOPIC_ARN'] = "arn:aws:sns:us-east-1:123456789012:ClientNotificationTopic-Test"
    os.environ['STAFF_NOTIFICATION_TOPIC_ARN'] = "arn:aws:sns:us-east-1:123456789012:StaffNotificationTopic-Test"

    example_sqs_event_client = {
        "Records": [
            {
                "messageId": "msg1-client",
                "receiptHandle": "handle1",
                "body": json.dumps({
                    "message_content": "Your booking for 'Service Deluxe' at 10:00 AM on 2024-09-15 is confirmed.",
                    "recipient_type": "client",
                    "contact_info": "client@example.com", # or phone for SMS
                    "notification_type": "booking_confirmation"
                }),
                "attributes": {}, "messageAttributes": {}, "md5OfBody": "", "eventSource": "aws:sqs", "eventSourceARN": "", "awsRegion": ""
            }
        ]
    }
    print("\n--- Testing Client Notification via SQS ---")
    # In real Lambda, boto3.client('sns') would use Lambda's IAM role.
    # For local testing, ensure your AWS CLI is configured with permissions or mock boto3.
    response = lambda_handler(example_sqs_event_client, {})
    print(json.dumps(response, indent=2))

    example_sqs_event_staff = {
        "Records": [
            {
                "messageId": "msg1-staff",
                "receiptHandle": "handle2",
                "body": json.dumps({
                    "message_content": "HITL Alert: User 'john.doe' requires assistance with booking ID 'XYZ789'.",
                    "recipient_type": "staff",
                    "contact_info": "staff-alerts@example.com",
                    "notification_type": "hitl_alert"
                }),
                "attributes": {}, "messageAttributes": {}, "md5OfBody": "", "eventSource": "aws:sqs", "eventSourceARN": "", "awsRegion": ""
            }
        ]
    }
    print("\n--- Testing Staff Notification via SQS ---")
    response = lambda_handler(example_sqs_event_staff, {})
    print(json.dumps(response, indent=2))

    example_sqs_event_batch = {
        "Records": [
            {
                "messageId": "msg1-batch",
                "body": json.dumps({
                    "message_content": "Client reminder: Your appointment is tomorrow.",
                    "recipient_type": "client", "contact_info": "client1@example.com", "notification_type": "appointment_reminder"
                })
            },
            {
                "messageId": "msg2-batch-invalid-json",
                "body": "This is not valid JSON"
            },
            {
                "messageId": "msg3-batch-missing-fields",
                "body": json.dumps({"message_content": "Staff alert only"}) # Missing recipient_type and notification_type
            }
        ]
    }
    print("\n--- Testing Batch Notifications with Errors via SQS ---")
    response = lambda_handler(example_sqs_event_batch, {})
    print(json.dumps(response, indent=2))
