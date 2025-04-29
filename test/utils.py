import os
import logging
import time
from pathlib import Path
from app.core.settings.upstage import upstagesettings
from app.core.settings.koreainvest import kissettings
from app.core.settings.bingsearch import bingsearchsettings

# Create output directory for test logs
OUTPUT_DIR = Path(__file__).parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

# Configure logging
def setup_logger(test_name):
    """
    Setup a logger for a specific test with file output
    
    Args:
        test_name (str): Name of the test (used for log file name)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = OUTPUT_DIR / f"{test_name}_{timestamp}.log"
    
    logger = logging.getLogger(test_name)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
        
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(name)s - %(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_service_settings():
    """
    Get settings from each service's settings module
    Assumes settings modules have already loaded environment variables (.env)
    """
    settings = {
        'upstage': {
            'api_key': upstagesettings.api_info[0] if hasattr(upstagesettings, 'api_info') else None,
            'api_endpoint': upstagesettings.api_info[1] if hasattr(upstagesettings, 'api_info') else None
        },
        'kis': {
            'app_key': kissettings.app_key if hasattr(kissettings, 'app_key') else None,
            'app_secret': kissettings.app_secret if hasattr(kissettings, 'app_secret') else None
        },
        'websearch': {
            'search_api_key': websearchsettings.api_key if hasattr(websearchsettings, 'api_key') else None,
            'search_engine_id': websearchsettings.search_engine_id if hasattr(websearchsettings, 'search_engine_id') else None
        }
    }
    return settings

def get_credentials(service_name):
    """
    Get credentials for a specific service
    
    Args:
        service_name (str): Service name ('upstage', 'kis', 'websearch')
        
    Returns:
        dict: Service credential object or None (if invalid)
    """
    settings = get_service_settings()
    
    if service_name not in settings:
        return None
        
    service_settings = settings[service_name]
    
    # Check if all values exist
    if all(service_settings.values()):
        return service_settings
    else:
        return None 