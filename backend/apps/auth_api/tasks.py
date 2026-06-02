import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import TwoFactorOTP

logger = logging.getLogger(__name__)


@shared_task(soft_time_limit=30, time_limit=60)
def cleanup_expired_otps():
    cutoff = timezone.now()
    deleted, _ = TwoFactorOTP.objects.filter(
        expires_at__lt=cutoff, is_used=False,
    ).delete()
    if deleted:
        logger.info('Cleaned up %d expired OTPs', deleted)
    return {'deleted': deleted}
