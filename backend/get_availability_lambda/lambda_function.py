import json
import logging
import os
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
# boto3 might be used by other AWS SDK features if the lambda expands, but not directly for GCal.
# For now, it's not strictly necessary for the described GCal logic.
# import boto3 

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # --- 1. Retrieve and Validate Query Parameters ---
        params = event.get('queryStringParameters', {})
        if not params:
            logger.warning("Missing queryStringParameters.")
            return {"statusCode": 400, "body": json.dumps({"error": "Missing query string parameters."})}

        calendar_id = params.get('calendar_id')
        start_time_iso = params.get('start_time_iso')
        end_time_iso = params.get('end_time_iso')
        service_duration_str = params.get('service_duration_minutes')
        buffer_minutes_str = params.get('buffer_minutes_between_appointments')

        required_params = {
            "calendar_id": calendar_id,
            "start_time_iso": start_time_iso,
            "end_time_iso": end_time_iso,
            "service_duration_minutes": service_duration_str,
            "buffer_minutes_between_appointments": buffer_minutes_str
        }
        missing_params = [key for key, value in required_params.items() if not value]
        if missing_params:
            logger.warning(f"Missing required query parameters: {', '.join(missing_params)}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing required query parameters: {', '.join(missing_params)}"})
            }

        try:
            service_duration_minutes = int(service_duration_str)
            buffer_minutes_between_appointments = int(buffer_minutes_str)
            if service_duration_minutes <= 0 or buffer_minutes_between_appointments < 0:
                raise ValueError("Durations must be positive.")
        except ValueError:
            logger.warning("Invalid duration or buffer minutes. Must be integers.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "service_duration_minutes and buffer_minutes_between_appointments must be valid integers."})
            }

        try:
            # Ensure times are timezone-aware (UTC) for consistency
            start_datetime_dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
            end_datetime_dt = datetime.fromisoformat(end_time_iso.replace('Z', '+00:00'))
            if start_datetime_dt.tzinfo is None or start_datetime_dt.tzinfo.utcoffset(start_datetime_dt) != timezone.utc:
                 start_datetime_dt = start_datetime_dt.astimezone(timezone.utc)
            if end_datetime_dt.tzinfo is None or end_datetime_dt.tzinfo.utcoffset(end_datetime_dt) != timezone.utc:
                end_datetime_dt = end_datetime_dt.astimezone(timezone.utc)
        except ValueError:
            logger.warning("Invalid ISO time format for start_time_iso or end_time_iso.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid ISO time format. Use YYYY-MM-DDTHH:MM:SSZ."})
            }

        # --- 2. Load Google Credentials ---
        credentials_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if not credentials_json_str:
            logger.error("GOOGLE_APPLICATION_CREDENTIALS_JSON env var not set.")
            return {"statusCode": 500, "body": json.dumps({"error": "Google credentials not configured."})}
        
        try:
            credentials_info = json.loads(credentials_json_str)
            creds = service_account.Credentials.from_service_account_info(credentials_info)
        except Exception as e:
            logger.error(f"Error loading Google credentials: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to load Google credentials."})}

        # --- 3. Build Google Calendar Service ---
        try:
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        except Exception as e: # Broad exception for build issues
            logger.error(f"Failed to build Google Calendar service: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to initialize Google Calendar service."})}

        # --- 4. Prepare and Call FreeBusy API ---
        freebusy_query_body = {
            "timeMin": start_datetime_dt.isoformat(), # Use validated and timezone-aware dt objects
            "timeMax": end_datetime_dt.isoformat(),
            "items": [{"id": calendar_id}],
            # "timeZone": "UTC" # timeMin/Max are already in UTC. FreeBusy respects this.
        }
        
        logger.info(f"Querying FreeBusy for calendar {calendar_id} from {freebusy_query_body['timeMin']} to {freebusy_query_body['timeMax']}")
        
        try:
            events_result = service.freebusy().query(body=freebusy_query_body).execute()
        except HttpError as e:
            logger.error(f"Google Calendar API HttpError: {e.content}")
            error_details = json.loads(e.content.decode('utf-8')).get('error', {})
            error_message = error_details.get('message', 'Unknown Google Calendar API error.')
            if e.resp.status == 404:
                 error_message = f"Calendar ID '{calendar_id}' not found or access denied."
            return {"statusCode": e.resp.status, "body": json.dumps({"error": f"Google Calendar API error: {error_message}"})}
        
        busy_slots_raw = events_result.get('calendars', {}).get(calendar_id, {}).get('busy', [])
        logger.info(f"Received {len(busy_slots_raw)} busy slots from GCal.")

        # --- 5. Availability Logic ---
        available_slots_iso = []
        current_time_dt = start_datetime_dt
        slot_duration_total = timedelta(minutes=(service_duration_minutes + buffer_minutes_between_appointments))
        
        # Define business hours (example: 9 AM to 6 PM UTC, Mon-Sat)
        # These should ideally be configurable per location/calendar
        min_business_hour_utc = int(os.environ.get("MIN_BUSINESS_HOUR_UTC", 9))
        max_business_hour_utc = int(os.environ.get("MAX_BUSINESS_HOUR_UTC", 18)) # Slot must END by max_hour
        # Weekday: 0=Mon, 5=Sat, 6=Sun
        min_business_weekday = int(os.environ.get("MIN_BUSINESS_WEEKDAY", 0)) # Monday
        max_business_weekday = int(os.environ.get("MAX_BUSINESS_WEEKDAY", 5)) # Saturday

        # Convert busy_slots_raw to datetime objects for easier comparison
        busy_slots = []
        for busy_event in busy_slots_raw:
            try:
                busy_start = datetime.fromisoformat(busy_event['start'].replace('Z', '+00:00'))
                busy_end = datetime.fromisoformat(busy_event['end'].replace('Z', '+00:00'))
                busy_slots.append({'start': busy_start.astimezone(timezone.utc), 'end': busy_end.astimezone(timezone.utc)})
            except ValueError:
                logger.warning(f"Skipping busy slot with invalid time format: {busy_event}")
                continue

        iteration_increment = timedelta(minutes=15) # Check availability at 15-minute intervals

        while current_time_dt + slot_duration_total <= end_datetime_dt:
            potential_slot_start = current_time_dt
            potential_slot_end = current_time_dt + slot_duration_total

            # Check business hours and day
            # Ensure the entire slot (start and end) is within business hours
            is_within_business_hours = (
                min_business_hour_utc <= potential_slot_start.hour and
                potential_slot_end.hour < max_business_hour_utc or 
                (potential_slot_end.hour == max_business_hour_utc and potential_slot_end.minute == 0) # Slot can end exactly at max_business_hour_utc:00
            )
            is_business_day = (
                min_business_weekday <= potential_slot_start.weekday() <= max_business_weekday and
                min_business_weekday <= potential_slot_end.weekday() <= max_business_weekday # Ensure end also on business day
            )

            if not (is_within_business_hours and is_business_day):
                current_time_dt += iteration_increment
                continue

            is_busy = False
            for busy_event in busy_slots:
                # Check for overlap: (StartA < EndB) and (EndA > StartB)
                if (potential_slot_start < busy_event['end'] and potential_slot_end > busy_event['start']):
                    is_busy = True
                    # logger.debug(f"Slot [{potential_slot_start.isoformat()}-{potential_slot_end.isoformat()}] overlaps with busy [{busy_event['start'].isoformat()}-{busy_event['end'].isoformat()}]")
                    break 
            
            if not is_busy:
                available_slots_iso.append(potential_slot_start.isoformat())
            
            current_time_dt += iteration_increment
        
        logger.info(f"Found {len(available_slots_iso)} available slots for calendar '{calendar_id}'.")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"availableSlots": available_slots_iso})
        }

    except json.JSONDecodeError as e: # For issues with loading GOOGLE_APPLICATION_CREDENTIALS_JSON
        logger.error(f"JSONDecodeError: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Invalid JSON format in credentials."})}
    except ValueError as e: # Catch other ValueErrors (e.g., from datetime parsing if not caught earlier)
        logger.error(f"ValueError: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid value provided: {str(e)}."})}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "An unexpected server error occurred."})
        }
