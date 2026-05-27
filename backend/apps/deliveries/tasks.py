import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

from decouple import config
from celery import shared_task

from .models import Delivery

logger = logging.getLogger(__name__)


@shared_task
def send_delivery_sms(phone_number: str, farmer_name: str, batch_id: str, product_type: str):
    api_key = config('AT_API_KEY', default='')
    username = config('AT_USERNAME', default='')

    if not api_key or not username:
        logger.warning(
            'AT_API_KEY or AT_USERNAME not set. SMS not sent to %s for batch %s',
            phone_number, batch_id,
        )
        return

    product_label = dict(Delivery.PRODUCT_CHOICES).get(product_type, product_type)
    message = (
        f"Dear {farmer_name}, your delivery ({product_label}) "
        f"has been recorded. Batch ID: {batch_id}. "
        f"Thank you for partnering with us."
    )

    payload = json.dumps({
        'username': username,
        'to': phone_number,
        'message': message,
    }).encode('utf-8')

    headers = {
        'ApiKey': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        req = Request(
            'https://api.africastalking.com/version1/messaging',
            data=payload,
            headers=headers,
            method='POST',
        )
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            logger.info('SMS sent to %s: %s', phone_number, body)
    except URLError as e:
        logger.error('Failed to send SMS to %s: %s', phone_number, e)


@shared_task
def send_bulk_delivery_sms(deliveries: list[dict]):
    for d in deliveries:
        send_delivery_sms.delay(
            phone_number=d['phone_number'],
            farmer_name=d['farmer_name'],
            batch_id=d['batch_id'],
            product_type=d['product_type'],
        )
