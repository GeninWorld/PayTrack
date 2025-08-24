#!/usr/bin/env python3
"""
Celery worker script that can run independently from the Flask app.
This creates the necessary Flask app context for database operations.
"""

import os
from dotenv import load_dotenv
from celery_app import create_celery_app

# Load environment variables
load_dotenv()

# Create celery app with Flask context
celery_app = create_celery_app()

if __name__ == '__main__':
    # Start the celery worker
    celery_app.start()