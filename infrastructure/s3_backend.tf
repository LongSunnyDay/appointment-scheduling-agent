# Terraform configuration for S3 Backend State Storage and DynamoDB Lock Table

# --- S3 Bucket for Terraform State ---
# This S3 bucket will store the Terraform state file.
# IMPORTANT: Bucket names must be globally unique.
# Please replace "your-unique-terraform-state-bucket-name" with a unique name for your bucket.
resource "aws_s3_bucket" "terraform_state_bucket" {
  bucket = "your-unique-terraform-state-bucket-name" # CHANGE TO A GLOBALLY UNIQUE NAME

  # Enable versioning to keep history of state files
  versioning_configuration {
    status = "Enabled"
  }

  # Enable server-side encryption by default
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  # It's good practice to block public access, though by default new S3 buckets
  # have public access blocked. Explicitly defining it is safer.
  # block_public_acls       = true
  # block_public_policy     = true
  # ignore_public_acls      = true
  # restrict_public_buckets = true

  tags = {
    Name        = "TerraformStateBucket"
    Environment = "infra"
    Purpose     = "Terraform State Storage"
  }
}

# --- DynamoDB Table for Terraform State Locking ---
# This DynamoDB table is used by Terraform to lock the state file,
# preventing concurrent modifications which can lead to corruption.
resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "TerraformStateLock"
  billing_mode = "PAY_PER_REQUEST" # Cost-effective for infrequent access
  hash_key     = "LockID"         # Terraform expects this specific hash key name

  attribute {
    name = "LockID"
    type = "S" # String
  }

  tags = {
    Name        = "TerraformStateLockTable"
    Environment = "infra"
    Purpose     = "Terraform State Locking"
  }
}

# --- Terraform Backend Configuration (Instructions) ---
# The following 'terraform' block should be placed in your main Terraform
# configuration file (e.g., main.tf, backend.tf, or a dedicated provider.tf).
# It configures Terraform to use the S3 bucket and DynamoDB table defined above
# for state management. Make sure to update the 'bucket' name if you changed it.

# terraform {
#   backend "s3" {
#     bucket         = "your-unique-terraform-state-bucket-name" # Ensure this matches your S3 bucket name
#     key            = "global/s3/terraform.tfstate"             # Example path for the state file in the bucket
#     region         = "us-east-1"                               # Change to your desired AWS region
#     dynamodb_table = "TerraformStateLock"                      # Matches the DynamoDB table name defined above
#     encrypt        = true                                      # Encrypts the state file
#   }
# }
