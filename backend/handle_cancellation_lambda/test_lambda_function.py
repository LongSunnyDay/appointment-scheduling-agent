import unittest
from unittest.mock import patch, MagicMock, call
import json
import os

# Import the Lambda function to test
from backend.handle_cancellation_lambda.lambda_function import lambda_handler

class TestHandleCancellationLambda(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ['APPOINTMENTS_TABLE_NAME'] = 'mock_appointments_table_cancel'
        os.environ['NOTIFICATION_SQS_URL'] = 'mock_notification_sqs_url_cancel'
        os.environ['GOOGLE_CALENDAR_SYNC_SQS_URL'] = 'mock_google_calendar_sqs_url_cancel'
        os.environ['LOG_LEVEL'] = 'INFO'

    @patch('boto3.resource')
    @patch('boto3.client')
    def setUp(self, mock_boto3_client, mock_boto3_resource):
        self.mock_dynamodb_resource = MagicMock()
        self.mock_appointments_table = MagicMock()
        self.mock_dynamodb_resource.Table.return_value = self.mock_appointments_table
        mock_boto3_resource.return_value = self.mock_dynamodb_resource

        self.mock_sqs_client = MagicMock()
        mock_boto3_client.return_value = self.mock_sqs_client
        
        self.lambda_handler = lambda_handler

    def _create_api_gateway_event(self, booking_id):
        return {
            "pathParameters": {"id": booking_id},
            "requestContext": {"requestId": "test-cancel-id", "http": {"method": "POST"}}
        }

    def test_successful_cancellation_with_google_calendar_event(self):
        booking_id = "booking_with_gcal"
        event = self._create_api_gateway_event(booking_id)
        google_event_id = "gcal_event_123"

        mock_booking_item = {
            'bookingId': booking_id,
            'status': 'confirmed', # Booking is confirmed
            'googleCalendarEventId': google_event_id, # Has a Google Calendar event
            'locationId': 'location1',
            'clientDetails': {'name': 'Test Client', 'email': 'test@example.com'},
            'serviceName': 'Test Service',
            'proposedStartTime': '2024-01-01T10:00:00Z'
        }
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'cancelled', 'updatedAt': 'some-iso-time'}
        }
        self.mock_sqs_client.send_message.return_value = {'MessageId': 'sqs-msg-id'}

        response = self.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['message'], f"Booking {booking_id} cancelled successfully.")
        self.assertEqual(response_body['booking']['status'], 'cancelled')

        self.mock_appointments_table.get_item.assert_called_once_with(Key={'bookingId': booking_id})
        self.mock_appointments_table.update_item.assert_called_once()
        update_args = self.mock_appointments_table.update_item.call_args[1]
        self.assertEqual(update_args['Key'], {'bookingId': booking_id})
        self.assertEqual(update_args['ExpressionAttributeValues'][':status_val'], 'cancelled')

        self.assertEqual(self.mock_sqs_client.send_message.call_count, 2)
        
        # Check Google Calendar SQS call (DELETE_EVENT)
        gcal_sqs_call_args = self.mock_sqs_client.send_message.call_args_list[0][1]
        self.assertEqual(gcal_sqs_call_args['QueueUrl'], 'mock_google_calendar_sqs_url_cancel')
        gcal_message_body = json.loads(gcal_sqs_call_args['MessageBody'])
        self.assertEqual(gcal_message_body['bookingId'], booking_id)
        self.assertEqual(gcal_message_body['googleCalendarEventId'], google_event_id)
        self.assertEqual(gcal_message_body['action'], 'DELETE_EVENT')

        # Check Notification SQS call
        notification_sqs_call_args = self.mock_sqs_client.send_message.call_args_list[1][1]
        self.assertEqual(notification_sqs_call_args['QueueUrl'], 'mock_notification_sqs_url_cancel')
        notification_message_body = json.loads(notification_sqs_call_args['MessageBody'])
        self.assertEqual(notification_message_body['bookingId'], booking_id)
        self.assertEqual(notification_message_body['notificationType'], 'BOOKING_CANCELLED')

    def test_successful_cancellation_pending_booking_no_gcal_event(self):
        booking_id = "booking_pending_no_gcal"
        event = self._create_api_gateway_event(booking_id)

        mock_booking_item = {
            'bookingId': booking_id,
            'status': 'pending_confirmation', # Booking is pending
            # No googleCalendarEventId
            'locationId': 'location2', # Still need locationId for consistency if logic were different
            'clientDetails': {'name': 'Pending Client', 'email': 'pending@example.com'},
            'serviceName': 'Pending Service',
            'proposedStartTime': '2024-02-01T10:00:00Z'
        }
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'cancelled', 'updatedAt': 'some-iso-time'}
        }
        self.mock_sqs_client.send_message.return_value = {'MessageId': 'sqs-msg-id-notify'}

        response = self.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['message'], f"Booking {booking_id} cancelled successfully.")

        self.mock_appointments_table.update_item.assert_called_once()
        
        # Only one SQS call (Notification)
        self.mock_sqs_client.send_message.assert_called_once()
        notification_sqs_call_args = self.mock_sqs_client.send_message.call_args_list[0][1]
        self.assertEqual(notification_sqs_call_args['QueueUrl'], 'mock_notification_sqs_url_cancel')
        notification_message_body = json.loads(notification_sqs_call_args['MessageBody'])
        self.assertEqual(notification_message_body['notificationType'], 'BOOKING_CANCELLED')

    def test_booking_not_found_for_cancellation(self):
        booking_id = "booking_not_exist_cancel"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.return_value = {} # No 'Item'

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 404)
        self.assertIn(f"Booking {booking_id} not found", response['body'])
        self.mock_appointments_table.update_item.assert_not_called()
        self.mock_sqs_client.send_message.assert_not_called()

    def test_booking_already_cancelled_cannot_cancel_again(self):
        booking_id = "booking_already_cancelled"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.return_value = {
            'Item': {'bookingId': booking_id, 'status': 'cancelled'}
        }
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 409)
        self.assertIn(f"Booking {booking_id} cannot be cancelled. Current status: cancelled", response['body'])
        self.mock_appointments_table.update_item.assert_not_called()

    def test_booking_already_completed_cannot_cancel(self):
        booking_id = "booking_already_completed"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.return_value = {
            'Item': {'bookingId': booking_id, 'status': 'completed'}
        }
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 409)
        self.assertIn(f"Booking {booking_id} cannot be cancelled. Current status: completed", response['body'])

    def test_dynamodb_get_item_error_on_cancellation(self):
        booking_id = "booking_ddb_get_error_cancel"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.side_effect = Exception("DynamoDB get_item failed during cancel")
        
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 500)
        self.assertIn("Failed to fetch booking details.", response['body'])

    def test_dynamodb_update_item_error_on_cancellation(self):
        booking_id = "booking_ddb_update_error_cancel"
        event = self._create_api_gateway_event(booking_id)
        mock_booking_item = {'bookingId': booking_id, 'status': 'confirmed'}
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.side_effect = Exception("DynamoDB update_item failed during cancel")

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 500)
        self.assertIn("Failed to update booking status.", response['body'])
        self.mock_sqs_client.send_message.assert_not_called() # No SQS if DB update fails

    def test_sqs_send_gcal_error_still_sends_notification(self):
        booking_id = "booking_sqs_gcal_err_cancel"
        event = self._create_api_gateway_event(booking_id)
        google_event_id = "gcal_event_456"
        mock_booking_item = {
            'bookingId': booking_id, 'status': 'confirmed', 
            'googleCalendarEventId': google_event_id, 'locationId': 'locX',
            'clientDetails': {'name': 'ClientX', 'email': 'clientx@example.com'}
        }
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'cancelled'}
        }
        
        self.mock_sqs_client.send_message.side_effect = [
            Exception("SQS send for GCal DELETE failed"),
            {'MessageId': 'sqs-notify-msg-id'}
        ]

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 200) # Still 200, GCal SQS error is logged but non-fatal to cancellation itself
        self.assertIn(f"Booking {booking_id} cancelled successfully.", response['body'])
        
        self.mock_appointments_table.update_item.assert_called_once()
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 2)
        
        # Check that the second SQS call (Notification) was made
        notification_sqs_call_args = self.mock_sqs_client.send_message.call_args_list[1][1]
        self.assertEqual(notification_sqs_call_args['QueueUrl'], 'mock_notification_sqs_url_cancel')

    def test_sqs_send_notification_error(self):
        booking_id = "booking_sqs_notification_err_cancel"
        event = self._create_api_gateway_event(booking_id)
        mock_booking_item = {
            'bookingId': booking_id, 'status': 'pending_confirmation', 
            'clientDetails': {'name': 'ClientY', 'email': 'clienty@example.com'}
        } # No GCal event ID
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'cancelled'}
        }
        self.mock_sqs_client.send_message.side_effect = Exception("SQS send for Notification failed")

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 200) # Still 200, Notification SQS error is logged
        self.assertIn(f"Booking {booking_id} cancelled successfully.", response['body'])
        self.mock_sqs_client.send_message.assert_called_once() # Attempted once

    def test_missing_path_parameter_id_for_cancellation(self):
        event = { "pathParameters": {} } 
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 400)
        self.assertIn("Missing booking ID in request path.", response['body'])

    def test_missing_environment_variables_for_cancellation(self):
        original_val = os.environ.pop('APPOINTMENTS_TABLE_NAME', None)
        booking_id = "booking_env_error_cancel"
        event = self._create_api_gateway_event(booking_id)
        
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 500)
        self.assertIn("Configuration error", response['body'])
        
        if original_val is not None:
            os.environ['APPOINTMENTS_TABLE_NAME'] = original_val
            
    def test_cancellation_no_client_email(self):
        booking_id = "booking_no_email"
        event = self._create_api_gateway_event(booking_id)

        mock_booking_item = {
            'bookingId': booking_id,
            'status': 'pending_confirmation',
            'clientDetails': {'name': 'No Email Client'} # No email
        }
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'cancelled'}
        }

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 200)
        self.assertIn(f"Booking {booking_id} cancelled successfully.", response['body'])
        self.mock_sqs_client.send_message.assert_not_called() # Notification SQS not called


if __name__ == '__main__':
    unittest.main(verbosity=2)

# To run from project root:
# PYTHONPATH=. python -m unittest backend.handle_cancellation_lambda.test_lambda_function
# (Assuming __init__.py is in backend/ and backend/handle_cancellation_lambda/)
