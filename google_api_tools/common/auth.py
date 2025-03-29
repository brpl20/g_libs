"""
Common authentication utilities for Google API tools.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logger = logging.getLogger('google_api_tools.auth')

def get_credentials(
    scopes: List[str],
    client_secrets_file: str,
    token_file: str
) -> Optional[Credentials]:
    """
    Get and refresh OAuth2 credentials for Google APIs.
    
    Args:
        scopes: OAuth scopes required for the API
        client_secrets_file: Path to the client secrets JSON file
        token_file: Path to store/retrieve the token
        
    Returns:
        Credentials object or None if authentication failed
    """
    creds = None
    
    # Check if token file exists
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(token_file)), scopes)
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
    
    # If credentials don't exist or are invalid, refresh or create new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                creds = None
        else:
            try:
                if not os.path.exists(client_secrets_file):
                    logger.error(f"Client secrets file not found: {client_secrets_file}")
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, scopes)
                creds = flow.run_local_server(port=0)
                logger.info("New credentials obtained successfully")
            except Exception as e:
                logger.error(f"Error obtaining new credentials: {e}")
                return None
        
        # Save the credentials for future use
        try:
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Credentials saved to {token_file}")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
    
    return creds
