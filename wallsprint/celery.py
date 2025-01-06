import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallsprint.settings')

app = Celery('wallsprint')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'send-mail-every-day-at-1': {
        'task': 'playground.tasks.notify_customers',
        'schedule': crontab(hour=13, minute=10),
        'args': ('Hello World',),
    }
}

app.autodiscover_tasks()