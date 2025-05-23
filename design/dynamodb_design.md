# DynamoDB Table Design: AI-Based Client Registration System

This document outlines the proposed DynamoDB table structure for the Automobile Detailing Center Registration System.

## Core Principles:

*   **Single-Table vs. Multi-Table:** A multi-table design is chosen for clarity and separation of concerns for the main entities: Appointments, Services, and Locations. This can simplify IAM policies and allows for different throughput settings if needed in the future, though PAY_PER_REQUEST is the initial choice.
*   **Key Design:** Primary keys are chosen for direct entity lookup. GSIs are designed to support common query patterns.

## Table Definitions:

### 1. Appointments Table

*   **Table Name:** `Appointments` (or `AppointmentsTable` as per Terraform convention)
*   **Primary Key:**
    *   Partition Key (PK): `bookingId` (String) - Unique identifier for each booking.
*   **Attributes (core):**
    *   `bookingId` (String)
    *   `clientId` (String) - Identifier for the client who made the booking.
    *   `clientName` (String)
    *   `clientContact` (Map) - e.g., `{"email": "client@example.com", "phone": "+1234567890"}`
    *   `serviceName` (String) - Denormalized for quick display, but `serviceId` could also be stored.
    *   `serviceDurationMinutes` (Number) - Denormalized from Service.
    *   `locationId` (String) - Identifier for the location of the appointment.
    *   `locationName` (String) - Denormalized for quick display.
    *   `proposedStartTime` (String) - ISO 8601 format (e.g., `2024-08-15T10:00:00Z`).
    *   `proposedEndTime` (String) - ISO 8601 format.
    *   `status` (String) - e.g., `pending_confirmation`, `confirmed`, `cancelled`, `completed`, `rejected`.
    *   `googleCalendarEventId` (String, Optional) - ID from Google Calendar if synced.
    *   `bookingChannel` (String) - e.g., `website`, `instagram`, `facebook`, `phone`.
    *   `notes` (String, Optional) - Client notes.
    *   `createdAt` (String) - ISO 8601 format.
    *   `updatedAt` (String) - ISO 8601 format.
*   **Global Secondary Indexes (GSIs):**
    *   **GSI 1: `LocationStatusIndex`**
        *   Partition Key (PK): `locationId` (String)
        *   Sort Key (SK): `status#proposedStartTime` (String) - Composite key to query by location, then filter/sort by status and time.
        *   Projection: ALL
        *   Query Patterns:
            *   Get all appointments for a `locationId`, sorted by `status` then `proposedStartTime`.
            *   Get `pending_confirmation` appointments for a `locationId`.
            *   Get `confirmed` upcoming appointments for a `locationId`.
    *   **GSI 2: `ClientIdStatusIndex`**
        *   Partition Key (PK): `clientId` (String)
        *   Sort Key (SK): `status#proposedStartTime` (String) - Composite key.
        *   Projection: ALL
        *   Query Patterns:
            *   List all appointments for a `clientId`, sorted by status and then time.
            *   List upcoming/past appointments for a `clientId`.
    *   **GSI 3: `StatusTimeIndex` (Optional - for general operational queries)**
        *   Partition Key (PK): `status` (String)
        *   Sort Key (SK): `proposedStartTime` (String)
        *   Projection: ALL
        *   Query Patterns:
            *   Find all `pending_confirmation` appointments across all locations, ordered by time.
*   **Local Secondary Indexes (LSIs):** None proposed at this stage, as GSIs cover primary query patterns.

### 2. Services Table

*   **Table Name:** `Services` (or `ServicesTable`)
*   **Primary Key:**
    *   Partition Key (PK): `serviceId` (String) - Unique identifier for each service.
*   **Attributes (core):**
    *   `serviceId` (String)
    *   `serviceName` (String)
    *   `description` (String)
    *   `durationMinutes` (Number) - Duration of the service itself.
    *   `bufferMinutesBetweenAppointments` (Number) - Time to add after a service before next can start.
    *   `price` (Number) - Can be stored in cents or as a decimal string.
    *   `applicableLocationIds` (List of Strings, Optional) - If a service is only at specific locations.
    *   `isActive` (Boolean)
*   **Global Secondary Indexes (GSIs):**
    *   **GSI 1: `ServiceNameIndex` (If querying by name is common and `serviceId` is not always known upfront)**
        *   Partition Key (PK): `serviceName` (String)
        *   Sort Key (SK): None needed if names are unique; could be `serviceId` if names can be non-unique.
        *   Projection: ALL or KEYS_ONLY (if only `serviceId` is needed from lookup).
        *   Query Patterns:
            *   Get `serviceId` by `serviceName`.
            *   List all services (by scanning the table, or if a GSI on `isActive` is made).
*   **Local Secondary Indexes (LSIs):** None proposed.

### 3. Locations Table

*   **Table Name:** `Locations` (or `LocationsTable`)
*   **Primary Key:**
    *   Partition Key (PK): `locationId` (String) - Unique identifier for each location.
*   **Attributes (core):**
    *   `locationId` (String)
    *   `locationName` (String)
    *   `address` (String or Map) - e.g., `{"street": "123 Main St", "city": "Anytown", "zip": "12345"}`
    *   `googleCalendarId` (String) - Google Calendar ID for this location's schedule.
    *   `operatingHours` (Map or String) - e.g., `{"Mon": "9am-5pm", "Tue": "9am-5pm", ...}` or a descriptive string.
    *   `contactPhone` (String)
    *   `isActive` (Boolean)
*   **Global Secondary Indexes (GSIs):**
    *   **GSI 1: `LocationNameIndex` (If querying by name is common)**
        *   Partition Key (PK): `locationName` (String)
        *   Projection: ALL
        *   Query Patterns:
            *   Get location details by `locationName`.
*   **Local Secondary Indexes (LSIs):** None proposed.

## General Considerations:

*   **Timestamps:** `createdAt` and `updatedAt` attributes should be maintained for all records.
*   **Data Types:** Use appropriate DynamoDB data types (S for String, N for Number, B for Binary, BOOL for Boolean, L for List, M for Map).
*   **Error Handling:** Application logic should handle cases where items are not found or queries return empty results.
*   **Scalability:** PAY_PER_REQUEST billing mode is suitable for unpredictable workloads. If traffic becomes high and predictable, provisioned throughput might be considered.
*   **Denormalization:** Some data (like `serviceName` in Appointments) is denormalized to reduce the need for frequent joins, which are not a native DynamoDB feature. Ensure application logic updates denormalized data if the source data changes (though for things like service name, this is rare).
