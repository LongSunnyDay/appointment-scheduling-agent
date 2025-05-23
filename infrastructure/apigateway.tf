# Terraform configuration for API Gateway (HTTP API)

# --- API Gateway v2 HTTP API ---
resource "aws_apigatewayv2_api" "main_api" {
  name          = "ClientRegistrationAPI"
  protocol_type = "HTTP"
  description   = "Main API Gateway for client registration and related services."

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

# --- Placeholder for Routes and Integrations ---

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

# - POST /bookings
# resource "aws_apigatewayv2_route" "create_booking_route" {
#   api_id    = aws_apigatewayv2_api.main_api.id
#   route_key = "POST /bookings"
# }
# resource "aws_apigatewayv2_integration" "create_booking_integration" {
#   api_id           = aws_apigatewayv2_api.main_api.id
#   integration_type = "AWS_PROXY"
#   integration_uri  = module.bookings_lambda.function_arn # Example
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
