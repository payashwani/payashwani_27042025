# payashwani_27042025
# Restaurant Downtime Reporting API

## Description

This backend API calculates and reports restaurant downtime based on store status data, business hours, and timezone information. It provides insights into how often and when a store was offline during its operational hours, enabling restaurant owners to monitor and improve their online presence.

## Architecture

The application follows a data processing workflow:

1.  **Data Ingestion:** CSV data files containing store status, business hours, and timezone data are read.
2.  **Data Storage:** The CSV data is loaded into a PostgreSQL database using SQLAlchemy, an Object Relational Mapper (ORM) for Python. This allows for efficient data querying and manipulation.
3.  **API Layer:** FastAPI, a modern, high-performance Python web framework, is used to define the API endpoints for triggering and retrieving reports.
4.  **Report Generation:** When a report is requested, the API queries the database, performs necessary calculations (including timezone conversions, business hour filtering, and downtime analysis), and formats the results as a CSV string.
5.  **Report Delivery:** The generated CSV data is returned as a response to the API request.

The application utilizes asynchronous background tasks (via FastAPI's `BackgroundTasks`) to handle report generation, ensuring that API requests are processed efficiently without blocking the main thread.

## Technologies Used

* **FastAPI:** A modern, fast (high-performance), web framework for building APIs with Python 3.7+
* **SQLAlchemy:** A SQL toolkit and Object Relational Mapper (ORM) for Python, providing a full suite of well-known enterprise-level persistence patterns and designed for efficient and high-performing database access.
* **PostgreSQL:** A powerful, open-source object-relational database system.
* **Python:** The programming language used for the entire backend implementation.
* **Pytz:** Python library for timezone calculations.
* **Pandas:** Python library for data manipulation (specifically, for creating the CSV output).
* **uvicorn:** ASGI server.

## Database Schema

The application uses the following database tables:

* **`store_status`:** Stores the status of each store at specific timestamps.
    * `store_id` (String, Primary Key)
    * `timestamp_utc` (DateTime, Primary Key)
    * `status` (String)
    * `local_time` (DateTime) - Calculated local time
    * `prev_status` (String) - Previous status of the store

* **`business_hours`:** Stores the business hours for each store.
    * `id` (Integer, Primary Key)
    * `store_id` (String)
    * `dayofweek` (Integer)
    * `start_time_local` (Time)
    * `end_time_local` (Time)

* **`timezone_data`:** Stores the timezone information for each store.
    * `store_id` (String, Primary Key)
    * `timezone_str` (String)

* **`report_status`:** Stores the status and data of each generated report.
    * `report_id` (String(36), Primary Key)
    * `status` (String)
    * `report_data` (String) - CSV data

## API Endpoints

### `POST /trigger_report`

* **Description:** Triggers the generation of a new downtime report.
* **Request Body:** None
* **Response:**
    * `200 OK`:
        ```json
        {
            "report_id": "your-unique-report-id"
        }
        ```
        * `report_id`: A unique identifier for the generated report. This ID is used to retrieve the report later.

### `GET /get_report/{report_id}`

* **Description:** Retrieves the status or the generated CSV report based on the provided `report_id`.
* **Path Parameters:**
    * `report_id` (String): The unique identifier of the report to retrieve.
* **Response:**
    * `200 OK`:
        * If the report is still being generated:
            ```json
            {
                "status": "running"
            }
            ```
        * If the report is complete:
            * Returns the CSV data as the response body with appropriate headers (`Content-Type: text/csv`, `Content-Disposition`).
    * `404 Not Found`: If the `report_id` is invalid.

## Uptime/Downtime Calculation

The uptime and downtime calculations are performed within the `generate_report` function. The key steps are:

1.  **Timezone Conversion:** UTC timestamps from the `store_status` table are converted to the local timezone of each store using the `timezone_data` table. A default timezone of `America/Chicago` is used if a store's timezone is not found.
2.  **Business Hour Filtering:** The store status data is filtered to include only records that fall within the store's business hours, as defined in the `business_hours` table. If no business hours are defined for a store on a given day, it's assumed the store is open 24/7.
3.  **Status Extrapolation:** To handle gaps in the polling data, we extrapolate the store's status. It's assumed that the store's status remains the same as the last recorded status until the next status update.
4.  **Uptime/Downtime Calculation:**
    * The "current time" is determined as the maximum `local_time` across all store status records.
    * Uptime and downtime are calculated for the last hour, last 24 hours, and last 7 days.
    * For each time interval between status changes:
        * The overlap between the interval and the target timeframe (e.g., last hour) is calculated.
        * If the store was "active" during the overlap, the duration is added to the uptime.
        * If the store was "inactive", the duration is added to the downtime.
    * Uptime is reported in minutes for the last hour and in hours for the last 24 hours and last 7 days.
    * **Important Note:** The hourly calculation was corrected to only include intervals that *end* within the last hour to avoid overcounting.

## How to Run the Application

1.  **Prerequisites:**
    * Python 3.7 or higher
    * PostgreSQL database set up and running
2.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```
3.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    ```
4.  **Activate the virtual environment:**
    * **Linux/macOS:**
        ```bash
        source .venv/bin/activate
        ```
    * **Windows (PowerShell):**
        ```powershell
        .venv\Scripts\Activate.ps1
        ```
5.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Configure the database connection:**
    * Create a `.env` file in the root directory of the project.
    * Add the following line, replacing `<your_database_url>` with your PostgreSQL connection string:
        ```
        DATABASE_URL=<your_database_url>
        ```
        * Example: `DATABASE_URL=postgresql://user:password@host:port/database_name`
7.  **Run the application:**
    ```bash
    uvicorn main:app --reload
    ```

## Ideas for Improving the Solution

Due to time constraints, the following enhancements are proposed for future development:

### 1. Enhanced Data Analysis and Reporting

* **More Granular Timeframes:** Allow users to request reports for custom date/time ranges instead of being limited to pre-defined intervals (last hour, 24 hours, 7 days). This would provide greater flexibility in analyzing downtime patterns and investigating specific incidents.
* **Detailed Downtime Events:** Instead of just aggregated uptime/downtime, provide a list of individual downtime events within the reporting period. Each event would include the start time, end time, and duration of the outage. This would enable restaurant owners to pinpoint specific issues and identify potential root causes.
* **Uptime Percentage Calculation:** Calculate and report uptime as a percentage of total business hours, in addition to raw uptime in minutes/hours. This would offer a more intuitive measure of store reliability and allow for easier comparisons between stores.
* **Peak Downtime Analysis:** Analyze historical data to identify peak downtime periods (e.g., times of day, days of the week) for each store. This information could help owners proactively address potential issues and optimize staffing.

### 2. Backend Enhancements

* **Database Optimization:** Implement database indexing strategies (e.g., indexing the `store_id` and `timestamp_utc` columns in the `store_status` table) to improve query performance, especially when dealing with large datasets. Consider database partitioning for very large tables to further enhance scalability.
* **Asynchronous Task Management:** For production environments, consider using a dedicated task queue system like Celery or Redis Queue for asynchronous report generation. This would provide better scalability, fault tolerance, and monitoring capabilities compared to FastAPI's built-in `BackgroundTasks`.
* **API Documentation:** Integrate Swagger UI or ReDoc to automatically generate interactive API documentation based on the FastAPI code. This would significantly improve the developer experience and make it easier for other applications to consume the API.
* **Input Validation and Sanitization:** Implement robust input validation and sanitization to prevent potential security vulnerabilities and ensure data integrity. Use FastAPI's built-in validation features and consider libraries like Pydantic for more complex validation rules.
* **Configuration Management:** Use a more robust configuration management library (e.g., `python-decouple`) to manage environment variables and application settings. This would make it easier to deploy the application to different environments.

### 3. Error Handling and Logging

* **Comprehensive Logging:** Implement more detailed and structured logging using a library like `loguru`. Include different log levels (DEBUG, INFO, WARNING, ERROR) and log timestamps, request IDs, and other relevant context to facilitate debugging and monitoring.
* **Custom Exceptions:** Define custom exception classes to handle specific error scenarios within the application. This would make the error handling logic more organized and easier to understand.
* **API Error Responses:** Ensure that the API returns informative error messages with appropriate HTTP status codes (e.g., 400 Bad Request, 500 Internal Server Error) to provide clients with clear feedback on any errors that occur.

## CSV Report

The generated CSV report is located in the `reports/report.csv` file.

 ## Video Demonstration
 You can view a demonstartaion of API workflow and code explanation in this loom video :
      https://www.loom.com/share/49fdc23772d547c28617b397a79f3b47?sid=8f736536-a733-44a3-a5f0-9ae834da398c  
      
