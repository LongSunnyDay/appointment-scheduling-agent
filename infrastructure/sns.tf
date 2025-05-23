# Terraform configuration for AWS SNS Topics

# --- Client Notification Topic ---
# This SNS topic is used to broadcast notifications intended for clients.
# For example, appointment confirmations, reminders, or cancellation notices.
# Lambda functions or other services can subscribe to this topic to handle
# the actual delivery of notifications (e.g., via email, SMS).
resource "aws_sns_topic" "client_notification_topic" {
  name = "ClientNotificationTopic"
  # display_name = "Client Notifications for Appointment System" # Optional display name

  tags = {
    Name        = "ClientNotificationTopic"
    Environment = "dev"
    Project     = "ClientRegistration"
    Audience    = "Client"
  }
}

# --- Staff Notification Topic ---
# This SNS topic is used to broadcast notifications intended for staff members.
# For example, notifications about new bookings, cancellations, or important system alerts.
# Different staff members or services (e.g., a staff dashboard, email groups)
# can subscribe to this topic based on their needs.
resource "aws_sns_topic" "staff_notification_topic" {
  name = "StaffNotificationTopic"
  # display_name = "Staff Notifications for Appointment System" # Optional display name

  tags = {
    Name        = "StaffNotificationTopic"
    Environment = "dev"
    Project     = "ClientRegistration"
    Audience    = "Staff"
  }
}

# Note on SNS Subscriptions:
# Actual subscriptions (e.g., Lambda functions, SQS queues, email addresses)
# to these topics will be defined elsewhere, typically in the resources
# that need to receive these notifications or in a dedicated 'sns_subscriptions.tf' file.
# For example:
# resource "aws_sns_topic_subscription" "client_email_notification_subscription" {
#   topic_arn = aws_sns_topic.client_notification_topic.arn
#   protocol  = "lambda" # or "email", "sqs", etc.
#   endpoint  = module.notification_lambda.function_arn # Example for Lambda
# }
