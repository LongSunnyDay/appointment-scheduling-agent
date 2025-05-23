# Terraform configuration for AWS CloudWatch Log Groups and Alarms (Placeholders)

# This file defines CloudWatch Log Groups for Lambda functions.
# It also includes a note about the importance of setting up CloudWatch Alarms
# for monitoring critical metrics, which should be implemented as the system matures.

# --- CloudWatch Log Groups for Lambda Functions ---
# A log group is created for each Lambda function to store its execution logs.
# Log retention is set to 14 days as an example; adjust as needed.

resource "aws_cloudwatch_log_group" "langchain_ai_agent_lambda_logs" {
  name              = "/aws/lambda/LangchainAIAgentLambda"
  retention_in_days = 14

  tags = {
    Name        = "LangchainAIAgentLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "create_booking_lambda_logs" {
  name              = "/aws/lambda/CreateBookingLambda"
  retention_in_days = 14

  tags = {
    Name        = "CreateBookingLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "get_availability_lambda_logs" {
  name              = "/aws/lambda/GetAvailabilityLambda"
  retention_in_days = 14

  tags = {
    Name        = "GetAvailabilityLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "handle_cancellation_lambda_logs" {
  name              = "/aws/lambda/HandleCancellationLambda"
  retention_in_days = 14

  tags = {
    Name        = "HandleCancellationLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "confirm_appointment_lambda_logs" {
  name              = "/aws/lambda/ConfirmAppointmentLambda"
  retention_in_days = 14

  tags = {
    Name        = "ConfirmAppointmentLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "get_services_lambda_logs" {
  name              = "/aws/lambda/GetServicesLambda"
  retention_in_days = 14

  tags = {
    Name        = "GetServicesLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "get_locations_lambda_logs" {
  name              = "/aws/lambda/GetLocationsLambda"
  retention_in_days = 14

  tags = {
    Name        = "GetLocationsLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "google_calendar_sync_lambda_logs" {
  name              = "/aws/lambda/GoogleCalendarSyncLambda"
  retention_in_days = 14

  tags = {
    Name        = "GoogleCalendarSyncLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

resource "aws_cloudwatch_log_group" "notification_lambda_logs" {
  name              = "/aws/lambda/NotificationLambda"
  retention_in_days = 14

  tags = {
    Name        = "NotificationLambda-LogGroup"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- CloudWatch Alarms (Placeholder Note) ---
# IMPORTANT: Comprehensive monitoring and alerting are crucial for a production system.
# This initial setup does not define specific CloudWatch Alarms.
# As the project evolves, alarms should be configured for key metrics, including but not limited to:
#   - Lambda Function Errors (AWS/Lambda Namespace, Errors metric)
#   - Lambda Function Throttling (AWS/Lambda Namespace, Throttles metric)
#   - Lambda Function Duration (AWS/Lambda Namespace, Duration metric, for performance monitoring)
#   - API Gateway 4XX/5XX Errors (AWS/ApiGateway Namespace, 4XXError, 5XXError metrics)
#   - API Gateway Latency (AWS/ApiGateway Namespace, Latency metric)
#   - SQS Queue Depth (AWS/SQS Namespace, ApproximateNumberOfMessagesVisible metric for all queues and DLQs)
#   - SQS Age of Oldest Message (AWS/SQS Namespace, ApproximateAgeOfOldestMessage metric for DLQs)
#   - DynamoDB Read/Write Capacity Issues (AWS/DynamoDB Namespace, ReadThrottleEvents, WriteThrottleEvents)
#   - DynamoDB System Errors (AWS/DynamoDB Namespace, SystemErrors)
#   - Application-specific custom metrics (e.g., number of bookings, failed payments, etc.)
#
# These alarms should be configured with appropriate thresholds and notification actions
# (e.g., notifying the StaffNotificationTopic SNS topic or specific operational channels).
