import json
import logging
import os
import boto3
import uuid
from datetime import datetime, timedelta, timezone

# Initialize logger and environment variables
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

dynamodb = boto3.resource('dynamodb')
appointments_table_name = os.environ.get('APPOINTMENTS_TABLE_NAME')
services_table_name = os.environ.get('SERVICES_TABLE_NAME') # Used by get_service_details

def get_service_details(service_name, db_resource, table_name):
    # Placeholder: In a real scenario, this would query the ServicesTable.
    # For now, it returns a mock duration and buffer.
    # You could extend this to actually query DynamoDB if serviceId is passed.
    logger.info(f"Fetching details for service: {service_name} (mocked from table: {table_name})")
    if service_name == "Full Detail":
        return {"duration_minutes": 180, "buffer_minutes": 30, "price": 250.00}
    elif service_name == "Interior Clean":
        return {"duration_minutes": 90, "buffer_minutes": 15, "price": 120.00}
    else: # Default mock for other services
        return {"duration_minutes": 60, "buffer_minutes": 15, "price": 75.00}

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        if not appointments_table_name:
            logger.error("APPOINTMENTS_TABLE_NAME environment variable not set.")
            # This is a configuration error, so raise it to be caught by the general Exception handler
            raise ValueError("Appointments table name not configured.")

        body = json.loads(event.get('body', '{}'))

        # Required fields validation
        required_fields = ['clientId', 'clientName', 'clientContact', 'serviceName', 'locationId', 'proposedStartTime']
        missing_fields = [field for field in required_fields if not body.get(field)]
        if missing_fields:
            logger.warning(f"Missing required fields: {', '.join(missing_fields)}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Missing required fields: {', '.join(missing_fields)}"})
            }

        clientId = body['clientId']
        clientName = body['clientName']
        clientContact = body['clientContact'] # Expected to be a map
        serviceName = body['serviceName']
        locationId = body['locationId']
        proposedStartTime = body['proposedStartTime'] # ISO format string

        # Validate clientContact structure (basic check)
        if not isinstance(clientContact, dict):
            logger.warning("clientContact is not a valid map.")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "clientContact must be a map (object)."})
            }
        
        # Validate proposedStartTime format (basic check)
        try:
            start_time_dt = datetime.fromisoformat(proposedStartTime.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid proposedStartTime format: {proposedStartTime}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid proposedStartTime format. Please use ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ)."})
            }

        service_details = get_service_details(serviceName, dynamodb, services_table_name)
        if not service_details: # Should not happen with current mock, but good practice
            logger.error(f"Service details not found for: {serviceName}")
            return {
                "statusCode": 404, # Or 400 if considered bad input
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Service '{serviceName}' not found or details unavailable."})
            }

        bookingId = str(uuid.uuid4())

        # Calculate proposedEndTime
        duration = timedelta(minutes=service_details['duration_minutes'])
        # Buffer is not added to the client's booking item's end time, it's for scheduling between appointments.
        end_time_dt = start_time_dt + duration
        proposedEndTime_iso = end_time_dt.isoformat()

        booking_item = {
            'bookingId': bookingId,
            'clientId': clientId,
            'clientName': clientName,
            'clientContact': clientContact,
            'serviceName': serviceName,
            'serviceDurationMinutes': service_details['duration_minutes'],
            'locationId': locationId,
            # 'locationName': body.get('locationName'), # Optional: Add if provided, or fetch based on locationId
            'proposedStartTime': proposedStartTime,
            'proposedEndTime': proposedEndTime_iso,
            'status': 'pending_confirmation', # Initial status
            'bookingChannel': body.get('bookingChannel', 'api'),
            'notes': body.get('notes'), # Optional
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat()
        }

        # Filter out None values to avoid DynamoDB validation errors for optional fields
        booking_item_cleaned = {k: v for k, v in booking_item.items() if v is not None}

        table = dynamodb.Table(appointments_table_name)
        table.put_item(Item=booking_item_cleaned)
        logger.info(f"Booking {bookingId} created successfully and saved to DynamoDB.")

        return {
            "statusCode": 201, # 201 Created
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Booking created successfully. Awaiting confirmation.",
                "bookingId": bookingId,
                "bookingDetails": booking_item_cleaned 
            })
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON format in request body."})
        }
    except KeyError as e:
        logger.error(f"Missing key in request body: {e}")
        # This might be redundant if required_fields check is comprehensive
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Missing expected key in request: {str(e)}"})
        }
    except ValueError as e: # Catch configuration errors or other ValueErrors
        logger.error(f"Value error: {e}")
        return {
            "statusCode": 500, # Server-side issue if it's a config error like missing table name
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Internal configuration error: {str(e)}"})
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "An unexpected error occurred. Please try again later."})
        }
