# Terraform configuration for API Gateway (HTTP API)

variable "create_booking_lambda_arn" {
  description = "ARN of the Create Booking Lambda function"
  type        = string
  # Example default - replace with actual ARN or mechanism to get it (e.g., data source, module output)
  default     = "arn:aws:lambda:us-east-1:123456789012:function:create_booking_lambda_name_placeholder"
}

# --- API Gateway v2 HTTP API ---
resource "aws_apigatewayv2_api" "main_api" {
  name          = "ClientRegistrationAPI"
  protocol_type = "HTTP"
  description   = "Main API Gateway for client registration and related services."

  cors_configuration {
    allow_origins = ["*"] # For development; restrict in production
    allow_methods = ["POST", "GET", "OPTIONS", "PUT", "DELETE", "PATCH"] # Added GET, OPTIONS and other common methods
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"] # Common headers
    expose_headers = ["Date", "Content-Length"]
    max_age = 300
  }

  tags = {
    Name = "client-registration-api"
  }
}

# --- Default Stage for the API ---
# This stage is automatically deployed on changes.
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.main_api.id
  name        = "$default" # Special name for the default stage
  auto_deploy = true

  # Access logs can be configured here if needed in the future
  # access_log_settings {
  #   destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn # Example
  #   format          = "$context.identity.sourceIp - $context.identity.caller - [$context.requestTime] \"$context.httpMethod $context.resourcePath $context.protocol\" $context.status $context.responseLength $context.requestId"
  # }

  tags = {
    Name = "default-stage"
  }
}

# --- Integration for POST /bookings ---
resource "aws_apigatewayv2_integration" "post_bookings_integration" {
  api_id           = aws_apigatewayv2_api.main_api.id
  integration_type = "AWS_PROXY" # For Lambda integration
  integration_uri  = var.create_booking_lambda_arn
  payload_format_version = "2.0"       # Recommended for new Lambda integrations
}

# --- Route for POST /bookings ---
resource "aws_apigatewayv2_route" "post_bookings_route" {
  api_id    = aws_apigatewayv2_api.main_api.id
  route_key = "POST /bookings"
  target    = "integrations/${aws_apigatewayv2_integration.post_bookings_integration.id}"
}


# --- Placeholder for Other Routes and Integrations ---

# TODO: Add routes and integrations for Webhook Endpoints
# - Instagram Webhook
# - Facebook Webhook
# Example:
# resource "aws_apigatewayv2_route" "instagram_webhook_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "POST /webhooks/instagram"
# }
# resource "aws_apigatewayv2_integration" "instagram_webhook_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY" # Assuming Lambda integration
#   integration_uri  = module.instagram_webhook_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }
# resource "aws_apigatewayv2_route" "facebook_webhook_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "POST /webhooks/facebook"
# }
# resource "aws_apigatewayv2_integration" "facebook_webhook_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY" # Assuming Lambda integration
#   integration_uri  = module.facebook_webhook_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }


# TODO: Add route and integration for Website Chat Endpoint
# Example:
# resource "aws_apigatewayv2_route" "website_chat_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "POST /chat/message" # Or WebSocket route: "$connect", "$disconnect", "$default"
# }
# resource "aws_apigatewayv2_integration" "website_chat_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY" # Assuming Lambda integration for chat messages
#   integration_uri  = module.chat_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }


# TODO: Add routes and integrations for Backend API Endpoints
# These will likely integrate with Lambda functions in the 'backend' module.

# - GET /services
# resource "aws_apigatewayv2_route" "get_services_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "GET /services"
# }
# resource "aws_apigatewayv2_integration" "get_services_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY"
#   integration_uri  = module.services_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }

# - GET /locations
# resource "aws_apigatewayv2_route" "get_locations_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "GET /locations"
# }
# resource "aws_apigatewayv2_integration" "get_locations_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY"
#   integration_uri  = module.locations_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }

# - GET /availability
# resource "aws_apigatewayv2_route" "get_availability_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "GET /availability" # Query params for service, location, date range
# }
# resource "aws_apigatewayv2_integration" "get_availability_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY"
#   integration_uri  = module.availability_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }

# - POST /bookings/{id}/confirm
# resource "aws_apigatewayv2_route" "confirm_booking_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "POST /bookings/{id}/confirm"
# }
# resource "aws_apigatewayv2_integration" "confirm_booking_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY"
#   integration_uri  = module.bookings_confirm_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }

# - POST /bookings/{id}/cancel
# resource "aws_apigatewayv2_route" "cancel_booking_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "POST /bookings/{id}/cancel"
# }
# resource "aws_apigatewayv2_integration" "cancel_booking_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY"
#   integration_uri  = module.bookings_cancel_lambda.function_arn # Example
#   payload_format_version = "2.0"
# }

# Note: Lambda function ARNs (integration_uri) used above are illustrative.
# These would typically come from the outputs of Lambda module instantiations.
# Permissions for API Gateway to invoke these Lambdas will also be required,
# often handled by `aws_lambda_permission` resources or by ensuring the
# `api_gateway_invoke_lambda_role` (defined in iam.tf) has the necessary
# `lambda:InvokeFunction` permissions for these specific functions.
