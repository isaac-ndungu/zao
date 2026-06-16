from datetime import date, timedelta
from decimal import Decimal

from django.db.models import IntegerField, Q, Value
from django.db.models.functions import Coalesce

from apps.base.constants import UserRole

SUPPORTED_SCHEMA_VERSION = 1


def parse_period(start_date=None, end_date=None, period='30d'):
    """Return (start_date, end_date) from params or period shortcut."""
    today = date.today()
    if start_date and end_date:
        return start_date, end_date

    period = period or '30d'
    mapping = {
        '24h': today - timedelta(days=1),
        '7d': today - timedelta(days=7),
        '30d': today - timedelta(days=30),
        '90d': today - timedelta(days=90),
        '1y': today - timedelta(days=365),
        'all': date(2000, 1, 1),
    }
    end = end_date or today
    start = start_date or mapping.get(period, today - timedelta(days=30))
    return start, end


def scope_filter(scope_type, cooperative_id=None, farmer_id=None):
    """Return a Q filter for the given scope."""
    if scope_type == 'farmer':
        return Q(farmer_id=farmer_id)
    if scope_type == 'cooperative':
        return Q(cooperative_id=cooperative_id)
    return Q()


def farmer_reference_filter(scope_type, farmer_id=None):
    """Return a Q filter for models with a 'farmer' FK."""
    if scope_type == 'farmer':
        return Q(farmer_id=farmer_id)
    return Q()


def get_role_scope(user):
    """Determine the analytics scope for a user."""
    if user.role == UserRole.ADMIN:
        return {'scope': 'global'}
    if user.role == UserRole.FARMER:
        farmer_profile = getattr(user, 'farmer_profile', None)
        if farmer_profile is None:
            return {'scope': 'none'}
        return {'scope': 'farmer', 'farmer_id': farmer_profile.id}
    return {'scope': 'cooperative', 'cooperative_id': user.cooperative_id}


def coalesce_sum(expression, output_field=None):
    """Wrap a Sum() in Coalesce to return 0 instead of None.

    Use output_field=IntegerField() when summing integer fields to
    avoid Expression contains mixed types errors.
    """
    if output_field:
        return Coalesce(expression, Value(0, output_field=output_field), output_field=output_field)
    return Coalesce(expression, Decimal('0'))


def migrate_snapshot_data(data, from_version, to_version=SUPPORTED_SCHEMA_VERSION):
    """Forward-migrate snapshot data to the current schema version."""
    if from_version >= to_version:
        return data

    current = dict(data)

    if from_version < 1:
        current.setdefault('farmers', {})
        current.setdefault('production', {})
        current.setdefault('financial', {})
        current.setdefault('sales', {})
        current.setdefault('loans', {})
        current.setdefault('disbursements', {})

    current['_schema_version'] = to_version
    return current


def compare_periods(current, previous):
    """Compute percentage change between two period values.

    Returns None (null) when the change is from zero to non-zero
    (meaningful percentage is infinite/undefined).
    Returns 0.0 when both are zero (no change).
    """
    changes = {}
    for key in current:
        if not isinstance(current[key], (int, float, Decimal)):
            continue
        curr = float(current[key] or 0)
        prev = float(previous.get(key, 0) or 0)

        if prev == 0 and curr == 0:
            changes[key] = 0.0
        elif prev == 0:
            changes[key] = None
        else:
            changes[key] = round((curr - prev) / prev * 100, 1)
    return changes
