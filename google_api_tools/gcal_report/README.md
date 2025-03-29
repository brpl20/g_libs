# Google Calendar Report Generator

This application fetches events from your Google Calendar and generates reports for different time periods, with summaries of time spent on recurring events.

## Features

- View events from different time periods:
  - Last month
  - Current year
  - Last year
  - Specific month from current year
  - Custom date range
- See a chronological list of all events
- Get a summary of recurring events with total time spent
- Calculate total time spent on calendar events
- Categorize events with @XXX pattern (e.g., @ADV, @MKT, @PES) and group by subcategories
- Generate separate boards for categorized and uncategorized events
- Calculate average hours per working day
- Store completed periods in a local database for offline access

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a Google Cloud project and enable the Google Calendar API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials JSON file and save it as `credentials.json` in the application directory

3. Run the application:
   ```
   python gcal_app.py
   ```

4. On first run, you'll be prompted to authorize the application to access your Google Calendar.

## Configuration

The application creates a `gcal_config.json` file with default settings. You can modify this file to change:

- The path to your credentials file
- The path to the token file (for storing OAuth tokens)
- Your timezone
- Hours to count for all-day events (default: 8)
- List of calendars to fetch events from (default: ["primary"])
- Database file path for storing calendar data
- Number of working days per week (default: 5)

## Usage

1. Run the application:
   ```
   python gcal_app.py
   ```

2. Select a time period for the report
3. View the events and summary information, including:
   - Chronological list of all events
   - Categorized events board (for events with @XXX pattern)
   - Uncategorized events board
   - Time summary with total hours and average per working day
   - Summary of recurring events

4. Store completed periods in the database:
   - Select option 17 from the main menu
   - Choose the period you want to store
   - The data will be saved locally and used for future reports

5. Choose to generate another report or exit

## Requirements

- Python 3.7+
- Google API Python Client
- Google Auth libraries
- Python dateutil
