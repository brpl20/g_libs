#!/usr/bin/env python3
"""
Google Calendar Credentials Setup Helper

This script helps users set up their Google Calendar API credentials
by providing step-by-step instructions and checking for credential files.
"""

import os
import sys
import json
import webbrowser
from pathlib import Path

def print_header():
    """Print a formatted header"""
    print("\n" + "="*80)
    print("Google Calendar API Credentials Setup Helper".center(80))
    print("="*80 + "\n")

def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\nSTEP {step_num}: {title}")
    print("-" * 50)

def check_credentials_file():
    """Check if credentials.json exists"""
    creds_file = Path("credentials.json")
    if creds_file.exists():
        with open(creds_file, 'r') as f:
            try:
                data = json.load(f)
                if 'installed' in data and 'client_id' in data['installed']:
                    return True
            except json.JSONDecodeError:
                pass
    return False

def main():
    """Main function to guide through credentials setup"""
    print_header()
    
    print("This helper will guide you through setting up Google Calendar API credentials.")
    print("You'll need to create a Google Cloud project and enable the Calendar API.")
    
    # Check if credentials already exist
    if check_credentials_file():
        print("\nGood news! A credentials.json file already exists in this directory.")
        print("You can run the main application with: python gcal_app.py")
        
        if input("\nDo you want to set up new credentials anyway? (y/n): ").lower() != 'y':
            print("\nExiting. Your existing credentials will be used.")
            return
    
    # Step 1: Create Google Cloud Project
    print_step(1, "Create a Google Cloud Project")
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Click on the project dropdown at the top of the page")
    print("3. Click 'NEW PROJECT'")
    print("4. Enter a name for your project (e.g., 'Calendar Report')")
    print("5. Click 'CREATE'")
    
    if input("\nOpen Google Cloud Console in your browser? (y/n): ").lower() == 'y':
        webbrowser.open("https://console.cloud.google.com/")
    
    input("\nPress Enter when you've created your project...")
    
    # Step 2: Enable the Calendar API
    print_step(2, "Enable the Google Calendar API")
    print("1. In your Google Cloud project, go to 'APIs & Services' > 'Library'")
    print("2. Search for 'Google Calendar API'")
    print("3. Click on 'Google Calendar API' in the results")
    print("4. Click 'ENABLE'")
    
    if input("\nOpen API Library in your browser? (y/n): ").lower() == 'y':
        webbrowser.open("https://console.cloud.google.com/apis/library")
    
    input("\nPress Enter when you've enabled the API...")
    
    # Step 3: Create OAuth credentials
    print_step(3, "Create OAuth Credentials")
    print("1. Go to 'APIs & Services' > 'Credentials'")
    print("2. Click 'CREATE CREDENTIALS' and select 'OAuth client ID'")
    print("3. If prompted to configure the consent screen, do so:")
    print("   - Choose 'External' user type")
    print("   - Enter an app name, user support email, and developer contact email")
    print("   - Save and continue through the remaining screens")
    print("4. Return to the 'Create OAuth client ID' screen")
    print("5. Select 'Desktop app' as the application type")
    print("6. Enter a name (e.g., 'Calendar Report Desktop Client')")
    print("7. Click 'CREATE'")
    
    if input("\nOpen Credentials page in your browser? (y/n): ").lower() == 'y':
        webbrowser.open("https://console.cloud.google.com/apis/credentials")
    
    input("\nPress Enter when you've created your credentials...")
    
    # Step 4: Download credentials
    print_step(4, "Download and Save Credentials")
    print("1. In the OAuth 2.0 Client IDs section, find your newly created client")
    print("2. Click the download button (⬇️) to download the JSON file")
    print("3. Save the file as 'credentials.json' in this directory")
    
    input("\nPress Enter when you've downloaded the credentials file...")
    
    # Check if credentials file exists now
    if check_credentials_file():
        print("\n✅ Great! The credentials.json file has been found and looks valid.")
        print("\nYou can now run the main application with: python gcal_app.py")
    else:
        print("\n❌ The credentials.json file was not found in this directory.")
        print("Please make sure you've downloaded the file and saved it as 'credentials.json'")
        print("in the same directory as this script.")
    
    print("\nSetup process complete!")

if __name__ == "__main__":
    main()
