import json
import re

from apps.base.models import AuditLog


def normalize_phone(value: str) -> str:
    value = value.strip()
    if value.startswith('+'):
        value = value[1:]
    if value.startswith('0'):
        value = '254' + value[1:]
    return value


KENYA_PHONE_RE = re.compile(r'^(?:\+254|0|254)?7\d{8}$')

KENYA_ID_RE = re.compile(r'^\d{6,8}$')


def _serialize(value):
    if isinstance(value, (dict, list)):
        return json.loads(json.dumps(value, default=str))
    return value


def log_audit(actor, resource_type, resource_id, action, previous_value=None, new_value=None, cooperative_id=None):
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
    )
