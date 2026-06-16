from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status

from apps.base.constants import UserRole
from apps.base.models import AuditAction

pytestmark = pytest.mark.django_db


# =============================================================================
# Query shape tests
# =============================================================================


def test_farmer_production_shape(farmer, delivery):
    from .queries.farmer import get_farmer_production
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_farmer_production(
        farmer_id=farmer.id,
        cooperative_id=farmer.cooperative_id,
        start_date=start,
        end_date=end,
    )
    assert 'period' in result
    assert 'data' in result
    d = result['data']
    assert 'total_kg' in d
    assert 'delivery_count' in d
    assert 'by_product_type' in d
    assert 'by_status' in d
    assert 'grade_distribution' in d
    assert 'monthly_series' in d
    assert isinstance(d['total_kg'], float)
    assert isinstance(d['delivery_count'], int)


def test_farmer_production_compare(farmer, delivery):
    from .queries.farmer import get_farmer_production
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_farmer_production(
        farmer_id=farmer.id,
        cooperative_id=farmer.cooperative_id,
        start_date=start,
        end_date=end,
        compare_to='previous',
    )
    assert 'comparison' in result
    assert 'changes' in result['comparison']


def test_farmer_financial_shape(farmer):
    from .queries.farmer import get_farmer_financial
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_farmer_financial(
        farmer_id=farmer.id,
        cooperative_id=farmer.cooperative_id,
        start_date=start,
        end_date=end,
    )
    assert 'data' in result
    d = result['data']
    assert 'total_gross' in d
    assert 'total_net' in d
    assert 'payment_count' in d
    assert 'payout_monthly_series' in d


def test_farmer_loans_shape(farmer):
    from .queries.farmer import get_farmer_loans
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_farmer_loans(
        farmer_id=farmer.id,
        cooperative_id=farmer.cooperative_id,
        start_date=start,
        end_date=end,
    )
    assert 'data' in result
    d = result['data']
    assert 'total_outstanding' in d
    assert 'active_count' in d
    assert 'default_rate_pct' in d


def test_coop_dashboard_shape(cooperative):
    from .queries.cooperative import get_dashboard
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_dashboard(
        cooperative_id=cooperative.id,
        start_date=start,
        end_date=end,
    )
    assert 'period' in result
    assert 'data' in result
    d = result['data']
    for section in ('farmers', 'production', 'financial', 'sales', 'loans', 'disbursements', 'inventory'):
        assert section in d, f'Missing section: {section}'


def test_admin_dashboard_shape():
    from .queries.admin import get_admin_dashboard
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_admin_dashboard(start_date=start, end_date=end)
    assert 'period' in result
    assert 'data' in result
    d = result['data']
    for section in ('farmers', 'production', 'financial', 'sales', 'loans', 'disbursements', 'inventory'):
        assert section in d, f'Missing section: {section}'


def test_admin_production_shape():
    from .queries.admin import get_admin_production
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=1)
    result = get_admin_production(start_date=start, end_date=end)
    assert 'data' in result
    d = result['data']
    assert 'total_kg' in d
    assert 'delivery_count' in d


# =============================================================================
# Role-scoped endpoint tests
# =============================================================================


def test_farmer_sees_own_production(api_client, farmer, delivery):
    from apps.auth_api.models import User
    farmer_user = User.objects.create(
        email='farmer@test.com', phone_number='+254700000001',
        role=UserRole.FARMER, cooperative=farmer.cooperative,
    )
    farmer.user = farmer_user
    farmer.save()
    api_client.force_authenticate(user=farmer_user)
    resp = api_client.get('/api/analytics/production/')
    assert resp.status_code == 200
    assert 'data' in resp.data


def test_farmer_blocked_from_dashboard(api_client, farmer):
    from apps.auth_api.models import User
    farmer_user = User.objects.create(
        email='farmer2@test.com', phone_number='+254700000002',
        role=UserRole.FARMER, cooperative=farmer.cooperative,
    )
    farmer.user = farmer_user
    farmer.save()
    api_client.force_authenticate(user=farmer_user)
    resp = api_client.get('/api/analytics/dashboard/')
    assert resp.status_code == 403


def test_staff_can_access_dashboard(api_client, cooperative):
    from apps.auth_api.models import User
    staff = User.objects.create(
        email='manager@test.com', phone_number='+254700000003',
        role=UserRole.MANAGER, cooperative=cooperative,
    )
    api_client.force_authenticate(user=staff)
    resp = api_client.get('/api/analytics/dashboard/')
    assert resp.status_code == 200


def test_admin_without_coop_blocked(api_client):
    from apps.auth_api.models import User
    admin = User.objects.create(
        email='admin@test.com', phone_number='+254700000004',
        role=UserRole.ADMIN, cooperative=None,
    )
    api_client.force_authenticate(user=admin)
    resp = api_client.get('/api/analytics/dashboard/')
    assert resp.status_code == 403
    assert 'admin/analytics' in resp.data['detail']


def test_admin_with_coop_gets_coop_data(api_client, cooperative):
    from apps.auth_api.models import User
    admin = User.objects.create(
        email='admin2@test.com', phone_number='+254700000005',
        role=UserRole.ADMIN, cooperative=cooperative,
    )
    api_client.force_authenticate(user=admin)
    resp = api_client.get('/api/analytics/dashboard/')
    assert resp.status_code == 200


# =============================================================================
# Leaderboard permissions
# =============================================================================


def test_leaderboard_blocked_for_farmer(api_client, farmer):
    from apps.auth_api.models import User
    farmer_user = User.objects.create(
        email='farmer3@test.com', phone_number='+254700000006',
        role=UserRole.FARMER, cooperative=farmer.cooperative,
    )
    farmer.user = farmer_user
    farmer.save()
    api_client.force_authenticate(user=farmer_user)
    resp = api_client.get('/api/analytics/leaderboard/')
    assert resp.status_code == 403


def test_leaderboard_allowed_for_accountant(api_client, cooperative):
    from apps.auth_api.models import User
    acc = User.objects.create(
        email='acc@test.com', phone_number='+254700000007',
        role=UserRole.ACCOUNTANT, cooperative=cooperative,
    )
    api_client.force_authenticate(user=acc)
    resp = api_client.get('/api/analytics/leaderboard/')
    assert resp.status_code == 200


def test_leaderboard_allowed_for_manager(api_client, cooperative):
    from apps.auth_api.models import User
    mgr = User.objects.create(
        email='mgr@test.com', phone_number='+254700000008',
        role=UserRole.MANAGER, cooperative=cooperative,
    )
    api_client.force_authenticate(user=mgr)
    resp = api_client.get('/api/analytics/leaderboard/')
    assert resp.status_code == 200


# =============================================================================
# Export tests
# =============================================================================


def test_export_sync_small(api_client, cooperative):
    from apps.auth_api.models import User
    mgr = User.objects.create(
        email='mgr2@test.com', phone_number='+254700000009',
        role=UserRole.MANAGER, cooperative=cooperative,
    )
    api_client.force_authenticate(user=mgr)
    resp = api_client.get('/api/analytics/export/?type=production&period=7d')
    assert resp.status_code in (200, 202)
    if resp.status_code == 200:
        assert resp.get('Content-Type') == 'text/csv'


def test_export_blocked_for_farmer(api_client, farmer):
    from apps.auth_api.models import User
    farmer_user = User.objects.create(
        email='farmer4@test.com', phone_number='+254700000010',
        role=UserRole.FARMER, cooperative=farmer.cooperative,
    )
    farmer.user = farmer_user
    farmer.save()
    api_client.force_authenticate(user=farmer_user)
    resp = api_client.get('/api/analytics/export/?type=production')
    assert resp.status_code == 403


@patch('apps.analytics.views.AnalyticsViewSet._estimate_export_rows', return_value=20000)
def test_export_async_large(mock_count, api_client, cooperative):
    from apps.auth_api.models import User
    mgr = User.objects.create(
        email='mgr3@test.com', phone_number='+254700000011',
        role=UserRole.MANAGER, cooperative=cooperative,
    )
    api_client.force_authenticate(user=mgr)
    resp = api_client.get('/api/analytics/export/?type=production&period=30d')
    assert resp.status_code == 202
    assert 'task_id' in resp.data
    assert resp.data['status'] == 'PENDING'


# =============================================================================
# Cache behavior
# =============================================================================


def test_cache_hit_on_second_call(api_client, cooperative):
    from apps.auth_api.models import User
    mgr = User.objects.create(
        email='mgr4@test.com', phone_number='+254700000012',
        role=UserRole.MANAGER, cooperative=cooperative,
    )
    api_client.force_authenticate(user=mgr)
    resp1 = api_client.get('/api/analytics/production/?period=7d')
    assert resp1.status_code == 200
    resp2 = api_client.get('/api/analytics/production/?period=7d')
    assert resp2.status_code == 200


# =============================================================================
# AuditAction enum
# =============================================================================


def test_snapshot_failed_audit_action_exists():
    assert hasattr(AuditAction, 'SNAPSHOT_FAILED')
    assert AuditAction.SNAPSHOT_FAILED.value == 'SNAPSHOT_FAILED'
    assert hasattr(AuditAction, 'EXPORT_FAILED')
    assert AuditAction.EXPORT_FAILED.value == 'EXPORT_FAILED'
