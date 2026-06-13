from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.base.constants import get_soft_deletable_models


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
