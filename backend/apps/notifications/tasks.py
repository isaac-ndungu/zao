import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Notification, USSDSession
from .utils import send_sms

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_task(self, notification_id: str):
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error('Notification %s not found', notification_id)
        return {'error': 'Notification not found'}

    recipient_phone = notification.recipient.phone_number if notification.recipient else None
    if not recipient_phone:
        notification.status = 'FAILED'
        notification.error_message = 'No recipient phone number'
        notification.save(update_fields=['status', 'error_message'])
        return {'error': 'No recipient phone number'}

    result = send_sms(recipient_phone, notification.content)

    if result['success']:
        notification.status = 'SENT'
        notification.external_id = result['external_id'] or ''
        notification.sent_at = timezone.now()
        notification.save(update_fields=['status', 'external_id', 'sent_at'])
        return {'status': 'SENT', 'notification_id': notification_id}
    else:
        notification.retry_count += 1
        if notification.retry_count < notification.max_retries:
            notification.error_message = result['error'] or ''
            notification.save(update_fields=['retry_count', 'error_message'])
            countdown = 60 * (2 ** (notification.retry_count - 1))
            raise self.retry(countdown=countdown)

        notification.status = 'FAILED'
        notification.error_message = result['error'] or ''
        notification.save(update_fields=['status', 'retry_count', 'error_message'])
        return {'status': 'FAILED', 'notification_id': notification_id, 'error': result['error']}


@shared_task
def send_bulk_sms_task(notification_ids: list):
    CHUNK_SIZE = 50
    CHUNK_DELAY = 30

    chunks = [
        notification_ids[i:i + CHUNK_SIZE]
        for i in range(0, len(notification_ids), CHUNK_SIZE)
    ]

    for i, chunk in enumerate(chunks):
        for nid in chunk:
            send_sms_task.delay(str(nid))
        if i < len(chunks) - 1:
            send_bulk_sms_task.apply_async(args=[chunk], countdown=CHUNK_DELAY)

    return {
        'status': 'queued',
        'total': len(notification_ids),
        'chunks': len(chunks),
    }


@shared_task
def cleanup_expired_ussd_sessions():
    cutoff = timezone.now() - timedelta(hours=1)
    deleted, _ = USSDSession.objects.filter(last_activity__lt=cutoff).delete()
    if deleted:
        logger.info('Cleaned up %d expired USSD sessions', deleted)
    return {'deleted': deleted}
