# Terraform configuration for IAM Roles

# --- IAM Role for Lambda Function Execution ---
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

# --- Attach Logging Policy to Lambda Execution Role ---
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
