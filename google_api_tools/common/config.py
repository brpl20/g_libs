"""
Common configuration utilities for Google API tools.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('google_api_tools.config')

def load_config(config_file: str, default_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load configuration from a JSON file, creating it with defaults if it doesn't exist.
    
    Args:
        config_file: Path to the configuration file
        default_config: Default configuration to use if file doesn't exist
        
    Returns:
        Configuration dictionary
    """
    config = default_config.copy()
    
    # Create config file with defaults if it doesn't exist
    if not os.path.exists(config_file):
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Created new configuration file: {config_file}")
        except Exception as e:
            logger.error(f"Error creating configuration file: {e}")
            return config
    
    # Load existing configuration
    try:
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
            config.update(loaded_config)
        logger.info(f"Loaded configuration from: {config_file}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
    
    return config

def save_config(config_file: str, config: Dict[str, Any]) -> bool:
    """
    Save configuration to a JSON file.
    
    Args:
        config_file: Path to the configuration file
        config: Configuration dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved configuration to: {config_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False
