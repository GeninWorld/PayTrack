from celery import Celery
import os
from celery.schedules import crontab
from dotenv import load_dotenv
load_dotenv()

# Create Celery instance
celery = Celery('tasks')

# Basic Celery configuration
celery.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Nairobi',
    enable_utc=True,
    imports=[
        'workers.initiate_mpesa',  # <-- import your task module here
    ]
)

celery.conf.beat_schedule = {
    'schedule-tenant-payments-every-friday': {
        'task': 'workers.schedule_billing',
        # 'schedule': crontab(hour=9, minute=0, day_of_week='fri'),
        'schedule': crontab(minute='*/3'), 
    },
}

def init_celery(app):
    """Initialize Celery with existing Flask app"""
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    celery.flask_app = app  # Store app reference for tasks
    return celery

# start celery worker and batching with:
# celery -A app.celery worker --loglevel=info