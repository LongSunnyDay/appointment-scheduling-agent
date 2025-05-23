# Terraform configuration for placeholder AWS Lambda Functions
# These definitions are placeholders and will be updated with actual
# deployment packages, specific handlers, and potentially environment variables
# once the Lambda function code is developed.

# --- Placeholder for Langchain AI Agent Lambda ---
resource "aws_lambda_function" "langchain_ai_agent_lambda" {
  function_name = "LangchainAIAgentLambda"
  filename      = "placeholder.zip" # To be replaced with actual package
  source_code_hash = filebase64sha256("placeholder.zip") # To be replaced

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler" # Or specific handler e.g., main.handler
  runtime = "python3.9"

  description = "Placeholder for Langchain AI Agent Lambda. Handles AI-driven interactions."

  tags = {
    Name        = "LangchainAIAgentLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Create Booking Lambda ---
resource "aws_lambda_function" "create_booking_lambda" {
  function_name = "CreateBookingLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Create Booking Lambda. Handles new booking requests."

  tags = {
    Name        = "CreateBookingLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Get Availability Lambda ---
resource "aws_lambda_function" "get_availability_lambda" {
  function_name = "GetAvailabilityLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Get Availability Lambda. Retrieves available slots."

  tags = {
    Name        = "GetAvailabilityLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Handle Cancellation Lambda ---
resource "aws_lambda_function" "handle_cancellation_lambda" {
  function_name = "HandleCancellationLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Handle Cancellation Lambda. Processes booking cancellations."

  tags = {
    Name        = "HandleCancellationLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Confirm Appointment Lambda ---
resource "aws_lambda_function" "confirm_appointment_lambda" {
  function_name = "ConfirmAppointmentLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Confirm Appointment Lambda. Confirms appointments."

  tags = {
    Name        = "ConfirmAppointmentLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Get Services Lambda ---
resource "aws_lambda_function" "get_services_lambda" {
  function_name = "GetServicesLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Get Services Lambda. Retrieves list of available services."

  tags = {
    Name        = "GetServicesLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Get Locations Lambda ---
resource "aws_lambda_function" "get_locations_lambda" {
  function_name = "GetLocationsLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Get Locations Lambda. Retrieves list of business locations."

  tags = {
    Name        = "GetLocationsLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Google Calendar Sync Lambda ---
resource "aws_lambda_function" "google_calendar_sync_lambda" {
  function_name = "GoogleCalendarSyncLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Google Calendar Sync Lambda. Synchronizes bookings with Google Calendar."

  tags = {
    Name        = "GoogleCalendarSyncLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Placeholder for Notification Lambda ---
resource "aws_lambda_function" "notification_lambda" {
  function_name = "NotificationLambda"
  filename      = "placeholder.zip"
  source_code_hash = filebase64sha256("placeholder.zip")

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.9"

  description = "Placeholder for Notification Lambda. Sends notifications (email, SMS) to clients."

  tags = {
    Name        = "NotificationLambda"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# Note: The `aws_iam_role.lambda_execution_role.arn` is referenced from 'iam.tf'.
# Ensure 'iam.tf' is applied first or that this ARN is correctly resolvable.
# The 'placeholder.zip' file needs to exist at the root of your Terraform project
# or in a location accessible by Terraform during planning/applying.
# You can create a dummy zip file: `echo "placeholder" > placeholder.txt; zip placeholder.zip placeholder.txt`
# This helps in validating the Terraform configuration before actual code is ready.
