#!/bin/sh
set -e

case "${SERVICE_TYPE:-web}" in
  worker)
    exec celery -A zaoapi worker -l info
    ;;
  beat)
    exec celery -A zaoapi beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  web)
    python manage.py collectstatic --noinput --clear
    exec gunicorn zaoapi.wsgi:application --bind 0.0.0.0:8000 --workers 4
    ;;
esac
