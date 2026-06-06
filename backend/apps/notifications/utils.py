import logging

from django.conf import settings
from decouple import config

import africastalking

from apps.base.utils import normalize_phone_for_sms

logger = logging.getLogger(__name__)


def send_sms(phone_number: str, message: str) -> dict:
    phone = normalize_phone_for_sms(phone_number)

    if settings.NOTIFICATIONS_DRY_RUN:
        logger.info(
            'DRY RUN SMS to %s (%d chars): %.100s',
            phone, len(message), message,
        )
        return {'success': True, 'external_id': 'dry-run', 'error': None}

    api_key = config('AT_API_KEY', default='')
    username = config('AT_USERNAME', default='')

    if not api_key or not username:
        logger.warning(
            'AT_API_KEY or AT_USERNAME not set. SMS not sent to %s', phone,
        )
        return {'success': False, 'external_id': None, 'error': 'AT credentials not configured'}

    try:
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS
        response = sms.send(message, [phone])
        recipients = response.get('SMSMessageData', {}).get('Recipients', [])
        external_id = recipients[0].get('messageId', '') if recipients else ''
        logger.info('SMS sent to %s: %s', phone, response)
        return {'success': True, 'external_id': external_id, 'error': None}
    except Exception as e:
        logger.error('Failed to send SMS to %s: %s', phone, e)
        return {'success': False, 'external_id': None, 'error': str(e)}


def format_delivery_for_ussd(delivery) -> str:
    qty = float(delivery.quantity_kg or delivery.volume_litres or 0)
    unit = 'L' if delivery.volume_litres else 'K'
    grade = delivery.grade or '-'
    date_str = delivery.date_delivered.strftime('%d/%m')
    return f'{date_str} - {qty}{unit} Gr{grade}'
