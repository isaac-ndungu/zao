import logging
from datetime import timedelta
from subprocess import run as subprocess_run, PIPE

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.base.constants import get_soft_deletable_models

logger = logging.getLogger(__name__)


@shared_task(soft_time_limit=300, time_limit=600)
def purge_deleted_records():
    days = settings.TRASH_RETENTION_DAYS
    cutoff = timezone.now() - timedelta(days=days)

    models = []
    for model_cls in get_soft_deletable_models():
        mgr = model_cls.objects
        all_with_trashed = mgr.all_with_trashed if hasattr(mgr, 'all_with_trashed') else mgr
        models.append((model_cls.__name__, model_cls, all_with_trashed))

    total = 0
    for label, model_cls, all_with_trashed in models:
        qs = all_with_trashed().filter(deleted_at__lt=cutoff)
        count = qs.count()
        if count:
            for obj in qs:
                obj.hard_delete()
            total += count

    return f'Purged {total} record(s) older than {days} days'


@shared_task(bind=True, soft_time_limit=600, time_limit=900)
def backup_database(self):
    """Run dbbackup management command with compression."""
    try:
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        logger.info('Starting database backup: %s', timestamp)

        call_command('dbbackup', compression=True, clean=True, verbosity=0)

        logger.info('Database backup completed: %s', timestamp)
        return {'status': 'success', 'timestamp': timestamp}
    except Exception as exc:
        logger.error('Database backup failed: %s', exc)
        raise self.retry(exc=exc, countdown=300, max_retries=2)


@shared_task(bind=True, soft_time_limit=300, time_limit=600)
def verify_backup_integrity(self):
    """Check the most recent backup exists and is non-empty."""
    try:
        storage = _get_backup_storage()
        files = sorted(storage.list_directory(''))
        if not files:
            logger.warning('No backup files found')
            return {'status': 'warning', 'message': 'No backup files found'}

        latest = files[-1]
        size = storage.storage.size(latest)

        if size == 0:
            logger.error('Latest backup is empty: %s', latest)
            return {'status': 'error', 'file': latest, 'size': size}

        logger.info('Latest backup verified: %s (%d bytes)', latest, size)
        return {'status': 'ok', 'file': latest, 'size': size}
    except Exception as exc:
        logger.error('Backup verification failed: %s', exc)
        return {'status': 'error', 'message': str(exc)}


def _get_backup_storage():
    from dbbackup.storage import get_storage
    return get_storage()
