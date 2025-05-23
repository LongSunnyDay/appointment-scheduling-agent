# Terraform configuration for IAM Roles

# --- Variable Definitions ---
variable "appointments_table_arn" {
  description = "ARN of the Appointments DynamoDB table"
  type        = string
  default     = "arn:aws:dynamodb:us-east-1:123456789012:table/AppointmentsTable" # Replace with actual region/account or use data source/output from dynamodb.tf
}

variable "services_table_arn" {
  description = "ARN of the Services DynamoDB table"
  type        = string
  default     = "arn:aws:dynamodb:us-east-1:123456789012:table/ServicesTable" # Replace
}

variable "locations_table_arn" {
  description = "ARN of the Locations DynamoDB table"
  type        = string
  default     = "arn:aws:dynamodb:us-east-1:123456789012:table/LocationsTable" # Replace
}

variable "booking_notification_queue_arn" {
  description = "ARN of the SQS queue for booking notifications"
  type        = string
  default     = "arn:aws:sqs:us-east-1:123456789012:BookingNotificationQueueName" # Replace
}

variable "google_calendar_api_key_secret_arn_pattern" {
  description = "ARN pattern for Secrets Manager secrets holding Google Calendar API Key"
  type        = string
  default     = "arn:aws:secretsmanager:us-east-1:123456789012:secret:GoogleCalendarAPIKey-*" # Replace region/account
}

# --- IAM Role for Lambda Function Execution (General Purpose) ---
resource "aws_iam_role" "lambda_execution_role" {
  name = "lambda_execution_role"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "lambda-execution-role"
  }
}

# --- IAM Policy for Basic Lambda CloudWatch Logging ---
resource "aws_iam_policy" "lambda_logging_policy" {
  name        = "lambda_logging_policy"
  description = "Allows Lambda functions to write logs to CloudWatch."

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*" # Restrict if possible, but often broad for general logging
      }
    ]
  })
}

# --- Attach Logging Policy to General Lambda Execution Role ---
resource "aws_iam_role_policy_attachment" "lambda_logging_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_logging_policy.arn
}

# Placeholder comment for additional permissions for lambda_execution_role
# Specific permissions for services like DynamoDB, SQS, SNS, Secrets Manager,
# and Google Calendar API will be added/refined here as individual policies
# or by updating the main role's inline policies once requirements are clearer.

# --- IAM Role for API Gateway to Invoke Lambda Functions ---
resource "aws_iam_role" "api_gateway_invoke_lambda_role" {
  name = "api_gateway_invoke_lambda_role"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "api-gateway-invoke-lambda-role"
  }
}

# --- IAM Policy for API Gateway to Invoke Lambda ---
# This policy allows API Gateway to invoke any Lambda function.
# It's a broad permission and should be refined if specific Lambda functions
# are known, or by using resource-based policies on the Lambda functions themselves.
resource "aws_iam_policy" "apigateway_lambda_invoke_policy" {
  name        = "apigateway_lambda_invoke_policy"
  description = "Allows API Gateway to invoke Lambda functions."

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action   = "lambda:InvokeFunction",
        Effect   = "Allow",
        Resource = "*" # Restrict this to specific Lambda ARNs if possible
      }
    ]
  })
}

# --- Attach Lambda Invoke Policy to API Gateway Role ---
resource "aws_iam_role_policy_attachment" "apigateway_lambda_invoke_attachment" {
  role       = aws_iam_role.api_gateway_invoke_lambda_role.name
  policy_arn = aws_iam_policy.apigateway_lambda_invoke_policy.arn
}

# --- IAM Role for Booking API Lambda Function ---
resource "aws_iam_role" "lambda_booking_api_role" {
  name = "lambda_booking_api_role"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name    = "lambda-booking-api-role"
    Project = "DetailingCenter"
  }
}

# --- Attach Logging Policy to Booking API Lambda Role ---
resource "aws_iam_role_policy_attachment" "lambda_booking_api_logging_attachment" {
  role       = aws_iam_role.lambda_booking_api_role.name
  policy_arn = aws_iam_policy.lambda_logging_policy.arn
}

# --- IAM Policy for Booking API Lambda to Access DynamoDB ---
resource "aws_iam_policy" "lambda_booking_api_dynamodb_policy" {
  name        = "lambda_booking_api_dynamodb_policy"
  description = "Allows Lambda to access specific DynamoDB tables for the booking API."

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        Effect   = "Allow",
        Resource = [
          var.appointments_table_arn,
          "${var.appointments_table_arn}/index/*", # Allow access to GSIs
          var.services_table_arn,
          "${var.services_table_arn}/index/*",
          var.locations_table_arn,
          "${var.locations_table_arn}/index/*"
        ]
      }
    ]
  })
}

# --- Attach DynamoDB Policy to Booking API Lambda Role ---
resource "aws_iam_role_policy_attachment" "lambda_booking_api_dynamodb_attachment" {
  role       = aws_iam_role.lambda_booking_api_role.name
  policy_arn = aws_iam_policy.lambda_booking_api_dynamodb_policy.arn
}

# --- IAM Policy for Booking API Lambda to Access SQS ---
resource "aws_iam_policy" "lambda_booking_api_sqs_policy" {
  name        = "lambda_booking_api_sqs_policy"
  description = "Allows Lambda to send messages to an SQS queue."

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action   = "sqs:SendMessage",
        Effect   = "Allow",
        Resource = var.booking_notification_queue_arn
      }
    ]
  })
}

# --- Attach SQS Policy to Booking API Lambda Role ---
resource "aws_iam_role_policy_attachment" "lambda_booking_api_sqs_attachment" {
  role       = aws_iam_role.lambda_booking_api_role.name
  policy_arn = aws_iam_policy.lambda_booking_api_sqs_policy.arn
}

# --- IAM Policy for Booking API Lambda to Access Secrets Manager ---
resource "aws_iam_policy" "lambda_booking_api_secrets_policy" {
  name        = "lambda_booking_api_secrets_policy"
  description = "Allows Lambda to get specific secrets from Secrets Manager."

  policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action   = "secretsmanager:GetSecretValue",
        Effect   = "Allow",
        Resource = var.google_calendar_api_key_secret_arn_pattern
      }
    ]
  })
}

# --- Attach Secrets Manager Policy to Booking API Lambda Role ---
resource "aws_iam_role_policy_attachment" "lambda_booking_api_secrets_attachment" {
  role       = aws_iam_role.lambda_booking_api_role.name
  policy_arn = aws_iam_policy.lambda_booking_api_secrets_policy.arn
}
