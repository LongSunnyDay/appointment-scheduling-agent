# Terraform configuration for AWS SQS Queues

# --- Booking Request Queue (FIFO) ---
# This queue handles incoming booking requests. It's a FIFO queue to ensure
# requests are processed in the order they are received.
resource "aws_sqs_queue" "booking_request_queue" {
  name                        = "BookingRequestQueue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true # Useful if message producers might send duplicates
  visibility_timeout_seconds  = 300  # 5 minutes; adjust based on expected processing time

  # Redrive policy specifies the DLQ for messages that fail processing.
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.booking_request_dlq.arn
    maxReceiveCount     = 5 # Number of times a message is delivered before being sent to DLQ
  })

  tags = {
    Name        = "BookingRequestQueue"
    Environment = "dev"
    Project     = "ClientRegistration"
    Type        = "FIFO"
  }
}

# --- Booking Request Dead Letter Queue (FIFO) ---
# Stores messages from BookingRequestQueue that failed processing multiple times.
resource "aws_sqs_queue" "booking_request_dlq" {
  name       = "BookingRequestDLQ.fifo"
  fifo_queue = true # DLQ for a FIFO queue must also be FIFO

  # Consider setting a message retention period appropriate for investigation
  # message_retention_seconds = 1209600 # 14 days (example)

  tags = {
    Name        = "BookingRequestDLQ"
    Environment = "dev"
    Project     = "ClientRegistration"
    Type        = "FIFO-DLQ"
  }
}

# --- Notification Queue (Standard) ---
# This queue handles messages for sending notifications (e.g., email, SMS).
# Order is not strictly critical, so a standard queue is used for higher throughput.
resource "aws_sqs_queue" "notification_queue" {
  name                       = "NotificationQueue"
  visibility_timeout_seconds = 180 # 3 minutes; adjust based on notification sending time

  # Redrive policy for messages that fail processing (e.g., email service temporary failure).
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notification_dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Name        = "NotificationQueue"
    Environment = "dev"
    Project     = "ClientRegistration"
    Type        = "Standard"
  }
}

# --- Notification Dead Letter Queue (Standard) ---
# Stores messages from NotificationQueue that failed processing multiple times.
resource "aws_sqs_queue" "notification_dlq" {
  name = "NotificationDLQ"

  # message_retention_seconds = 1209600 # 14 days (example)

  tags = {
    Name        = "NotificationDLQ"
    Environment = "dev"
    Project     = "ClientRegistration"
    Type        = "Standard-DLQ"
  }
}
