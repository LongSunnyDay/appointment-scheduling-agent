# Terraform configuration for AWS Secrets Manager - Placeholders

# This file defines placeholders for AWS Secrets Manager secrets.
# The actual secret values (secret_string) are NOT populated here via Terraform
# due to their sensitive nature. They should be populated securely either:
# 1. Manually via the AWS Management Console after the secret resource is created.
# 2. Via AWS CLI or SDKs in a secure pipeline (e.g., CI/CD) after initial creation.

# --- Placeholder for Google Calendar API Credentials ---
resource "aws_secretsmanager_secret" "google_calendar_api_credentials" {
  name        = "GoogleCalendarApiCredentials"
  description = "Stores credentials for accessing the Google Calendar API (e.g., OAuth tokens, service account key JSON)."

  # The actual secret_string (e.g., JSON content) is not set here.
  # It should be populated securely in AWS Secrets Manager after creation.

  tags = {
    Name        = "GoogleCalendarApiCredentials"
    Environment = "dev" # Or "prod", depending on the environment
    Project     = "ClientRegistration"
    Purpose     = "Google Calendar Integration"
  }
}

# --- Placeholder for Large Language Model (LLM) API Key ---
resource "aws_secretsmanager_secret" "llm_api_key" {
  name        = "LlmApiKey"
  description = "Stores the API key for accessing a Large Language Model (e.g., OpenAI, Anthropic)."

  # The actual secret_string (API key) is not set here.
  # It should be populated securely in AWS Secrets Manager after creation.

  tags = {
    Name        = "LlmApiKey"
    Environment = "dev"
    Project     = "ClientRegistration"
    Purpose     = "AI Agent LLM Access"
  }
}

# --- Placeholder for Facebook API Token ---
resource "aws_secretsmanager_secret" "facebook_api_token" {
  name        = "FacebookApiToken"
  description = "Stores the API token for accessing the Facebook Graph API (e.g., for webhook validation, page interactions)."

  # The actual secret_string (API token) is not set here.
  # It should be populated securely in AWS Secrets Manager after creation.

  tags = {
    Name        = "FacebookApiToken"
    Environment = "dev"
    Project     = "ClientRegistration"
    Purpose     = "Facebook Integration"
  }
}

# --- Placeholder for Instagram API Token ---
resource "aws_secretsmanager_secret" "instagram_api_token" {
  name        = "InstagramApiToken"
  description = "Stores the API token for accessing the Instagram Graph API (e.g., for webhook validation, content posting)."

  # The actual secret_string (API token) is not set here.
  # It should be populated securely in AWS Secrets Manager after creation.

  tags = {
    Name        = "InstagramApiToken"
    Environment = "dev"
    Project     = "ClientRegistration"
    Purpose     = "Instagram Integration"
  }
}

# Reminder: After Terraform applies these changes, navigate to AWS Secrets Manager
# in the AWS Console (or use AWS CLI) to set the actual secret values for each
# of these secrets. Access to these secrets should be tightly controlled via IAM policies.
