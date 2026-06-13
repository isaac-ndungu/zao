from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cooperatives.models import Cooperative

User = get_user_model()


@shared_task(soft_time_limit=300, time_limit=600)
def purge_deleted_records():
    days = settings.TRASH_RETENTION_DAYS
    cutoff = timezone.now() - timedelta(days=days)

    models = [
        ('User', User, User.objects.all_with_trashed),
        ('Cooperative', Cooperative, Cooperative.objects.all_with_trashed),
    ]

    total = 0
    for label, model_cls, all_with_trashed in models:
        if not hasattr(model_cls, 'deleted_at'):
            continue
        qs = all_with_trashed().filter(deleted_at__lt=cutoff)
        count = qs.count()
        if count:
            for obj in qs:
                obj.hard_delete()
            total += count

    return f'Purged {total} record(s) older than {days} days'
