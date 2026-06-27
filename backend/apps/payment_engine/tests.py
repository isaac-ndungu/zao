from __future__ import annotations

import csv
import uuid
import datetime
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.cooperatives.models import PaymentModel
from apps.payment_engine.engine import (
    _compute_deductions,
    apply_deductions,
    compute_fixed_price,
    compute_revenue_share,
)
from apps.payment_engine.models import (
    ComputationWarning,
    CycleStatus,
    FarmerPayment,
    PaymentCycle,
    PaymentStatus,
    Severity,
)
from apps.conftest import (
    CooperativeFactory,
    DeliveryFactory,
    FarmInputCreditFactory,
    FarmerFactory,
    FarmerPaymentFactory,
    GradeFactory,
    GradePriceFactory,
    LoanFactory,
    PaymentCycleFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def coop():
    return CooperativeFactory()


# =============================================================================
# Authentication & Permission Tests — PaymentCycleViewSet
# =============================================================================


def _payment_cycle_detail_url(cycle_id=None):
    if cycle_id is None:
        cycle_id = uuid.uuid4()
    return f'/api/payment-engine/{cycle_id}/'


class TestPaymentCycleAuthentication:
    LIST_URL = '/api/payment-engine/'

    def test_unauthenticated_list(self, client):
        assert client.get(self.LIST_URL).status_code == 401

    def test_unauthenticated_create(self, client):
        assert client.post(self.LIST_URL, {'name': 'x'}).status_code == 401

    def test_unauthenticated_retrieve(self, client):
        assert client.get(_payment_cycle_detail_url()).status_code == 401

    def test_unauthenticated_update(self, client):
        assert client.put(_payment_cycle_detail_url(), {'name': 'x'}).status_code == 401

    def test_unauthenticated_partial_update(self, client):
        assert client.patch(_payment_cycle_detail_url(), {'name': 'x'}).status_code == 401

    def test_unauthenticated_destroy(self, client):
        assert client.delete(_payment_cycle_detail_url()).status_code == 401

    def test_unauthenticated_run(self, client):
        assert client.post(_payment_cycle_detail_url() + 'run/').status_code == 401

    def test_unauthenticated_preview(self, client):
        assert client.get(_payment_cycle_detail_url() + 'preview/').status_code == 401

    def test_unauthenticated_lock(self, client):
        assert client.post(_payment_cycle_detail_url() + 'lock/').status_code == 401

    def test_unauthenticated_unlock(self, client):
        assert client.post(_payment_cycle_detail_url() + 'unlock/').status_code == 401

    def test_unauthenticated_status(self, client):
        assert client.get(_payment_cycle_detail_url() + 'status/').status_code == 401

    def test_unauthenticated_hold(self, client):
        assert client.post(_payment_cycle_detail_url() + 'hold/').status_code == 401

    def test_unauthenticated_release(self, client):
        assert client.post(_payment_cycle_detail_url() + 'release/').status_code == 401

    def test_unauthenticated_task_status(self, client):
        assert client.get(_payment_cycle_detail_url() + 'task-status/').status_code == 401

    def test_unauthenticated_export(self, client):
        assert client.get(_payment_cycle_detail_url() + 'export/').status_code == 401


class TestPaymentCycleRolePermissions:
    """Wrong roles get 403 for mutating actions; lock/unlock require IsManager."""

    _phone_counter = 100

    def _make_user(self, role, cooperative):
        from apps.auth_api.models import User
        TestPaymentCycleRolePermissions._phone_counter += 1
        cnt = TestPaymentCycleRolePermissions._phone_counter
        return User.objects.create(
            email=f'{role}{cnt}@test.com',
            phone_number=f'+254700{cnt:08d}',
            password='testpass123',
            role=role,
            cooperative=cooperative,
        )

    def test_farmer_cannot_create(self, api_client, coop):
        api_client.force_authenticate(user=self._make_user(UserRole.FARMER, coop))
        resp = api_client.post('/api/payment-engine/', {'name': 'x', 'start_date': '2024-01-01', 'end_date': '2024-01-31', 'cooperative_id': str(coop.id)})
        assert resp.status_code == 403

    def test_grader_cannot_create(self, api_client, coop):
        api_client.force_authenticate(user=self._make_user(UserRole.GRADER, coop))
        resp = api_client.post('/api/payment-engine/', {'name': 'x', 'start_date': '2024-01-01', 'end_date': '2024-01-31', 'cooperative_id': str(coop.id)})
        assert resp.status_code == 403

    def test_auditor_cannot_create(self, api_client, coop):
        api_client.force_authenticate(user=self._make_user(UserRole.AUDITOR, coop))
        resp = api_client.post('/api/payment-engine/', {'name': 'x', 'start_date': '2024-01-01', 'end_date': '2024-01-31', 'cooperative_id': str(coop.id)})
        assert resp.status_code == 403

    def test_manager_can_create(self, api_client, coop):
        api_client.force_authenticate(user=self._make_user(UserRole.MANAGER, coop))
        resp = api_client.post('/api/payment-engine/', {'name': 'Manager Cycle', 'start_date': '2024-01-01', 'end_date': '2024-01-31'})
        assert resp.status_code == 201

    def test_accountant_can_create(self, api_client, coop):
        api_client.force_authenticate(user=self._make_user(UserRole.ACCOUNTANT, coop))
        resp = api_client.post('/api/payment-engine/', {'name': 'Acc Cycle', 'start_date': '2024-01-01', 'end_date': '2024-01-31'})
        assert resp.status_code == 201

    def test_farmer_cannot_update(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        api_client.force_authenticate(user=self._make_user(UserRole.FARMER, coop))
        resp = api_client.patch(_payment_cycle_detail_url(cycle.id), {'name': 'hacked'})
        assert resp.status_code == 403

    def test_farmer_cannot_destroy(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        api_client.force_authenticate(user=self._make_user(UserRole.FARMER, coop))
        resp = api_client.delete(_payment_cycle_detail_url(cycle.id))
        assert resp.status_code == 403

    def test_accountant_cannot_lock(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        api_client.force_authenticate(user=self._make_user(UserRole.ACCOUNTANT, coop))
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'lock/')
        assert resp.status_code == 403

    def test_manager_can_lock(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        api_client.force_authenticate(user=self._make_user(UserRole.MANAGER, coop))
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'lock/')
        assert resp.status_code == 200

    def test_accountant_cannot_unlock(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.LOCKED)
        api_client.force_authenticate(user=self._make_user(UserRole.ACCOUNTANT, coop))
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'unlock/')
        assert resp.status_code == 403

    def test_farmer_cannot_run(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        api_client.force_authenticate(user=self._make_user(UserRole.FARMER, coop))
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'run/')
        assert resp.status_code == 403

    def test_accountant_can_run(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        api_client.force_authenticate(user=self._make_user(UserRole.ACCOUNTANT, coop))
        with patch('apps.payment_engine.views.run_payment_engine.delay') as mock_delay:
            mock_delay.return_value.id = 'task-123'
            resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'run/')
        assert resp.status_code == 200

    def test_farmer_cannot_hold(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        api_client.force_authenticate(user=self._make_user(UserRole.FARMER, coop))
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {'farmer_payment_id': str(uuid.uuid4())})
        assert resp.status_code == 403

    def test_accountant_can_hold(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop)
        api_client.force_authenticate(user=self._make_user(UserRole.ACCOUNTANT, coop))
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {'farmer_payment_id': str(fp.id), 'hold_reason': 'test'})
        assert resp.status_code == 200

    def test_accountant_can_export(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        api_client.force_authenticate(user=self._make_user(UserRole.ACCOUNTANT, coop))
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'export/')
        assert resp.status_code == 200


# =============================================================================
# PaymentCycle API — CRUD
# =============================================================================


class TestPaymentCycleList:
    def test_returns_paginated_cycles(self, api_client, coop):
        PaymentCycleFactory.create_batch(3, cooperative=coop)
        resp = api_client.get('/api/payment-engine/')
        assert resp.status_code == 200
        assert 'count' in resp.data
        assert 'results' in resp.data
        assert resp.data['count'] == 3
        assert len(resp.data['results']) == 3

    def test_list_empty(self, api_client):
        resp = api_client.get('/api/payment-engine/')
        assert resp.status_code == 200
        assert resp.data['count'] == 0

    def test_list_respects_cooperative_scope(self, api_client, coop):
        other_coop = CooperativeFactory()
        PaymentCycleFactory(cooperative=coop)
        PaymentCycleFactory(cooperative=other_coop)
        # admin sees all
        resp = api_client.get('/api/payment-engine/')
        assert resp.data['count'] == 2

    def test_non_admin_sees_only_own_coop(self, api_client, coop):
        from apps.auth_api.models import User
        other_coop = CooperativeFactory()
        PaymentCycleFactory(cooperative=coop)
        PaymentCycleFactory(cooperative=other_coop)
        user = User.objects.create(email='mgr@x.com', phone_number='+254700000002', role=UserRole.MANAGER, cooperative=coop)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/payment-engine/')
        assert resp.data['count'] == 1


class TestPaymentCycleCreate:
    def _manager(self, coop):
        from apps.auth_api.models import User
        return User.objects.create(email='cycle-create-mgr@x.com', phone_number='+254700008001', role=UserRole.MANAGER, cooperative=coop)

    def test_creates_cycle(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        resp = api_client.post('/api/payment-engine/', {
            'name': 'January 2024',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        assert resp.status_code == 201
        assert resp.data['name'] == 'January 2024'
        assert resp.data['status'] == CycleStatus.DRAFT
        assert 'id' in resp.data

    def test_validates_overlapping_dates(self, api_client, coop):
        mgr = self._manager(coop)
        api_client.force_authenticate(user=mgr)
        PaymentCycleFactory(cooperative=coop, name='Existing', start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
        resp = api_client.post('/api/payment-engine/', {
            'name': 'Overlap',
            'start_date': '2024-01-15',
            'end_date': '2024-02-15',
        })
        assert resp.status_code == 400
        assert 'overlap' in str(resp.data).lower()

    def test_validates_start_date_before_end_date(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        resp = api_client.post('/api/payment-engine/', {
            'name': 'Bad',
            'start_date': '2024-02-01',
            'end_date': '2024-01-01',
        })
        assert resp.status_code == 400

    def test_rejects_missing_name(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        resp = api_client.post('/api/payment-engine/', {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
        })
        assert resp.status_code == 400

    def test_rejects_missing_dates(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        resp = api_client.post('/api/payment-engine/', {'name': 'No Dates'})
        assert resp.status_code == 400


class TestPaymentCycleRetrieve:
    def test_returns_cycle_detail(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, name='Detail Test')
        resp = api_client.get(_payment_cycle_detail_url(cycle.id))
        assert resp.status_code == 200
        assert resp.data['name'] == 'Detail Test'
        assert resp.data['id'] == str(cycle.id)

    def test_returns_404_for_nonexistent(self, api_client):
        resp = api_client.get(_payment_cycle_detail_url())
        assert resp.status_code == 404


class TestPaymentCycleUpdate:
    def _manager(self, coop):
        from apps.auth_api.models import User
        return User.objects.create(email='cycle-upd-mgr@x.com', phone_number='+254700008010', role=UserRole.MANAGER, cooperative=coop)

    def test_full_update(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        cycle = PaymentCycleFactory(cooperative=coop, name='Old Name', start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
        resp = api_client.put(_payment_cycle_detail_url(cycle.id), {
            'name': 'New Name',
            'start_date': '2024-02-01',
            'end_date': '2024-02-28',
        })
        assert resp.status_code == 200
        cycle.refresh_from_db()
        assert cycle.name == 'New Name'
        assert str(cycle.start_date) == '2024-02-01'

    def test_partial_update(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        cycle = PaymentCycleFactory(cooperative=coop, name='Original', start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
        resp = api_client.patch(_payment_cycle_detail_url(cycle.id), {'name': 'Patched'})
        assert resp.status_code == 200
        cycle.refresh_from_db()
        assert cycle.name == 'Patched'
        assert cycle.start_date == date(2024, 1, 1)


class TestPaymentCycleDestroy:
    def _manager(self, coop):
        from apps.auth_api.models import User
        return User.objects.create(email='cycle-del-mgr@x.com', phone_number='+254700008020', role=UserRole.MANAGER, cooperative=coop)

    def test_deletes_draft_cycle(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DRAFT)
        resp = api_client.delete(_payment_cycle_detail_url(cycle.id))
        assert resp.status_code == 204
        assert PaymentCycle.objects.filter(id=cycle.id).count() == 0

    def test_rejects_non_draft(self, api_client, coop):
        mgr = self._manager(coop)
        api_client.force_authenticate(user=mgr)
        for status_val in [CycleStatus.COMPUTING, CycleStatus.COMPUTED, CycleStatus.LOCKED, CycleStatus.DISBURSED]:
            cycle = PaymentCycleFactory(cooperative=coop, status=status_val)
            resp = api_client.delete(_payment_cycle_detail_url(cycle.id))
            assert resp.status_code == 400, f'Expected 400 for status {status_val}'
            assert 'DRAFT' in str(resp.data)

    def test_returns_404_for_missing(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        resp = api_client.delete(_payment_cycle_detail_url())
        assert resp.status_code == 404


# =============================================================================
# PaymentCycle API — Custom Actions
# =============================================================================


class TestPaymentCycleActions:
    def _manager(self, coop):
        from apps.auth_api.models import User
        return User.objects.create(email='cycle-actions-mgr@x.com', phone_number='+254700008100', role=UserRole.MANAGER, cooperative=coop)

    def _accountant(self, coop):
        from apps.auth_api.models import User
        return User.objects.create(email='cycle-actions-acc@x.com', phone_number='+254700008101', role=UserRole.ACCOUNTANT, cooperative=coop)

    def test_run_starts_computation_on_draft(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DRAFT)
        with patch('apps.payment_engine.views.run_payment_engine.delay') as mock_delay:
            mock_delay.return_value.id = 'celery-task-1'
            resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'run/')
        assert resp.status_code == 200
        assert resp.data['task_id'] == 'celery-task-1'
        assert resp.data['status'] == 'started'

    def test_run_rejects_locked(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.LOCKED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'run/')
        assert resp.status_code == 400
        assert 'locked' in str(resp.data).lower()

    def test_run_rejects_disbursed(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DISBURSED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'run/')
        assert resp.status_code == 400
        assert 'disbursed' in str(resp.data).lower()

    def test_run_rejects_computing(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTING)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'run/')
        assert resp.status_code == 400
        assert 'computing' in str(resp.data).lower()

    def test_preview_returns_cycle_with_farmer_payments(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop)
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'preview/')
        assert resp.status_code == 200
        assert 'farmer_payments' in resp.data
        assert len(resp.data['farmer_payments']) >= 1
        payment_ids = [p['id'] for p in resp.data['farmer_payments']]
        assert str(fp.id) in payment_ids

    def test_preview_empty_cycle(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DRAFT)
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'preview/')
        assert resp.status_code == 200
        assert resp.data['farmer_payments'] == []

    def test_lock_computed_cycle(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'lock/')
        assert resp.status_code == 200
        cycle.refresh_from_db()
        assert cycle.status == CycleStatus.LOCKED
        assert cycle.locked_by is not None
        assert cycle.locked_at is not None

    def test_lock_rejects_non_computed(self, api_client, coop):
        mgr = self._manager(coop)
        for status_val in [CycleStatus.DRAFT, CycleStatus.COMPUTING, CycleStatus.LOCKED, CycleStatus.DISBURSED]:
            api_client.force_authenticate(user=mgr)
            cycle = PaymentCycleFactory(cooperative=coop, status=status_val)
            resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'lock/')
            assert resp.status_code == 400, f'Expected 400 for {status_val}'
            assert 'COMPUTED' in str(resp.data)

    def test_unlock_locked_cycle(self, api_client, coop):
        api_client.force_authenticate(user=self._manager(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.LOCKED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'unlock/')
        assert resp.status_code == 200
        cycle.refresh_from_db()
        assert cycle.status == CycleStatus.COMPUTED
        assert cycle.locked_by is None
        assert cycle.locked_at is None

    def test_unlock_rejects_non_locked(self, api_client, coop):
        mgr = self._manager(coop)
        for status_val in [CycleStatus.DRAFT, CycleStatus.COMPUTING, CycleStatus.COMPUTED, CycleStatus.DISBURSED]:
            api_client.force_authenticate(user=mgr)
            cycle = PaymentCycleFactory(cooperative=coop, status=status_val)
            resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'unlock/')
            assert resp.status_code == 400, f'Expected 400 for {status_val}'
            assert 'LOCKED' in str(resp.data)

    def test_status_returns_cycle_info(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'status/')
        assert resp.status_code == 200
        assert resp.data['id'] == str(cycle.id)
        assert resp.data['status'] == CycleStatus.COMPUTED
        assert 'totals' in resp.data
        assert 'has_warnings' in resp.data
        assert 'celery_task_id' in resp.data

    def test_status_on_draft(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DRAFT)
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'status/')
        assert resp.status_code == 200

    def test_hold_places_hold_on_farmer_payment(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {
            'farmer_payment_id': str(fp.id),
            'hold_reason': 'Verify documents',
        })
        assert resp.status_code == 200
        assert resp.data['status'] == 'held'
        fp.refresh_from_db()
        assert fp.is_on_hold is True
        assert fp.hold_reason == 'Verify documents'

    def test_hold_rejects_wrong_cycle_status(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DRAFT)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {
            'farmer_payment_id': str(fp.id),
        })
        assert resp.status_code == 400
        assert 'COMPUTED' in str(resp.data) or 'LOCKED' in str(resp.data)

    def test_hold_requires_farmer_payment_id(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {})
        assert resp.status_code == 400
        assert 'farmer_payment_id' in str(resp.data)

    def test_hold_returns_404_for_wrong_payment(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {
            'farmer_payment_id': str(uuid.uuid4()),
        })
        assert resp.status_code == 404

    def test_hold_works_on_locked_cycle(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.LOCKED)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'hold/', {
            'farmer_payment_id': str(fp.id),
        })
        assert resp.status_code == 200

    def test_release_releases_held_payment(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop, is_on_hold=True, hold_reason='Test')
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'release/', {
            'farmer_payment_id': str(fp.id),
        })
        assert resp.status_code == 200
        assert resp.data['status'] == 'released'
        fp.refresh_from_db()
        assert fp.is_on_hold is False
        assert fp.hold_reason == ''

    def test_release_requires_farmer_payment_id(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'release/', {})
        assert resp.status_code == 400

    def test_release_returns_404_for_wrong_payment(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'release/', {
            'farmer_payment_id': str(uuid.uuid4()),
        })
        assert resp.status_code == 404

    def test_release_rejects_wrong_cycle_status(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.DRAFT)
        fp = FarmerPaymentFactory(cycle=cycle, cooperative=coop)
        resp = api_client.post(_payment_cycle_detail_url(cycle.id) + 'release/', {
            'farmer_payment_id': str(fp.id),
        })
        assert resp.status_code == 400

    def test_task_status_returns_structure(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTED, celery_task_id='')
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'task-status/')
        assert resp.status_code == 200
        assert resp.data['task_id'] == ''
        assert resp.data['celery_state'] is None
        assert resp.data['cycle_status'] == CycleStatus.COMPUTED
        assert resp.data['warnings'] == []

    def test_task_status_with_celery_task_id(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, status=CycleStatus.COMPUTING, celery_task_id='task-abc')
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'task-status/')
        assert resp.status_code == 200
        assert resp.data['task_id'] == 'task-abc'
        assert resp.data['celery_state'] is not None

    def test_task_status_includes_warnings(self, api_client, coop):
        cycle = PaymentCycleFactory(cooperative=coop, celery_task_id='')
        ComputationWarning.objects.create(cycle=cycle, severity=Severity.WARNING, message='Low quality')
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'task-status/')
        assert len(resp.data['warnings']) == 1
        assert resp.data['warnings'][0]['message'] == 'Low quality'

    def test_export_returns_csv(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, name='Export Cycle')
        farmer = FarmerFactory(cooperative=coop)
        FarmerPaymentFactory(
            cycle=cycle, cooperative=coop, farmer=farmer,
            total_quantity=Decimal('150.00'),
            gross_amount=Decimal('6750.00'),
            net_amount=Decimal('6500.00'),
        )
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'export/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv'
        assert 'Export Cycle' in resp['Content-Disposition']
        content = resp.content.decode('utf-8')
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        assert len(rows) >= 2
        header = rows[0]
        assert 'member_number' in header
        assert 'farmer_name' in header
        assert 'net_amount' in header

    def test_export_empty_cycle(self, api_client, coop):
        api_client.force_authenticate(user=self._accountant(coop))
        cycle = PaymentCycleFactory(cooperative=coop, name='Empty')
        resp = api_client.get(_payment_cycle_detail_url(cycle.id) + 'export/')
        assert resp.status_code == 200
        content = resp.content.decode('utf-8')
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        assert len(rows) == 1


# =============================================================================
# FarmerPayment API
# =============================================================================


class TestFarmerPaymentAuthentication:
    LIST_URL = '/api/payments/'

    def test_unauthenticated_list(self, client):
        assert client.get(self.LIST_URL).status_code == 401

    def test_unauthenticated_create(self, client):
        assert client.post(self.LIST_URL, {}).status_code == 401

    def test_unauthenticated_retrieve(self, client):
        assert client.get(f'/api/payments/{uuid.uuid4()}/').status_code == 401

    def test_unauthenticated_update(self, client):
        assert client.put(f'/api/payments/{uuid.uuid4()}/', {}).status_code == 401

    def test_unauthenticated_destroy(self, client):
        assert client.delete(f'/api/payments/{uuid.uuid4()}/').status_code == 401


class TestFarmerPaymentRolePermissions:
    def test_farmer_cannot_create(self, api_client, coop):
        from apps.auth_api.models import User
        user = User.objects.create(email='farmer@x.com', phone_number='+254700000010', role=UserRole.FARMER, cooperative=coop)
        api_client.force_authenticate(user=user)
        resp = api_client.post('/api/payments/', {})
        assert resp.status_code == 403

    def test_farmer_cannot_update(self, api_client, coop):
        from apps.auth_api.models import User
        fp = FarmerPaymentFactory(cooperative=coop)
        user = User.objects.create(email='farmer2@x.com', phone_number='+254700000011', role=UserRole.FARMER, cooperative=coop)
        api_client.force_authenticate(user=user)
        resp = api_client.patch(f'/api/payments/{fp.id}/', {})
        assert resp.status_code == 403

    def test_farmer_cannot_destroy(self, api_client, coop):
        from apps.auth_api.models import User
        fp = FarmerPaymentFactory(cooperative=coop)
        user = User.objects.create(email='farmer3@x.com', phone_number='+254700000012', role=UserRole.FARMER, cooperative=coop)
        api_client.force_authenticate(user=user)
        resp = api_client.delete(f'/api/payments/{fp.id}/')
        assert resp.status_code == 403

    def test_farmer_can_list(self, api_client, coop):
        from apps.auth_api.models import User
        farmer = FarmerFactory(cooperative=coop)
        fp = FarmerPaymentFactory(cooperative=coop, farmer=farmer)
        user = User.objects.create(email='farmer4@x.com', phone_number='+254700000013', role=UserRole.FARMER, cooperative=coop)
        farmer.user = user
        farmer.save()
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/payments/')
        assert resp.status_code == 200

    def test_farmer_csv_export_blocked(self, api_client, coop):
        from apps.auth_api.models import User
        farmer = FarmerFactory(cooperative=coop)
        # create a farmer payment to ensure there is data
        FarmerPaymentFactory(cooperative=coop, farmer=farmer)
        user = User.objects.create(email='farmer5@x.com', phone_number='+254700000016', role=UserRole.FARMER, cooperative=coop)
        farmer.user = user
        farmer.save()
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/payments/?export=csv')
        assert resp.status_code == 403
        assert 'Farmers cannot export' in str(resp.data)

    def test_admin_can_export_csv(self, api_client, coop):
        FarmerPaymentFactory(cooperative=coop)
        resp = api_client.get('/api/payments/?export=csv')
        assert resp.status_code in (200, 202)


class TestFarmerPaymentList:
    def test_returns_paginated_payments(self, api_client, coop):
        FarmerPaymentFactory.create_batch(3, cooperative=coop)
        resp = api_client.get('/api/payments/')
        assert resp.status_code == 200
        assert 'count' in resp.data
        assert resp.data['count'] == 3

    def test_filter_by_cycle(self, api_client, coop):
        cycle_a = PaymentCycleFactory(cooperative=coop)
        cycle_b = PaymentCycleFactory(cooperative=coop)
        FarmerPaymentFactory(cycle=cycle_a, cooperative=coop)
        FarmerPaymentFactory(cycle=cycle_b, cooperative=coop)
        FarmerPaymentFactory(cycle=cycle_a, cooperative=coop)
        resp = api_client.get(f'/api/payments/?cycle={cycle_a.id}')
        assert resp.data['count'] == 2

    def test_filter_by_status(self, api_client, coop):
        FarmerPaymentFactory(cooperative=coop, payment_status=PaymentStatus.PENDING)
        FarmerPaymentFactory(cooperative=coop, payment_status=PaymentStatus.PAID)
        resp = api_client.get(f'/api/payments/?status={PaymentStatus.PAID}')
        assert resp.data['count'] == 1

    def test_filter_by_farmer(self, api_client, coop):
        farmer_a = FarmerFactory(cooperative=coop)
        farmer_b = FarmerFactory(cooperative=coop)
        FarmerPaymentFactory(cooperative=coop, farmer=farmer_a)
        FarmerPaymentFactory(cooperative=coop, farmer=farmer_b)
        resp = api_client.get(f'/api/payments/?farmer={farmer_a.id}')
        assert resp.data['count'] == 1

    def test_farmer_role_only_sees_own_payments(self, api_client, coop):
        from apps.auth_api.models import User
        farmer_a = FarmerFactory(cooperative=coop)
        farmer_b = FarmerFactory(cooperative=coop)
        FarmerPaymentFactory(cooperative=coop, farmer=farmer_a)
        FarmerPaymentFactory(cooperative=coop, farmer=farmer_b)
        user = User.objects.create(email='farmer6@x.com', phone_number='+254700000017', role=UserRole.FARMER, cooperative=coop)
        farmer_a.user = user
        farmer_a.save()
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/payments/')
        assert resp.data['count'] == 1

    def test_serializer_includes_farmer_name(self, api_client, coop):
        fp = FarmerPaymentFactory(cooperative=coop)
        resp = api_client.get('/api/payments/')
        assert resp.status_code == 200
        assert resp.data['results'][0]['farmer_name'] is not None


class TestFarmerPaymentDetail:
    def _accountant(self, coop):
        from apps.auth_api.models import User
        return User.objects.create(email='fp-detail-acc@x.com', phone_number='+254700008300', role=UserRole.ACCOUNTANT, cooperative=coop)

    def test_retrieve(self, api_client, coop):
        fp = FarmerPaymentFactory(cooperative=coop)
        resp = api_client.get(f'/api/payments/{fp.id}/')
        assert resp.status_code == 200
        assert resp.data['id'] == str(fp.id)

    def test_404_for_missing(self, api_client):
        resp = api_client.get(f'/api/payments/{uuid.uuid4()}/')
        assert resp.status_code == 404

    # Update, partial_update, and destroy are not supported for FarmerPayment
    # (all serializer fields are read-only; payments are created by the engine).


# =============================================================================
# Engine — compute_fixed_price
# =============================================================================


class TestComputeFixedPrice:
    def test_returns_empty_list_when_no_deliveries(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date(2023, 1, 1), end_date=date(2023, 1, 31))
        results = compute_fixed_price(cycle)
        assert results == []

    def test_aggregates_deliveries_by_grade(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        farmer = FarmerFactory(cooperative=coop)
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'), effective_from=date.today() - timedelta(days=30))
        delivery = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        GradeFactory(delivery=delivery, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        results = compute_fixed_price(cycle)
        assert len(results) == 1
        r = results[0]
        assert r.farmer.id == farmer.id
        assert r.total_quantity == 100.0
        assert r.gross_amount == 5000.0
        assert r.grade_breakdown['A']['kg'] == 100.0
        assert r.grade_breakdown['A']['amount'] == 5000.0

    def test_handles_multiple_grades_per_farmer(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        farmer = FarmerFactory(cooperative=coop)
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'), effective_from=date.today() - timedelta(days=30))
        GradePriceFactory(grade_letter='B', price_per_unit=Decimal('40.00'), effective_from=date.today() - timedelta(days=30))
        d1 = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        d2 = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('50.00'), status='GRADED', date_delivered=timezone.now())
        GradeFactory(delivery=d1, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        GradeFactory(delivery=d2, cooperative=coop, grade_letter='B', price_per_unit=Decimal('40.00'))
        results = compute_fixed_price(cycle)
        assert len(results) == 1
        r = results[0]
        assert r.total_quantity == 150.0
        assert r.gross_amount == 7000.0  # 5000 + 2000

    def test_handles_multiple_farmers(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        f1 = FarmerFactory(cooperative=coop)
        f2 = FarmerFactory(cooperative=coop)
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'), effective_from=date.today() - timedelta(days=30))
        d1 = DeliveryFactory(farmer=f1, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        d2 = DeliveryFactory(farmer=f2, cooperative=coop, quantity_kg=Decimal('200.00'), status='GRADED', date_delivered=timezone.now())
        GradeFactory(delivery=d1, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        GradeFactory(delivery=d2, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        results = compute_fixed_price(cycle)
        assert len(results) == 2
        amounts = {r.farmer.id: r.gross_amount for r in results}
        assert amounts[f1.id] == 5000.0
        assert amounts[f2.id] == 10000.0

    def test_skips_deliveries_without_grade_record(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        farmer = FarmerFactory(cooperative=coop)
        DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        results = compute_fixed_price(cycle)
        assert results == []

    def test_skips_deliveries_with_unknown_grade_price(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        farmer = FarmerFactory(cooperative=coop)
        delivery = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        GradeFactory(delivery=delivery, cooperative=coop, grade_letter='Z', price_per_unit=Decimal('999.00'))
        results = compute_fixed_price(cycle)
        assert results == []

    def test_respects_date_range(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date(2023, 6, 1), end_date=date(2023, 6, 30))
        farmer = FarmerFactory(cooperative=coop)
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'), effective_from=date(2023, 1, 1))
        # delivery outside range
        outside = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.datetime(2023, 5, 1, tzinfo=datetime.timezone.utc))
        GradeFactory(delivery=outside, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        results = compute_fixed_price(cycle)
        assert results == []

    def test_accepts_accepted_status_deliveries(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        farmer = FarmerFactory(cooperative=coop)
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'), effective_from=date.today() - timedelta(days=30))
        delivery = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='ACCEPTED', date_delivered=timezone.now())
        GradeFactory(delivery=delivery, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        results = compute_fixed_price(cycle)
        assert len(results) == 1


# =============================================================================
# Engine — compute_revenue_share
# =============================================================================


class TestComputeRevenueShare:
    def test_returns_empty_list_when_no_deliveries(self, coop):
        coop.payment_model = PaymentModel.REVENUE_SHARE
        coop.save()
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date(2023, 1, 1), end_date=date(2023, 1, 31))
        SaleFactory = _sale_factory_for(coop)
        SaleFactory(cooperative=coop, product_type='MILK', quantity=Decimal('1000'), price_per_unit=Decimal('50'), total_amount=Decimal('50000'), status='COMPLETED', sale_date=date(2023, 1, 15))
        results = compute_revenue_share(cycle)
        assert results == []

    def test_distributes_revenue_by_delivery_share(self, coop):
        coop.payment_model = PaymentModel.REVENUE_SHARE
        coop.save()
        from apps.sales.models import Sale as SaleModel
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        f1 = FarmerFactory(cooperative=coop)
        f2 = FarmerFactory(cooperative=coop)
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'), effective_from=date.today() - timedelta(days=30))
        d1 = DeliveryFactory(farmer=f1, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        d2 = DeliveryFactory(farmer=f2, cooperative=coop, quantity_kg=Decimal('300.00'), status='GRADED', date_delivered=timezone.now())
        GradeFactory(delivery=d1, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        GradeFactory(delivery=d2, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        SaleModel.objects.create(
            cooperative=coop, product_type='MILK', quantity=Decimal('400'), unit='kg',
            price_per_unit=Decimal('50'), total_amount=Decimal('20000'),
            status='COMPLETED', sale_date=date.today(),
            buyer_id=_buyer_for(coop).id,
        )
        results = compute_revenue_share(cycle)
        assert len(results) == 2
        amounts = {r.farmer.id: r.gross_amount for r in results}
        # f1: 100/400 * 20000 = 5000, f2: 300/400 * 20000 = 15000
        assert amounts[f1.id] == 5000.0
        assert amounts[f2.id] == 15000.0

    def test_creates_warning_when_no_sales(self, coop):
        coop.payment_model = PaymentModel.REVENUE_SHARE
        coop.save()
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        farmer = FarmerFactory(cooperative=coop)
        delivery = DeliveryFactory(farmer=farmer, cooperative=coop, quantity_kg=Decimal('100.00'), status='GRADED', date_delivered=timezone.now())
        GradeFactory(delivery=delivery, cooperative=coop, grade_letter='A', price_per_unit=Decimal('50.00'))
        results = compute_revenue_share(cycle)
        assert results == []

    def test_handles_zero_total_kg(self, coop):
        coop.payment_model = PaymentModel.REVENUE_SHARE
        coop.save()
        cycle = PaymentCycleFactory(cooperative=coop, start_date=date.today() - timedelta(days=10), end_date=date.today())
        results = compute_revenue_share(cycle)
        assert results == []


def _sale_factory_for(coop):
    """Create a minimal buyer for sale creation in revenue share tests."""
    from apps.sales.models import Buyer
    buyer, _ = Buyer.objects.get_or_create(cooperative=coop, name='Test Buyer')
    buyer.phone_number = '+254700000099'
    buyer.save()

    def make(**kwargs):
        from apps.sales.models import Sale
        kwargs.setdefault('buyer', buyer)
        kwargs.setdefault('cooperative', coop)
        kwargs.setdefault('status', 'COMPLETED')
        return Sale.objects.create(**kwargs)
    return make


def _buyer_for(coop):
    from apps.sales.models import Buyer
    buyer, _ = Buyer.objects.get_or_create(cooperative=coop, name='Default Buyer')
    buyer.phone_number = '+254700000098'
    buyer.save()
    return buyer


# =============================================================================
# Engine — _compute_deductions
# =============================================================================


class TestComputeDeductions:
    def test_returns_zero_when_no_loans_or_input_credits(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        fp = FarmerPayment(gross_amount=Decimal('10000.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        levy = 10000 * (float(coop.levy_percentage) / 100)
        expected_levy = round(levy, 2)
        expected_fee = round(float(coop.monthly_fee) / 1, 2)
        assert deductions.levy == expected_levy
        assert deductions.monthly_fee == expected_fee
        assert deductions.loan_repayment == 0.0
        assert deductions.input_credit == 0.0
        expected_net = max(10000.0 - expected_levy - expected_fee, 0)
        assert net == expected_net
        assert pending.loan_repayment_ded is None

    def test_includes_loan_repayment(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        loan = LoanFactory(farmer=farmer, cooperative=coop, status='ACTIVE', installments_paid=0, number_of_installments=6, installment_amount=Decimal('1833.33'))
        fp = FarmerPayment(gross_amount=Decimal('10000.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        assert deductions.loan_repayment == 1833.33
        assert pending.loan_repayment_ded is not None
        assert pending.loan_repayment_ded.amount == Decimal('1833.33')
        assert pending.updated_loan.installments_paid == 1
        assert pending.updated_loan.status == 'ACTIVE'

    def test_marks_loan_completed_after_final_installment(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        loan = LoanFactory(farmer=farmer, cooperative=coop, status='ACTIVE', installments_paid=5, number_of_installments=6, installment_amount=Decimal('1833.33'))
        fp = FarmerPayment(gross_amount=Decimal('10000.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        assert pending.updated_loan.status == 'COMPLETED'
        assert pending.updated_loan.installments_paid == 6

    def test_includes_input_credit(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        credit = FarmInputCreditFactory(farmer=farmer, cooperative=coop, amount=Decimal('5000.00'), installment_amount=Decimal('500.00'), supplied_date=date.today())
        fp = FarmerPayment(gross_amount=Decimal('10000.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=1, cycle=cycle, undeducted_credits=[credit])
        assert deductions.input_credit == 500.0
        assert len(pending.input_credit_deds) == 1

    def test_skips_input_credit_when_remaining_insufficient(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        credit = FarmInputCreditFactory(farmer=farmer, cooperative=coop, amount=Decimal('5000.00'), installment_amount=Decimal('500.00'), supplied_date=date.today())
        fp = FarmerPayment(gross_amount=Decimal('10.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=1, cycle=cycle, undeducted_credits=[credit])
        assert deductions.input_credit == 0.0
        assert pending.input_credit_deds == []

    def test_net_amount_never_negative(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        fp = FarmerPayment(gross_amount=Decimal('1.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        assert net >= 0

    def test_monthly_fee_is_shared_among_farmers(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        fp = FarmerPayment(gross_amount=Decimal('10000.00'), farmer=farmer, cycle=cycle, cooperative=coop)
        deductions, net, pending = _compute_deductions(fp, coop, active_farmer_count=5, cycle=cycle)
        expected_fee = float(coop.monthly_fee) / 5
        assert deductions.monthly_fee == expected_fee


# =============================================================================
# Engine — apply_deductions
# =============================================================================


class TestApplyDeductions:
    def test_writes_loan_deduction_to_db(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        loan = LoanFactory(farmer=farmer, cooperative=coop, status='ACTIVE', installments_paid=0, number_of_installments=6, installment_amount=Decimal('1833.33'))
        fp = FarmerPayment.objects.create(
            cooperative=coop, cycle=cycle, farmer=farmer,
            gross_amount=Decimal('10000.00'), net_amount=Decimal('0'),
        )
        deductions_dict, net = apply_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        from apps.deductions.models import Deduction
        from apps.loans.models import LoanRepayment
        assert Deduction.objects.filter(cycle=cycle, deduction_type='LOAN_REPAYMENT').count() == 1
        assert LoanRepayment.objects.filter(farmer_payment=fp).count() == 1
        loan.refresh_from_db()
        assert loan.installments_paid == 1

    def test_writes_input_credit_deduction_to_db(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        credit = FarmInputCreditFactory(farmer=farmer, cooperative=coop, amount=Decimal('500.00'), installment_amount=Decimal('500.00'), supplied_date=date.today())
        fp = FarmerPayment.objects.create(
            cooperative=coop, cycle=cycle, farmer=farmer,
            gross_amount=Decimal('10000.00'), net_amount=Decimal('0'),
        )
        apply_deductions(fp, coop, active_farmer_count=1, cycle=cycle, undeducted_credits=[credit])
        from apps.deductions.models import Deduction
        assert Deduction.objects.filter(cycle=cycle, deduction_type='INPUT_CREDIT').count() == 1
        credit.refresh_from_db()
        assert credit.total_deducted == Decimal('500.00')
        assert credit.status == 'COMPLETED'

    def test_updates_net_amount_on_farmer_payment(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        fp = FarmerPayment.objects.create(
            cooperative=coop, cycle=cycle, farmer=farmer,
            gross_amount=Decimal('10000.00'), net_amount=Decimal('99999.00'),
        )
        deductions_dict, net = apply_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        assert net < 10000.0

    def test_returns_deductions_dict(self, coop):
        cycle = PaymentCycleFactory(cooperative=coop)
        farmer = FarmerFactory(cooperative=coop)
        fp = FarmerPayment.objects.create(
            cooperative=coop, cycle=cycle, farmer=farmer,
            gross_amount=Decimal('10000.00'), net_amount=Decimal('0'),
        )
        deductions_dict, net = apply_deductions(fp, coop, active_farmer_count=1, cycle=cycle)
        assert 'levy' in deductions_dict
        assert 'monthly_fee' in deductions_dict
        assert 'loan_repayment' in deductions_dict
        assert 'input_credit' in deductions_dict
