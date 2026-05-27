import os
from decouple import config
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zaoapi.settings')

app = Celery('zaoapi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.broker_url = config('REDIS_URL')
app.conf.result_backend = config('REDIS_URL')
