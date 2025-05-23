# Langchain Tool: CheckAvailabilityTool

This document describes the conceptual structure and purpose of the `CheckAvailabilityTool` for the AI Booking Agent.

## Tool Purpose

The `CheckAvailabilityTool` is designed to be used by the Langchain agent when it needs to find out what appointment slots are open for a given service, location, and date/time preference.

## Tool Configuration

*   **`name`**: `"CheckAvailabilityTool"`

*   **`description`**: 
    "Use this tool to check for available appointment slots. Input should include the service name (or ID), location name (or ID), and the client's desired date, date range, or general time preference (e.g., 'next Tuesday afternoon'). The tool will return a list of available start times or a message indicating no slots are available."

*   **`args_schema` (Pydantic Model)**:
    The Langchain agent will be expected to provide arguments conforming to this Pydantic model when invoking the tool.

    ```python
    from pydantic import BaseModel, Field

    class CheckAvailabilityArgs(BaseModel):
        service_id: str = Field(description="The unique identifier for the service requested.")
        location_id: str = Field(description="The unique identifier for the detailing center location.")
        # Using specific start and end times for the query window based on user's preference
        # The agent needs to interpret "next Tuesday afternoon" into a concrete window
        date_start_iso: str = Field(description="The start of the desired date/time window in ISO 8601 format (e.g., '2024-08-15T00:00:00Z').")
        date_end_iso: str = Field(description="The end of the desired date/time window in ISO 8601 format (e.g., '2024-08-15T23:59:59Z').")
        # service_duration_minutes: int # This will be fetched by the backend based on service_id
        # buffer_minutes: int # This will be fetched by the backend based on service_id
    ```
    *Note: The agent provides `service_id` and `location_id`. The backend API (`/availability`) will use these to look up the actual service duration, buffer times, and the correct Google Calendar ID for the location to query.*

*   **`_run` Method (Conceptual Implementation)**:
    1.  The `_run(self, service_id: str, location_id: str, date_start_iso: str, date_end_iso: str) -> str` method is invoked by the Langchain agent with the arguments extracted from the user's query.
    2.  **Parameter Preparation**: The method takes the arguments provided by the LLM.
    3.  **API Interaction**:
        *   It makes an HTTPS GET request to the backend `/availability` API endpoint.
        *   The request parameters would be: `?serviceId=<service_id>&locationId=<location_id>&startTime=<date_start_iso>&endTime=<date_end_iso>`.
        *   (Alternative: POST request with a JSON body if parameters become more complex).
    4.  **Authentication**: The API call to `/availability` would be authenticated (e.g., using an API key or IAM if the tool is running in an AWS Lambda environment that can sign requests).
    5.  **Response Parsing**:
        *   The backend API (which in turn calls the Google Calendar availability logic) will return a JSON response.
        *   Example success response: `{"availableSlots": ["2024-08-15T10:00:00Z", "2024-08-15T14:00:00Z"]}`
        *   Example no slots response: `{"availableSlots": []}` or `{"message": "No slots available for the selected criteria."}`
        *   Example error response: `{"error": "Details about the error."}`
    6.  **Output Formatting**:
        *   The `_run` method parses this JSON response.
        *   It formats the list of available slots (or the "no slots" message) into a natural language string that the LLM can understand and relay to the user.
        *   For example: "I found the following available slots: August 15th at 10:00 AM, August 15th at 2:00 PM." or "Unfortunately, there are no slots available for that service at that location on the specified dates."
        *   If an error occurs, it should return a message like: "There was an issue checking availability. Please try again or ask for help from staff."
    7.  **Return Value**: The method returns this formatted string summary to the LLM.

## Backend `/availability` Endpoint (Assumed)

*   **Path**: `GET /availability`
*   **Query Parameters**:
    *   `serviceId` (string, required)
    *   `locationId` (string, required)
    *   `startTime` (string, ISO8601, required) - Start of the window to check.
    *   `endTime` (string, ISO8601, required) - End of the window to check.
*   **Logic**:
    1.  Retrieves `service_duration_minutes` and `buffer_minutes_between_appointments` from the `ServicesTable` using `serviceId`.
    2.  Retrieves `googleCalendarId` from the `LocationsTable` using `locationId`.
    3.  Calls the Google Calendar API logic (as implemented in `get_availability_lambda`) with these details to find free slots.
    4.  Returns the JSON response as described above.
```
