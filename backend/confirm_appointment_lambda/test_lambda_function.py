import unittest
from unittest.mock import patch, MagicMock
import json
import os

# Import the Lambda function to test
from backend.confirm_appointment_lambda.lambda_function import lambda_handler

class TestConfirmAppointmentLambda(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Mock environment variables before importing the lambda function if it reads them at global scope
        # However, our lambda_function.py reads them inside the handler or at module level after logger.
        # For safety, we set them up here.
        os.environ['APPOINTMENTS_TABLE_NAME'] = 'mock_appointments_table'
        os.environ['NOTIFICATION_SQS_URL'] = 'mock_notification_sqs_url'
        os.environ['GOOGLE_CALENDAR_SYNC_SQS_URL'] = 'mock_google_calendar_sqs_url'
        os.environ['LOG_LEVEL'] = 'INFO'


    @patch('boto3.resource')
    @patch('boto3.client')
    def setUp(self, mock_boto3_client, mock_boto3_resource):
        # This setUp method is called before each test method
        
        # Mock DynamoDB resource and table
        self.mock_dynamodb_resource = MagicMock()
        self.mock_appointments_table = MagicMock()
        self.mock_dynamodb_resource.Table.return_value = self.mock_appointments_table
        mock_boto3_resource.return_value = self.mock_dynamodb_resource

        # Mock SQS client
        self.mock_sqs_client = MagicMock()
        mock_boto3_client.return_value = self.mock_sqs_client
        
        # Re-import lambda_handler or reload its module if env vars need to be re-read by it.
        # For this structure, it's usually fine as os.environ is dynamic.
        # from backend.confirm_appointment_lambda import lambda_function
        # import importlib
        # importlib.reload(lambda_function)
        # self.lambda_handler = lambda_function.lambda_handler
        self.lambda_handler = lambda_handler


    def _create_api_gateway_event(self, booking_id):
        return {
            "pathParameters": {
                "id": booking_id
            },
            "requestContext": { # Add some typical requestContext
                "requestId": "test-request-id",
                "http": {
                    "method": "POST"
                }
            }
        }

    def test_successful_confirmation(self):
        booking_id = "booking123"
        event = self._create_api_gateway_event(booking_id)

        # Mock DynamoDB get_item response
        mock_booking_item = {
            'bookingId': booking_id,
            'status': 'pending_confirmation',
            'serviceId': 'serviceABC',
            'locationId': 'locationXYZ',
            'proposedStartTime': '2024-01-01T10:00:00Z',
            'proposedEndTime': '2024-01-01T11:00:00Z',
            'clientDetails': {'name': 'Test Client', 'email': 'test@example.com'}
        }
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}

        # Mock DynamoDB update_item response
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'confirmed', 'updatedAt': 'some-iso-time'}
        }
        
        # Mock SQS send_message response
        self.mock_sqs_client.send_message.return_value = {'MessageId': 'sqs-message-id'}

        response = self.lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['message'], f"Booking {booking_id} confirmed successfully.")
        self.assertEqual(response_body['booking']['status'], 'confirmed')

        # Assert DynamoDB calls
        self.mock_appointments_table.get_item.assert_called_once_with(Key={'bookingId': booking_id})
        self.mock_appointments_table.update_item.assert_called_once()
        update_args = self.mock_appointments_table.update_item.call_args[1]
        self.assertEqual(update_args['Key'], {'bookingId': booking_id})
        self.assertEqual(update_args['ExpressionAttributeValues'][':status_val'], 'confirmed')

        # Assert SQS calls (called twice)
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 2)
        
        # Check call to Google Calendar SQS
        calendar_sqs_call = self.mock_sqs_client.send_message.call_args_list[0]
        self.assertEqual(calendar_sqs_call[1]['QueueUrl'], 'mock_google_calendar_sqs_url')
        calendar_message_body = json.loads(calendar_sqs_call[1]['MessageBody'])
        self.assertEqual(calendar_message_body['bookingId'], booking_id)
        self.assertEqual(calendar_message_body['action'], 'CREATE_EVENT')

        # Check call to Notification SQS
        notification_sqs_call = self.mock_sqs_client.send_message.call_args_list[1]
        self.assertEqual(notification_sqs_call[1]['QueueUrl'], 'mock_notification_sqs_url')
        notification_message_body = json.loads(notification_sqs_call[1]['MessageBody'])
        self.assertEqual(notification_message_body['bookingId'], booking_id)
        self.assertEqual(notification_message_body['notificationType'], 'BOOKING_CONFIRMED')


    def test_booking_not_found(self):
        booking_id = "booking_not_exist"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.return_value = {} # No 'Item' key

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 404)
        self.assertIn(f"Booking {booking_id} not found", response['body'])
        self.mock_appointments_table.update_item.assert_not_called()
        self.mock_sqs_client.send_message.assert_not_called()

    def test_booking_already_confirmed(self):
        booking_id = "booking_already_done"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.return_value = {
            'Item': {'bookingId': booking_id, 'status': 'confirmed'}
        }
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 409)
        self.assertIn(f"Booking {booking_id} cannot be confirmed. Current status: confirmed", response['body'])
        self.mock_appointments_table.update_item.assert_not_called()

    def test_booking_in_cancelled_status(self):
        booking_id = "booking_cancelled_status"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.return_value = {
            'Item': {'bookingId': booking_id, 'status': 'cancelled'}
        }
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 409)
        self.assertIn(f"Booking {booking_id} cannot be confirmed. Current status: cancelled", response['body'])
        self.mock_appointments_table.update_item.assert_not_called()

    def test_dynamodb_get_item_error(self):
        booking_id = "booking_ddb_get_error"
        event = self._create_api_gateway_event(booking_id)
        self.mock_appointments_table.get_item.side_effect = Exception("DynamoDB get_item failed")
        
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 500)
        self.assertIn("Failed to fetch booking details.", response['body'])
        self.mock_appointments_table.update_item.assert_not_called()

    def test_dynamodb_update_item_error(self):
        booking_id = "booking_ddb_update_error"
        event = self._create_api_gateway_event(booking_id)
        mock_booking_item = {'bookingId': booking_id, 'status': 'pending_confirmation'}
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.side_effect = Exception("DynamoDB update_item failed")

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 500)
        self.assertIn("Failed to update booking status.", response['body'])
        # SQS messages should not be sent if DB update fails
        self.mock_sqs_client.send_message.assert_not_called()

    def test_sqs_send_calendar_message_error_still_sends_notification(self):
        booking_id = "booking_sqs_cal_error"
        event = self._create_api_gateway_event(booking_id)
        mock_booking_item = {
            'bookingId': booking_id, 'status': 'pending_confirmation',
            'serviceId': 's1', 'locationId': 'l1', 
            'proposedStartTime': '2024-01-01T10:00:00Z', 'proposedEndTime': '2024-01-01T11:00:00Z',
            'clientDetails': {'name': 'Test Client', 'email': 'test@example.com'}
        }
        self.mock_appointments_table.get_item.return_value = {'Item': mock_booking_item}
        self.mock_appointments_table.update_item.return_value = {
            'Attributes': {**mock_booking_item, 'status': 'confirmed'}
        }
        
        # First SQS call (calendar) fails, second (notification) succeeds
        self.mock_sqs_client.send_message.side_effect = [
            Exception("SQS send_message for calendar failed"), 
            {'MessageId': 'sqs-message-id-notification'}
        ]

        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 200) # Still 200 as booking confirmed, SQS error logged
        self.assertIn(f"Booking {booking_id} confirmed successfully", response['body'])
        
        self.mock_appointments_table.update_item.assert_called_once()
        self.assertEqual(self.mock_sqs_client.send_message.call_count, 2)
        
        # Check that the second call was to the notification queue
        notification_sqs_call = self.mock_sqs_client.send_message.call_args_list[1] # Second call
        self.assertEqual(notification_sqs_call[1]['QueueUrl'], 'mock_notification_sqs_url')

    def test_missing_path_parameter_id(self):
        event = { "pathParameters": {} } # Missing 'id'
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 400)
        self.assertIn("Missing booking ID in request path.", response['body'])

    def test_missing_environment_variables(self):
        # Temporarily remove an environment variable
        original_val = os.environ.pop('APPOINTMENTS_TABLE_NAME', None)
        
        # Need to reload the lambda_function module for it to pick up changed env vars at module level
        # For this test, we'll assume the check is robust enough at the start of the handler.
        # If APPOINTMENTS_TABLE_NAME is used to initialize dynamodb.Table() at global scope in lambda,
        # this test would need more complex module reloading.
        # Our current lambda_function.py initializes table inside handler.
        
        booking_id = "booking_env_error"
        event = self._create_api_gateway_event(booking_id)
        
        response = self.lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 500)
        self.assertIn("Configuration error", response['body'])
        
        # Restore environment variable
        if original_val is not None:
            os.environ['APPOINTMENTS_TABLE_NAME'] = original_val


if __name__ == '__main__':
    unittest.main(verbosity=2)

# To run these tests:
# Ensure you are in the project root directory.
# python -m unittest backend.confirm_appointment_lambda.test_lambda_function
# or if structure allows, just from root:
# python -m unittest discover -s backend/confirm_appointment_lambda -p "test_*.py"
# Ensure __init__.py files are present in backend and backend.confirm_appointment_lambda for discovery.
# (No, for `python -m unittest backend.confirm_appointment_lambda.test_lambda_function` it's fine)
# If lambda_function.py is at the root of confirm_appointment_lambda, then from root:
# python -m unittest backend.confirm_appointment_lambda.test_lambda_function

# If you have __init__.py in backend/ and backend/confirm_appointment_lambda/
# you can run from project root:
# python -m unittest backend.confirm_appointment_lambda.test_lambda_function
# Make sure PYTHONPATH includes the project root or that the IDE handles it.
# For example, if project root is /path/to/project, then
# PYTHONPATH=/path/to/project python -m unittest backend.confirm_appointment_lambda.test_lambda_function
# Or, more simply, `cd` into the `backend` directory and run:
# python -m unittest confirm_appointment_lambda.test_lambda_function
# Or, `cd` into `backend/confirm_appointment_lambda` and run:
# python -m unittest test_lambda_function
# Best practice is usually to run from project root with proper module paths.

# Assuming standard project structure where 'backend' is a top-level package:
# (Project Root)
# |-- backend
# |   |-- __init__.py (optional, for older Python or namespace pkg)
# |   |-- confirm_appointment_lambda
# |   |   |-- __init__.py (make this a package)
# |   |   |-- lambda_function.py
# |   |   |-- test_lambda_function.py
# |   |   |-- requirements.txt
# |   |-- handle_cancellation_lambda
# |   |   |-- __init__.py (make this a package)
# |   |   |-- lambda_function.py
# |   |   |-- test_lambda_function.py (to be created)

# To run from project root:
# PYTHONPATH=. python -m unittest backend.confirm_appointment_lambda.test_lambda_function
# The PYTHONPATH=. tells Python to look for modules in the current directory.
# Or, if your test runner (like VSCode's test explorer) is configured correctly, it should just work.
# For pytest, it generally handles paths better automatically.
# pytest backend/confirm_appointment_lambda/test_lambda_function.py
