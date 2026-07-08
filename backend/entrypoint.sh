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
    # Detect whether the database is truly fresh (no django_migrations table).
    # On a fresh DB, run migrate normally so contenttypes.0002_remove_content_type_name
    # can drop the now-obsolete name column. Only fall back to --fake-initial when
    # a previous deploy's state is detected, and only as a last resort.
    IS_FRESH=$(python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zaoapi.settings')
import django
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute(\"SELECT to_regclass('django_migrations')\")
    print('1' if c.fetchone()[0] is None else '0')
")
    if [ "$IS_FRESH" = "1" ]; then
      echo "Fresh database detected. Running migrate without --fake-initial."
      python manage.py migrate --noinput
    else
      echo "Existing migration history detected. Running migrate with --fake-initial."
      python manage.py migrate --fake-initial --noinput || python manage.py migrate --noinput
    fi
    python manage.py collectstatic --noinput --clear
    celery -A zaoapi worker -l info --concurrency=1 --max-tasks-per-child=1000 --max-memory-per-child=200000 &
    celery -A zaoapi beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
    exec gunicorn zaoapi.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2} --timeout 120
    ;;
esac
