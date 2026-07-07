#!/bin/sh
set -e

case "${SERVICE_TYPE:-web}" in
  worker)
    exec celery -A zaoapi worker -l info --concurrency=1 --max-tasks-per-child=1000 --max-memory-per-child=200000
    ;;
  beat)
    exec celery -A zaoapi beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ;;
  web)
    # Use fake-initial to handle existing databases gracefully
    # Django will only fake-apply if tables already exist, otherwise it creates them normally
    python manage.py migrate --fake-initial --noinput || python manage.py migrate --noinput
    python manage.py collectstatic --noinput --clear
    celery -A zaoapi worker -l info --concurrency=1 --max-tasks-per-child=1000 --max-memory-per-child=200000 &
    celery -A zaoapi beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
    exec gunicorn zaoapi.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2} --timeout 120
    ;;
esac
