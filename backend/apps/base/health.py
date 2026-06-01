from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    database_status = _check_database()
    redis_status = _check_redis()
    celery_status = _check_celery()

    all_ok = all(
        s == 'ok' for s in (database_status, redis_status, celery_status)
    )

    return JsonResponse(
        {
            'status': 'ok' if all_ok else 'degraded',
            'database': database_status,
            'redis': redis_status,
            'celery': celery_status,
        },
        status=200 if all_ok else 503,
    )


def _check_database():
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return 'ok'
    except Exception:
        return 'unreachable'


def _check_redis():
    try:
        import redis as redis_module

        r = redis_module.Redis.from_url(
            settings.CELERY_BROKER_URL or 'redis://localhost:6379/0'
        )
        r.ping()
        return 'ok'
    except Exception:
        return 'unreachable'


def _check_celery():
    try:
        from celery import current_app

        workers = current_app.control.ping(timeout=2)
        if workers:
            return 'ok'
        return 'no workers'
    except Exception:
        return 'unreachable'
