#!/usr/bin/env python3
"""
Google Calendar Report Generator
This application fetches events from Google Calendar and generates reports
for different time periods, with summaries of time spent on recurring events.
"""

import os
import logging
import datetime
import json
import re
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import pytz
from collections import defaultdict

# Google Calendar API imports
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gcal_report')

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Configuration file path
CONFIG_FILE = 'gcal_config.json'

# Default configuration
DEFAULT_CONFIG = {
    "credentials_file": "credentials.json",
    "token_file": "token.json",
    "timezone": "America/Sao_Paulo",
    "all_day_event_hours": 8,  # Hours to count for all-day events
    "calendars": ["primary"],  # List of calendars to fetch events from
    "database_file": "calendar_data.db",  # SQLite database file
    "working_days_per_week": 5  # Number of working days per week
}


def load_config() -> Dict[str, Any]:
    """Load configuration from file or create default if not exists"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {CONFIG_FILE}")
                return config
        else:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info(f"Default configuration created at {CONFIG_FILE}")
                return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return DEFAULT_CONFIG


class GoogleCalendarReport:
    def __init__(self):
        """Initialize the Google Calendar Report application"""
        self.config = load_config()
        self.service = None
        self.timezone = pytz.timezone(self.config.get("timezone", "UTC"))
        self.db_conn = None
        self.initialize_database()
        
    def initialize_database(self):
        """Initialize the SQLite database for storing calendar data"""
        db_file = self.config.get("database_file", "calendar_data.db")
        try:
            self.db_conn = sqlite3.connect(db_file)
            cursor = self.db_conn.cursor()
            
            # Create events table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                summary TEXT,
                start_time TEXT,
                end_time TEXT,
                duration REAL,
                is_all_day INTEGER,
                category TEXT,
                period_key TEXT,
                color TEXT
            )
            ''')
            
            # Create periods table to track which periods are stored
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS periods (
                period_key TEXT PRIMARY KEY,
                period_type TEXT,
                start_date TEXT,
                end_date TEXT,
                is_complete INTEGER
            )
            ''')
            
            self.db_conn.commit()
            logger.info(f"Database initialized: {db_file}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            print(f"Error initializing database: {e}")
        
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API"""
        creds = None
        token_file = self.config.get("token_file", "token.json")
        
        # Check if token file exists
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
                logger.info("Loaded existing credentials from token file")
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
                print(f"Error loading saved credentials: {e}")
                print("Will attempt to create new credentials.")
        
        # If credentials don't exist or are invalid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Refreshing expired credentials...")
                    creds.refresh(Request())
                    logger.info("Successfully refreshed credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            
            # If still no valid credentials, start OAuth flow
            if not creds:
                credentials_file = self.config.get("credentials_file", "credentials.json")
                
                # Check for credentials file
                if not os.path.exists(credentials_file):
                    logger.error(f"Credentials file not found: {credentials_file}")
                    print("\n" + "="*80)
                    print(f"ERROR: Credentials file '{credentials_file}' not found!")
                    print("\nTo set up Google Calendar access:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a project (or select existing one)")
                    print("3. Enable the Google Calendar API")
                    print("4. Create OAuth 2.0 credentials (Desktop application)")
                    print("5. Download the JSON file and save as 'credentials.json' in this directory")
                    print("="*80)
                    return False
                
                try:
                    print("\nStarting authentication flow...")
                    print("A browser window will open. Please log in and grant permission.")
                    
                    # Create the flow using the client secrets file
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES)
                    
                    # Run the OAuth flow to get credentials
                    creds = flow.run_local_server(
                        port=0, 
                        prompt='consent',
                        authorization_prompt_message="Please authorize this application to access your Google Calendar"
                    )
                    
                    # Save credentials for future use
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                    
                    logger.info(f"New credentials saved to {token_file}")
                    print(f"\nAuthentication successful! Credentials saved to {token_file}")
                    
                except Exception as e:
                    logger.error(f"Error in authentication flow: {e}")
                    print(f"\nAuthentication failed: {e}")
                    print("Please check your internet connection and try again.")
                    return False
        
        try:
            # Build the Google Calendar API service
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Calendar API")
            return True
        except Exception as e:
            logger.error(f"Error building service: {e}")
            return False
    
    def get_date_range(self, period: str) -> Tuple[datetime.datetime, datetime.datetime]:
        """
        Get start and end dates based on the selected period
        
        Args:
            period: One of 'last_month', 'current_year', 'last_year', 
                   'month_1' through 'month_12', or 'custom'
                   
        Returns:
            Tuple of (start_date, end_date) as datetime objects
        """
        now = datetime.datetime.now(self.timezone)
        
        if period == 'last_month':
            # First day of previous month
            start_date = (now.replace(day=1) - relativedelta(months=1))
            # Last day of previous month
            end_date = now.replace(day=1) - relativedelta(days=1)
            end_date = end_date.replace(hour=23, minute=59, second=59)
            
        elif period == 'current_year':
            # January 1st of current year
            start_date = datetime.datetime(now.year, 1, 1, tzinfo=self.timezone)
            # December 31st of current year
            end_date = datetime.datetime(now.year, 12, 31, 23, 59, 59, tzinfo=self.timezone)
            
        elif period == 'last_year':
            # January 1st of previous year
            start_date = datetime.datetime(now.year - 1, 1, 1, tzinfo=self.timezone)
            # December 31st of previous year
            end_date = datetime.datetime(now.year - 1, 12, 31, 23, 59, 59, tzinfo=self.timezone)
            
        elif period.startswith('month_'):
            try:
                month_num = int(period.split('_')[1])
                if 1 <= month_num <= 12:
                    # First day of specified month in current year
                    start_date = datetime.datetime(now.year, month_num, 1, tzinfo=self.timezone)
                    # Last day of specified month
                    if month_num == 12:
                        end_date = datetime.datetime(now.year, 12, 31, 23, 59, 59, tzinfo=self.timezone)
                    else:
                        end_date = datetime.datetime(now.year, month_num + 1, 1, tzinfo=self.timezone) - relativedelta(days=1)
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                else:
                    raise ValueError(f"Invalid month number: {month_num}")
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing month: {e}")
                # Default to current month if there's an error
                start_date = now.replace(day=1, hour=0, minute=0, second=0)
                end_date = (start_date + relativedelta(months=1) - relativedelta(days=1)).replace(hour=23, minute=59, second=59)
                
        elif period == 'custom':
            # For custom dates, we'll prompt the user
            print("\nEnter custom date range:")
            while True:
                try:
                    start_str = input("Start date (YYYY-MM-DD): ")
                    start_date = parse(start_str).replace(tzinfo=self.timezone)
                    start_date = start_date.replace(hour=0, minute=0, second=0)
                    break
                except Exception:
                    print("Invalid date format. Please use YYYY-MM-DD.")
            
            while True:
                try:
                    end_str = input("End date (YYYY-MM-DD): ")
                    end_date = parse(end_str).replace(tzinfo=self.timezone)
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    if end_date < start_date:
                        print("End date must be after start date.")
                        continue
                    break
                except Exception:
                    print("Invalid date format. Please use YYYY-MM-DD.")
        else:
            # Default to current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0)
            end_date = (start_date + relativedelta(months=1) - relativedelta(days=1)).replace(hour=23, minute=59, second=59)
        
        return start_date, end_date
    
    def get_period_key(self, period_type: str, start_date: datetime.datetime, end_date: datetime.datetime) -> str:
        """
        Generate a unique key for a time period
        
        Args:
            period_type: Type of period (e.g., 'month_3', 'year_2023')
            start_date: Start date
            end_date: End date
            
        Returns:
            String key for the period
        """
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        return f"{period_type}_{start_str}_{end_str}"
    
    def is_period_in_database(self, period_key: str) -> bool:
        """
        Check if a period is already stored in the database
        
        Args:
            period_key: Unique key for the period
            
        Returns:
            True if the period is stored and complete, False otherwise
        """
        if not self.db_conn:
            return False
            
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT is_complete FROM periods WHERE period_key = ?", 
                (period_key,)
            )
            result = cursor.fetchone()
            return result is not None and result[0] == 1
        except Exception as e:
            logger.error(f"Error checking period in database: {e}")
            return False
    
    def store_period_in_database(self, period_type: str, start_date: datetime.datetime, 
                                end_date: datetime.datetime, events: List[Dict[str, Any]]) -> bool:
        """
        Store a complete period and its events in the database
        
        Args:
            period_type: Type of period (e.g., 'month_3', 'year_2023')
            start_date: Start date
            end_date: End date
            events: List of event dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db_conn:
            logger.error("Database not initialized")
            return False
            
        period_key = self.get_period_key(period_type, start_date, end_date)
        
        try:
            cursor = self.db_conn.cursor()
            
            # Begin transaction
            self.db_conn.execute("BEGIN TRANSACTION")
            
            # Store period information
            cursor.execute(
                "INSERT OR REPLACE INTO periods (period_key, period_type, start_date, end_date, is_complete) VALUES (?, ?, ?, ?, ?)",
                (period_key, period_type, start_date.isoformat(), end_date.isoformat(), 1)
            )
            
            # Store events
            for event in events:
                if 'id' not in event or 'summary' not in event:
                    continue
                    
                # Extract event data
                event_id = event['id']
                summary = event['summary']
                
                # Parse category from summary if it matches the pattern
                category = "Other"
                match = re.match(r'^@([A-Z]{3})\s+(.*)', summary)
                if match:
                    category = match.group(1)
                
                # Handle all-day events
                is_all_day = 0
                if 'date' in event['start'] and 'date' in event['end']:
                    is_all_day = 1
                    start_time = event['start']['date']
                    end_time = event['end']['date']
                else:
                    start_time = event.get('start', {}).get('dateTime', '')
                    end_time = event.get('end', {}).get('dateTime', '')
                
                # Calculate duration
                duration = self.calculate_event_duration(event)
                
                # Get color if available
                color = event.get('colorId', '')
                
                # Store event in database
                cursor.execute(
                    """INSERT OR REPLACE INTO events 
                       (id, summary, start_time, end_time, duration, is_all_day, category, period_key, color) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event_id, summary, start_time, end_time, duration, is_all_day, category, period_key, color)
                )
            
            # Commit transaction
            self.db_conn.commit()
            logger.info(f"Stored {len(events)} events for period {period_key}")
            return True
            
        except Exception as e:
            # Rollback on error
            self.db_conn.rollback()
            logger.error(f"Error storing period in database: {e}")
            return False
    
    def get_events_from_database(self, period_key: str) -> List[Dict[str, Any]]:
        """
        Retrieve events from the database for a specific period
        
        Args:
            period_key: Unique key for the period
            
        Returns:
            List of event dictionaries
        """
        if not self.db_conn:
            return []
            
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE period_key = ?", 
                (period_key,)
            )
            
            events = []
            for row in cursor.fetchall():
                event = {
                    'id': row[0],
                    'summary': row[1],
                    'start': {'dateTime': row[2]} if not row[5] else {'date': row[2]},
                    'end': {'dateTime': row[3]} if not row[5] else {'date': row[3]},
                    'duration': row[4],
                    'category': row[6],
                    'colorId': row[8] if row[8] else None
                }
                events.append(event)
                
            logger.info(f"Retrieved {len(events)} events from database for period {period_key}")
            return events
            
        except Exception as e:
            logger.error(f"Error retrieving events from database: {e}")
            return []
    
    def get_events(self, start_date: datetime.datetime, end_date: datetime.datetime, 
                  period_type: str = '') -> List[Dict[str, Any]]:
        """
        Fetch events from Google Calendar or database for the specified date range
        
        Args:
            start_date: Start date for events
            end_date: End date for events
            period_type: Type of period (e.g., 'month_3', 'year_2023')
            
        Returns:
            List of event dictionaries
        """
        # Generate period key
        period_key = self.get_period_key(period_type, start_date, end_date)
        
        # Check if period is in database
        if self.is_period_in_database(period_key):
            logger.info(f"Using cached data for period {period_key}")
            return self.get_events_from_database(period_key)
        
        # If not in database or not complete, fetch from Google Calendar
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return []
        
        events_result = []
        try:
            # Convert to RFC3339 timestamp format
            time_min = start_date.isoformat()
            time_max = end_date.isoformat()
            
            logger.info(f"Fetching events from {time_min} to {time_max}")
            
            # Get calendar events for each calendar in config
            calendars = self.config.get("calendars", ["primary"])
            for calendar_id in calendars:
                page_token = None
                while True:
                    events = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=2500,  # Maximum allowed by API
                        singleEvents=True,  # Expand recurring events
                        orderBy='startTime',
                        pageToken=page_token
                    ).execute()
                    
                    events_result.extend(events.get('items', []))
                    page_token = events.get('nextPageToken')
                    if not page_token:
                        break
            
            logger.info(f"Retrieved {len(events_result)} events")
            return events_result
            
        except HttpError as error:
            logger.error(f"Error fetching events: {error}")
            return []
    
    def calculate_event_duration(self, event: Dict[str, Any]) -> float:
        """
        Calculate duration of an event in hours
        
        Args:
            event: Event dictionary from Google Calendar API
            
        Returns:
            Duration in hours as a float
        """
        # Check if event has start and end times
        if 'start' not in event or 'end' not in event:
            return 0.0
        
        # Handle all-day events
        if 'date' in event['start'] and 'date' in event['end']:
            # All-day events: count based on configuration
            hours_per_day = self.config.get("all_day_event_hours", 8)
            start_date = datetime.datetime.fromisoformat(event['start']['date'])
            end_date = datetime.datetime.fromisoformat(event['end']['date'])
            days = (end_date - start_date).days
            return days * float(hours_per_day)
        
        # Handle timed events
        elif 'dateTime' in event['start'] and 'dateTime' in event['end']:
            start_time = datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            duration = end_time - start_time
            return duration.total_seconds() / 3600  # Convert to hours
        
        return 0.0
    
    def generate_report(self, events: List[Dict[str, Any]], start_date: datetime.datetime, 
                       end_date: datetime.datetime, period_type: str = '') -> None:
        """
        Generate and display a report of events
        
        Args:
            events: List of event dictionaries
            start_date: Start date of the report period
            end_date: End date of the report period
            period_type: Type of period (e.g., 'month_3', 'year_2023')
        """
        if not events:
            print("\nNo events found for the selected period.")
            return
        
        # Format date range for display
        date_format = "%B %d, %Y"
        date_range = f"{start_date.strftime(date_format)} to {end_date.strftime(date_format)}"
        
        print(f"\n=== CALENDAR REPORT: {date_range} ===\n")
        
        # Track event durations by name for summary
        event_durations = defaultdict(float)
        event_count = defaultdict(int)
        
        # Track events by category (@XXX pattern)
        categorized_events = defaultdict(list)
        uncategorized_events = []
        
        # Track total time by category
        category_durations = defaultdict(float)
        
        # Process events
        for event in events:
            # Skip events without a summary
            if 'summary' not in event:
                continue
                
            summary = event['summary']
            
            # Check if event follows @XXX pattern (3 uppercase letters after @)
            category_match = re.match(r'^@([A-Z]{3})[ _](.*)', summary)
            if category_match:
                category = category_match.group(1)
                subcategory = category_match.group(2)
            else:
                category = "Other"
                subcategory = summary
            
            # Handle all-day events
            if 'date' in event['start']:
                start_date_str = event['start']['date']
                end_date_str = event['end']['date']
                start_time_str = "All day"
                end_time_str = ""
                
                # Calculate duration (in days)
                start = datetime.datetime.fromisoformat(start_date_str)
                end = datetime.datetime.fromisoformat(end_date_str)
                days = (end - start).days
                hours_per_day = self.config.get("all_day_event_hours", 8)
                duration = days * float(hours_per_day)
                duration_str = f"{days} day(s)"
                
            # Handle timed events
            else:
                start_dt = datetime.datetime.fromisoformat(
                    event['start']['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.datetime.fromisoformat(
                    event['end']['dateTime'].replace('Z', '+00:00'))
                
                # Format for display
                start_date_str = start_dt.strftime("%Y-%m-%d")
                start_time_str = start_dt.strftime("%H:%M")
                end_time_str = end_dt.strftime("%H:%M")
                
                # Calculate duration
                duration = (end_dt - start_dt).total_seconds() / 3600
                if duration < 1:
                    duration_str = f"{int(duration * 60)} min"
                else:
                    duration_str = f"{duration:.1f} hrs"
            
            # Track for summary
            event_durations[summary] += duration
            event_count[summary] += 1
            
            # Track by category
            category_durations[category] += duration
            
            # Add to categorized or uncategorized list
            event_data = {
                'summary': summary,
                'subcategory': subcategory,
                'date': start_date_str,
                'start': start_time_str,
                'end': end_time_str,
                'duration': duration,
                'duration_str': duration_str,
                'category': category,
                'color': event.get('colorId', '')
            }
            
            if category != "Other":
                categorized_events[category].append(event_data)
            else:
                uncategorized_events.append(event_data)
        
        # Display events chronologically
        print("EVENTS:")
        print("-" * 80)
        print(f"{'Date':<12} {'Start':<8} {'End':<8} {'Duration':<10} {'Summary':<40}")
        print("-" * 80)
        
        # Sort all events by date
        all_events = []
        for category, events_list in categorized_events.items():
            all_events.extend(events_list)
        all_events.extend(uncategorized_events)
        all_events.sort(key=lambda x: x['date'])
        
        for event_data in all_events:
            print(f"{event_data['date']:<12} {event_data['start']:<8} {event_data['end']:<8} "
                  f"{event_data['duration_str']:<10} {event_data['summary'][:40]}")
        
        # Calculate working days in the period
        total_days = (end_date - start_date).days + 1
        working_days_per_week = self.config.get("working_days_per_week", 5)
        weeks = total_days / 7
        working_days = round(weeks * working_days_per_week)
        
        # Calculate total time
        total_hours = sum(event_durations.values())
        avg_hours_per_working_day = total_hours / working_days if working_days > 0 else 0
        
        # Display time summary table
        print("\n\nTIME SUMMARY:")
        print("-" * 60)
        print(f"{'Metric':<30} {'Value':<20}")
        print("-" * 60)
        
        if total_hours < 24:
            total_time_str = f"{total_hours:.1f} hours"
        else:
            days = total_hours / 24
            total_time_str = f"{days:.1f} days ({total_hours:.1f} hours)"
        
        print(f"{'Total time':<30} {total_time_str:<20}")
        print(f"{'Total days in period':<30} {total_days:<20}")
        print(f"{'Working days in period':<30} {working_days:<20}")
        print(f"{'Average hours per working day':<30} {avg_hours_per_working_day:.1f} hours")
        print("-" * 60)
        
        # Display categorized events (@XXX pattern)
        print("\n\nCATEGORIZED EVENTS (@XXX):")
        print("=" * 100)
        
        # Sort categories by total duration
        sorted_categories = sorted(
            [(cat, category_durations[cat]) for cat in categorized_events.keys()],
            key=lambda x: x[1], reverse=True
        )
        
        for category, total_duration in sorted_categories:
            events_list = categorized_events[category]
            
            # Skip empty categories
            if not events_list:
                continue
                
            # Format category header with total time
            if total_duration < 24:
                duration_str = f"{total_duration:.1f} hours"
            else:
                days = total_duration / 24
                duration_str = f"{days:.1f} days ({total_duration:.1f} hours)"
                
            print(f"\n@{category} - Total: {duration_str} - {len(events_list)} events")
            print("-" * 100)
            print(f"{'Date':<12} {'Start':<8} {'End':<8} {'Duration':<10} {'Subcategory':<50}")
            print("-" * 100)
            
            # Group by subcategory
            subcategory_groups = defaultdict(list)
            subcategory_durations = defaultdict(float)
            
            for event in events_list:
                subcategory_groups[event['subcategory']].append(event)
                subcategory_durations[event['subcategory']] += event['duration']
            
            # Display events grouped by subcategory
            for subcategory, subcat_events in sorted(subcategory_groups.items(), 
                                                   key=lambda x: subcategory_durations[x[0]], 
                                                   reverse=True):
                # Calculate total for this subcategory
                subcat_total = subcategory_durations[subcategory]
                if subcat_total < 24:
                    subcat_total_str = f"{subcat_total:.1f} hours"
                else:
                    days = subcat_total / 24
                    subcat_total_str = f"{days:.1f} days ({subcat_total:.1f} hours)"
                
                # Print subcategory header
                print(f"\n  {subcategory} - Total: {subcat_total_str} - {len(subcat_events)} occurrences")
                
                # Sort events by date
                subcat_events.sort(key=lambda x: x['date'])
                
                # Print individual events
                for event in subcat_events:
                    print(f"{event['date']:<12} {event['start']:<8} {event['end']:<8} "
                          f"{event['duration_str']:<10} {event['subcategory'][:50]}")
        
        # Display uncategorized events
        if uncategorized_events:
            other_duration = category_durations["Other"]
            if other_duration < 24:
                other_duration_str = f"{other_duration:.1f} hours"
            else:
                days = other_duration / 24
                other_duration_str = f"{days:.1f} days ({other_duration:.1f} hours)"
                
            print(f"\n\nUNCATEGORIZED EVENTS - Total: {other_duration_str} - {len(uncategorized_events)} events")
            print("-" * 100)
            print(f"{'Date':<12} {'Start':<8} {'End':<8} {'Duration':<10} {'Summary':<50}")
            print("-" * 100)
            
            # Sort by duration
            uncategorized_events.sort(key=lambda x: x['duration'], reverse=True)
            
            for event in uncategorized_events:
                print(f"{event['date']:<12} {event['start']:<8} {event['end']:<8} "
                      f"{event['duration_str']:<10} {event['summary'][:50]}")
        
        # Generate summary for events that occurred multiple times
        print("\n\nSUMMARY OF RECURRING EVENTS:")
        print("-" * 80)
        print(f"{'Event':<50} {'Occurrences':<12} {'Total Time':<15}")
        print("-" * 80)
        
        # Sort by total duration (descending)
        for summary, total_duration in sorted(event_durations.items(), key=lambda x: x[1], reverse=True):
            # Show all events that match our pattern requirements
            # Skip entries with multiple @ symbols or that don't match the @XXX pattern
            if summary.count('@') > 1 or not re.match(r'^@[A-Z]{3}[ _].*$', summary):
                continue
                    
                # Format duration
                if total_duration < 1:
                    duration_str = f"{int(total_duration * 60)} minutes"
                elif total_duration < 24:
                    duration_str = f"{total_duration:.1f} hours"
                else:
                    days = total_duration / 24
                    duration_str = f"{days:.1f} days"
                
                print(f"{summary[:50]:<50} {event_count[summary]:<12} {duration_str:<15}")
        
        print("-" * 80)
        print(f"Total events: {len(events)}")
        print(f"Total time: {total_time_str}")
        print("=" * 80)


def main():
    """Main function to run the Google Calendar Report application"""
    print("\n=== Google Calendar Report Generator ===\n")
    
    # Create and authenticate the report generator
    report_gen = GoogleCalendarReport()
    
    print("Authenticating with Google Calendar...")
    if not report_gen.authenticate():
        print("\nAuthentication failed. Please check your credentials and try again.")
        print("Make sure 'credentials.json' exists in the application directory.")
        print("You can download it from Google Cloud Console.")
        return
    
    print("\nAuthentication successful! You're connected to Google Calendar.")
    
    # Menu for selecting time period
    while True:
        print("\nSelect a time period for the report:")
        print("1. Last month")
        print("2. Current year")
        print("3. Last year")
        print("4. January (current year)")
        print("5. February (current year)")
        print("6. March (current year)")
        print("7. April (current year)")
        print("8. May (current year)")
        print("9. June (current year)")
        print("10. July (current year)")
        print("11. August (current year)")
        print("12. September (current year)")
        print("13. October (current year)")
        print("14. November (current year)")
        print("15. December (current year)")
        print("16. Custom date range")
        print("17. Store period data in database")
        print("0. Exit")
        
        choice = input("\nEnter your choice (0-17): ")
        
        if choice == '0':
            print("Exiting. Goodbye!")
            break
            
        # Map choices to period identifiers
        period_map = {
            '1': 'last_month',
            '2': 'current_year',
            '3': 'last_year',
            '4': 'month_1',
            '5': 'month_2',
            '6': 'month_3',
            '7': 'month_4',
            '8': 'month_5',
            '9': 'month_6',
            '10': 'month_7',
            '11': 'month_8',
            '12': 'month_9',
            '13': 'month_10',
            '14': 'month_11',
            '15': 'month_12',
            '16': 'custom'
        }
        
        if choice == '17':
            # Store period data in database
            print("\nStore completed period data in database:")
            print("This will save the data locally so you don't need to fetch it from Google Calendar again.")
            
            # Show period options
            print("\nSelect a period to store:")
            for key, value in period_map.items():
                if key != '16':  # Skip custom
                    print(f"{key}. {value.replace('_', ' ').title()}")
            
            period_choice = input("\nEnter your choice: ")
            if period_choice in period_map and period_choice != '16':
                period = period_map[period_choice]
                
                # Get date range
                start_date, end_date = report_gen.get_date_range(period)
                
                # Fetch events
                print(f"\nFetching events from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
                events = report_gen.get_events(start_date, end_date, period)
                
                # Store in database
                if report_gen.store_period_in_database(period, start_date, end_date, events):
                    print(f"\nSuccessfully stored {len(events)} events for period {period}.")
                else:
                    print("\nFailed to store period data in database.")
            else:
                print("Invalid choice.")
                
        elif choice in period_map:
            period = period_map[choice]
            
            # Get date range for the selected period
            start_date, end_date = report_gen.get_date_range(period)
            
            # Fetch events (will use database if available)
            print(f"\nFetching events from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
            events = report_gen.get_events(start_date, end_date, period)
            
            # Generate and display report
            report_gen.generate_report(events, start_date, end_date, period)
            
            # Ask if user wants to continue
            if input("\nGenerate another report? (y/n): ").lower() != 'y':
                print("Exiting. Goodbye!")
                break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
