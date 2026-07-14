import logging

from celery import shared_task

from apps.notifications.utils import send_sms

from .models import Delivery, ProductType

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_delivery_sms(self, phone_number: str, farmer_name: str, batch_id: str, product_type: str):
    product_label = dict(ProductType.choices).get(product_type, product_type)
    message = (
        f"Dear {farmer_name}, your delivery ({product_label}) "
        f"has been recorded. Batch ID: {batch_id}. "
        f"Thank you for partnering with us."
    )

    result = send_sms(phone_number, message)
    if result['success']:
        logger.info('Delivery SMS sent to %s (batch %s)', phone_number, batch_id)
    else:
        logger.error('Failed to send delivery SMS to %s: %s', phone_number, result['error'])
        raise RuntimeError(f'SMS delivery failed: {result["error"]}')


@shared_task
def send_bulk_delivery_sms(deliveries: list[dict]):
    for d in deliveries:
        send_delivery_sms.delay(
            phone_number=d['phone_number'],
            farmer_name=d['farmer_name'],
            batch_id=d['batch_id'],
            product_type=d['product_type'],
        )
