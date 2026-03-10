import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str, level: int = logging.INFO):
    """Function to setup as many loggers as you want"""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # Optional file handler
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup_logger is called multiple times for the same name
    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(file_handler)

    return logger

# Create a default logger for general use
logger = setup_logger("ar_automation")
