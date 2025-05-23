# Terraform configuration for AWS DynamoDB Tables

# --- Appointments Table ---
# Stores information about client bookings/appointments.
resource "aws_dynamodb_table" "appointments_table" {
  name         = "AppointmentsTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "bookingId"

  attribute {
    name = "bookingId"
    type = "S" # String
  }
  attribute {
    name = "clientId"
    type = "S"
  }
  attribute {
    name = "serviceName" # Denormalized for quick lookups, actual details in ServicesTable
    type = "S"
  }
  attribute {
    name = "locationId"
    type = "S"
  }
  attribute {
    name = "proposedStartTime" # ISO 8601 format, e.g., "2024-07-30T14:30:00Z"
    type = "S"
  }
  attribute {
    name = "status" # e.g., "pending_confirmation", "confirmed", "cancelled", "completed"
    type = "S"
  }
  attribute {
    name = "googleCalendarEventId" # Optional, if synced with Google Calendar
    type = "S"
  }
  attribute {
    name = "createdAt" # ISO 8601 format
    type = "S"
  }

  # Global Secondary Index for querying appointments by location and time.
  # Useful for finding appointments at a specific location within a time range.
  global_secondary_index {
    name            = "LocationTimeIndex"
    hash_key        = "locationId"
    range_key       = "proposedStartTime"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying appointments by status and creation date.
  # Useful for finding appointments with a certain status, ordered by when they were created.
  global_secondary_index {
    name            = "StatusCreatedAtIndex"
    hash_key        = "status"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  tags = {
    Name        = "AppointmentsTable"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Services Table ---
# Stores details about the services offered.
resource "aws_dynamodb_table" "services_table" {
  name         = "ServicesTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "serviceId"

  attribute {
    name = "serviceId"
    type = "S"
  }
  attribute {
    name = "serviceName"
    type = "S"
  }
  attribute {
    name = "description"
    type = "S"
  }
  attribute {
    name = "durationMinutes"
    type = "N" # Number
  }
  attribute {
    name = "bufferMinutesBetweenAppointments"
    type = "N"
  }
  attribute {
    name = "price" # Stored as a number, e.g., cents or a decimal representation
    type = "N"
  }

  tags = {
    Name        = "ServicesTable"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}

# --- Locations Table ---
# Stores details about business locations.
resource "aws_dynamodb_table" "locations_table" {
  name         = "LocationsTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "locationId"

  attribute {
    name = "locationId"
    type = "S"
  }
  attribute {
    name = "locationName"
    type = "S"
  }
  attribute {
    name = "address"
    type = "S"
  }
  attribute {
    name = "googleCalendarId" # Specific Google Calendar ID for this location
    type = "S"
  }
  attribute {
    name = "operatingHours" # e.g., "Mon-Fri 9am-5pm, Sat 10am-2pm" or JSON string
    type = "S"
  }

  tags = {
    Name        = "LocationsTable"
    Environment = "dev"
    Project     = "ClientRegistration"
  }
}
