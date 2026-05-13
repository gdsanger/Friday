"""
Celery configuration for Friday project.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('friday')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule
app.conf.beat_schedule = {
    'renew-webhook-subscriptions': {
        'task': 'apps.mail.tasks.renew_webhook_subscriptions',
        'schedule': crontab(hour=6, minute=0),  # daily at 06:00
    },
    'daily-digest': {
        'task': 'apps.mail.tasks.send_daily_digest',
        'schedule': crontab(hour=7, minute=0),  # daily at 07:00
    },
    'overdue-notifications': {
        'task': 'apps.mail.tasks.send_overdue_notifications',
        'schedule': crontab(hour=8, minute=0),  # daily at 08:00
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
