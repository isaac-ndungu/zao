import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zaoapi.settings')

app = Celery('zaoapi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Global timeouts (per-task overrides take precedence)
app.conf.update(
    task_soft_time_limit=300,
    task_time_limit=600,
)
