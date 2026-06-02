import json
import re
from typing import List

from apps.base.models import AuditLog


def normalize_phone(value: str) -> str:
    value = value.strip()
    if value.startswith('+'):
        value = value[1:]
    if value.startswith('0'):
        value = '254' + value[1:]
    return value


def normalize_phone_for_sms(phone: str) -> str:
    phone = phone.strip()
    if phone.startswith('+254') and len(phone) == 13:
        return phone
    if phone.startswith('254') and len(phone) == 12:
        return f'+{phone}'
    if phone.startswith('0') and len(phone) == 10:
        return f'+254{phone[1:]}'
    if re.match(r'^[17]\d{8}$', phone) and len(phone) == 9:
        return f'+254{phone}'
    raise ValueError(f'Cannot normalize phone number for SMS: {phone}')


KENYA_PHONE_RE = re.compile(r'^(?:\+254|0|254)?7\d{8}$')

KENYA_ID_RE = re.compile(r'^\d{6,8}$')

NATURAL_SORT_RE = re.compile(r'(\d+)')


def natural_sort_key(value: str) -> list:
    """Split string into (text, int) parts for natural (human) sorting.
    E.g. DAIR-2026-10 sorts after DAIR-2026-2.
    """
    return [int(p) if p.isdigit() else p for p in NATURAL_SORT_RE.split(value)]


def _serialize(value):
    if isinstance(value, (dict, list)):
        return json.loads(json.dumps(value, default=str))
    return value


def log_audit(actor, resource_type, resource_id, action, previous_value=None, new_value=None, cooperative_id=None, ip_address=None):
    if not cooperative_id and actor:
        cooperative_id = getattr(actor, 'cooperative_id', None)
    return AuditLog.objects.create(
        actor=actor,
        cooperative_id=cooperative_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        previous_value=_serialize(previous_value),
        new_value=_serialize(new_value),
        ip_address=ip_address,
    )
