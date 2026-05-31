import json
import logging

from django.conf import settings
from decouple import config
from urllib.request import Request, urlopen
from urllib.error import URLError

from apps.base.utils import normalize_phone_for_sms

logger = logging.getLogger(__name__)

AT_API_URL = 'https://api.africastalking.com/version1/messaging'


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

    payload = json.dumps({
        'username': username,
        'to': phone,
        'message': message,
    }).encode('utf-8')

    headers = {
        'ApiKey': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        req = Request(AT_API_URL, data=payload, headers=headers, method='POST')
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            sms_data = body.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            external_id = recipients[0].get('messageId', '') if recipients else ''
            cost = recipients[0].get('cost', None) if recipients else None
            logger.info('SMS sent to %s: %s', phone, body)
            return {'success': True, 'external_id': external_id, 'error': None}
    except URLError as e:
        logger.error('Failed to send SMS to %s: %s', phone, e)
        return {'success': False, 'external_id': None, 'error': str(e)}


def format_delivery_for_ussd(delivery) -> str:
    qty = float(delivery.quantity_kg or delivery.volume_litres or 0)
    unit = 'L' if delivery.volume_litres else 'K'
    grade = delivery.grade or '-'
    date_str = delivery.date_delivered.strftime('%d/%m')
    return f'{date_str} - {qty}{unit} Gr{grade}'
