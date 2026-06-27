from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.conftest import (
    CooperativeFactory,
    DisbursementBatchFactory,
    DisbursementTransactionFactory,
    FarmerFactory,
    FarmerPaymentFactory,
    PaymentCycleFactory,
    UserFactory,
)
from apps.disbursement.models import (
    BatchStatus,
    CommandId,
    DisbursementBatch,
    DisbursementPaymentMethod,
    DisbursementTransaction,
    TransactionStatus,
)
from apps.disbursement.tasks import update_batch_summary
from apps.payment_engine.models import CycleStatus, FarmerPayment, PaymentCycle

pytestmark = pytest.mark.django_db


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def accountant_user(cooperative):
    user = UserFactory(
        role=UserRole.ACCOUNTANT,
        cooperative=cooperative,
    )
    user.raw_password = 'testpass123'
    return user


@pytest.fixture
def manager_user(cooperative):
    user = UserFactory(
        role=UserRole.MANAGER,
        cooperative=cooperative,
    )
    user.raw_password = 'testpass123'
    return user


@pytest.fixture
def farmer_role_user(cooperative):
    user = UserFactory(
        role=UserRole.FARMER,
        cooperative=cooperative,
    )
    user.raw_password = 'testpass123'
    return user


@pytest.fixture
def locked_payment_cycle(cooperative):
    cycle = PaymentCycleFactory(
        cooperative=cooperative,
        status=CycleStatus.LOCKED,
    )
    return cycle


@pytest.fixture
def locked_payment_cycle_with_payments(locked_payment_cycle, farmer):
    FarmerPaymentFactory(
        cycle=locked_payment_cycle,
        farmer=farmer,
        cooperative=locked_payment_cycle.cooperative,
        net_amount=Decimal('4300.00'),
    )
    return locked_payment_cycle


@pytest.fixture
def api_client_coop(db, cooperative):
    client = APIClient()
    user = UserFactory(role=UserRole.ACCOUNTANT, cooperative=cooperative)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def client():
    return APIClient()


# =============================================================================
# DisbursementBatch Model Tests
# =============================================================================

class TestDisbursementBatchModel:
    def test_create(self, cooperative):
        batch = DisbursementBatch.objects.create(cooperative=cooperative)
        assert batch.pk is not None
        assert batch.status == BatchStatus.PENDING

    def test_str(self, cooperative):
        batch = DisbursementBatch.objects.create(cooperative=cooperative)
        assert 'Batch' in str(batch)
        assert 'Pending' in str(batch)

    def test_default_command_id(self, cooperative):
        batch = DisbursementBatch.objects.create(cooperative=cooperative)
        assert batch.command_id == CommandId.SALARY_PAYMENT

    def test_status_transitions(self, cooperative):
        batch = DisbursementBatch.objects.create(cooperative=cooperative)
        for status in [BatchStatus.PROCESSING, BatchStatus.COMPLETED,
                       BatchStatus.PARTIALLY_COMPLETED, BatchStatus.FAILED]:
            batch.status = status
            batch.save()
            batch.refresh_from_db()
            assert batch.status == status

    def test_counts_default(self, cooperative):
        batch = DisbursementBatch.objects.create(cooperative=cooperative)
        assert batch.total_amount == 0
        assert batch.total_transactions == 0
        assert batch.successful_count == 0
        assert batch.failed_count == 0

    def test_approval_tracking(self, cooperative, superuser):
        now = timezone.now()
        batch = DisbursementBatch.objects.create(
            cooperative=cooperative,
            approved_by=superuser,
            approved_at=now,
            status=BatchStatus.PROCESSING,
        )
        assert batch.approved_by == superuser
        assert batch.approved_at == now

    def test_soft_delete(self, cooperative):
        batch = DisbursementBatch.objects.create(cooperative=cooperative)
        batch.soft_delete()
        assert batch.deleted_at is not None

    def test_ordering(self, cooperative):
        b1 = DisbursementBatch.objects.create(cooperative=cooperative)
        b2 = DisbursementBatch.objects.create(cooperative=cooperative)
        qs = DisbursementBatch.objects.all()
        assert list(qs) == [b2, b1]


# =============================================================================
# DisbursementTransaction Model Tests
# =============================================================================

class TestDisbursementTransactionModel:
    def test_create(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('4300.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='+254700000001',
        )
        assert tx.pk is not None
        assert tx.status == TransactionStatus.PENDING

    def test_str(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('4300.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='+254700000001',
        )
        assert '4300.00' in str(tx)
        assert 'Pending' in str(tx)

    def test_payment_methods(self, disbursement_batch, farmer):
        for i, method in enumerate([DisbursementPaymentMethod.M_PESA,
                                    DisbursementPaymentMethod.BANK,
                                    DisbursementPaymentMethod.CASH]):
            tx = DisbursementTransaction.objects.create(
                batch=disbursement_batch,
                farmer=farmer,
                cooperative=disbursement_batch.cooperative,
                amount=Decimal('1000.00'),
                payment_method=method,
                recipient_identifier='test',
                transaction_id=f'TXNPM{i}',
                conversation_id=f'CONVPM{i}',
            )
            assert tx.payment_method == method

    def test_status_transitions(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('1000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='+254700000001',
        )
        for status in [TransactionStatus.QUEUED, TransactionStatus.SENT,
                       TransactionStatus.SUCCESS, TransactionStatus.FAILED,
                       TransactionStatus.CANCELLED]:
            tx.status = status
            tx.save()
            tx.refresh_from_db()
            assert tx.status == status

    def test_mpesa_fields(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('4300.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='+254700000001',
            transaction_id='TXN001',
            conversation_id='CONV001',
            originator_conversation_id='ORIG001',
            result_code='0',
            result_desc='Success',
        )
        assert tx.transaction_id == 'TXN001'
        assert tx.conversation_id == 'CONV001'

    def test_retry_count(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('1000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='test',
        )
        assert tx.retry_count == 0
        tx.retry_count = 3
        tx.save()
        tx.refresh_from_db()
        assert tx.retry_count == 3

    def test_withholding_tax(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('5000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='test',
            withholding_tax_amount=Decimal('500.00'),
        )
        assert tx.withholding_tax_amount == Decimal('500.00')

    def test_soft_delete(self, disbursement_batch, farmer):
        tx = DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('1000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='test',
        )
        tx.soft_delete()
        assert tx.deleted_at is not None

    def test_unique_together_conversation_transaction(self, disbursement_batch, farmer):
        DisbursementTransaction.objects.create(
            batch=disbursement_batch,
            farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            amount=Decimal('1000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            recipient_identifier='test',
            conversation_id='CONV',
            transaction_id='TXN',
        )
        with pytest.raises(Exception):
            DisbursementTransaction.objects.create(
                batch=disbursement_batch,
                farmer=farmer,
                cooperative=disbursement_batch.cooperative,
                amount=Decimal('2000.00'),
                payment_method=DisbursementPaymentMethod.M_PESA,
                recipient_identifier='test2',
                conversation_id='CONV',
                transaction_id='TXN',
            )


# =============================================================================
# Authentication & Permission Tests
# =============================================================================

class TestDisbursementAPIAuth:
    """Unauthenticated requests should return 401 on all endpoints."""

    def test_list_unauthenticated(self, client):
        resp = client.get('/api/disbursements/')
        assert resp.status_code == 401

    def test_create_unauthenticated(self, client):
        resp = client.post('/api/disbursements/', {})
        assert resp.status_code == 401

    def test_retrieve_unauthenticated(self, client, disbursement_batch):
        resp = client.get(f'/api/disbursements/{disbursement_batch.pk}/')
        assert resp.status_code == 401

    def test_update_unauthenticated(self, client, disbursement_batch):
        resp = client.put(f'/api/disbursements/{disbursement_batch.pk}/', {})
        assert resp.status_code == 401

    def test_partial_update_unauthenticated(self, client, disbursement_batch):
        resp = client.patch(f'/api/disbursements/{disbursement_batch.pk}/', {})
        assert resp.status_code == 401

    def test_destroy_unauthenticated(self, client, disbursement_batch):
        resp = client.delete(f'/api/disbursements/{disbursement_batch.pk}/')
        assert resp.status_code == 401

    def test_initiate_unauthenticated(self, client):
        resp = client.post('/api/disbursements/initiate/', {})
        assert resp.status_code == 401

    def test_approve_unauthenticated(self, client, disbursement_batch):
        resp = client.post(f'/api/disbursements/{disbursement_batch.pk}/approve/')
        assert resp.status_code == 401

    def test_live_unauthenticated(self, client, disbursement_batch):
        resp = client.post(f'/api/disbursements/{disbursement_batch.pk}/live/')
        assert resp.status_code == 401

    def test_retry_failed_unauthenticated(self, client, disbursement_batch):
        resp = client.post(f'/api/disbursements/{disbursement_batch.pk}/retry_failed/')
        assert resp.status_code == 401

    def test_csv_unauthenticated(self, client, disbursement_batch):
        resp = client.get(f'/api/disbursements/{disbursement_batch.pk}/csv/')
        assert resp.status_code == 401

    def test_confirm_manual_unauthenticated(self, client, disbursement_batch):
        resp = client.post(f'/api/disbursements/{disbursement_batch.pk}/confirm_manual/', {})
        assert resp.status_code == 401

    def test_transactions_unauthenticated(self, client, disbursement_batch):
        resp = client.get(f'/api/disbursements/{disbursement_batch.pk}/transactions/')
        assert resp.status_code == 401


class TestDisbursementAPIPermissions:
    """Wrong roles should get 403 for accountant-or-manager actions."""

    def test_farmer_cannot_create(self, api_client_coop, farmer_role_user, cooperative):
        """create requires IsAccountantOrManager."""
        api_client_coop.force_authenticate(user=farmer_role_user)
        resp = api_client_coop.post('/api/disbursements/', {})
        assert resp.status_code == 403

    def test_farmer_cannot_initiate(self, api_client_coop, farmer_role_user, cooperative):
        api_client_coop.force_authenticate(user=farmer_role_user)
        resp = api_client_coop.post('/api/disbursements/initiate/', {})
        assert resp.status_code == 403

    def test_farmer_cannot_live(self, api_client_coop, farmer_role_user, cooperative):
        api_client_coop.force_authenticate(user=farmer_role_user)
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/live/')
        assert resp.status_code == 403

    def test_farmer_cannot_retry_failed(self, api_client_coop, farmer_role_user, cooperative):
        api_client_coop.force_authenticate(user=farmer_role_user)
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/retry_failed/')
        assert resp.status_code == 403

    def test_farmer_cannot_csv(self, api_client_coop, farmer_role_user, cooperative):
        api_client_coop.force_authenticate(user=farmer_role_user)
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.get(f'/api/disbursements/{batch.pk}/csv/')
        assert resp.status_code == 403

    def test_farmer_cannot_confirm_manual(self, api_client_coop, farmer_role_user, cooperative):
        api_client_coop.force_authenticate(user=farmer_role_user)
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/confirm_manual/', {})
        assert resp.status_code == 403

    def test_accountant_cannot_approve(self, api_client_coop, accountant_user, cooperative):
        """approve requires MANAGER role, not ACCOUNTANT."""
        api_client_coop.force_authenticate(user=accountant_user)
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/approve/')
        assert resp.status_code == 403

    def test_manager_can_approve(self, api_client_coop, manager_user, cooperative):
        api_client_coop.force_authenticate(user=manager_user)
        batch = DisbursementBatchFactory(cooperative=cooperative, status='PENDING')
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/approve/')
        assert resp.status_code == 200

    def test_accountant_can_initiate(self, api_client_coop, accountant_user, locked_payment_cycle):
        api_client_coop.force_authenticate(user=accountant_user)
        resp = api_client_coop.post('/api/disbursements/initiate/', {
            'payment_cycle': str(locked_payment_cycle.pk),
        })
        assert resp.status_code == 201

    def test_farmer_can_list(self, api_client_coop, farmer_role_user):
        """list only requires IsAuthenticated, so farmer can access."""
        api_client_coop.force_authenticate(user=farmer_role_user)
        resp = api_client_coop.get('/api/disbursements/')
        assert resp.status_code == 200

    def test_farmer_can_retrieve(self, api_client_coop, farmer_role_user, cooperative):
        """retrieve only requires IsAuthenticated."""
        api_client_coop.force_authenticate(user=farmer_role_user)
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.get(f'/api/disbursements/{batch.pk}/')
        assert resp.status_code == 200

    def test_accountant_can_create(self, api_client_coop, accountant_user, cooperative):
        api_client_coop.force_authenticate(user=accountant_user)
        resp = api_client_coop.post('/api/disbursements/', {'notes': 'test'})
        assert resp.status_code == 201


# =============================================================================
# CRUD Tests
# =============================================================================

class TestDisbursementAPICRUD:
    def test_list_empty(self, api_client_coop):
        resp = api_client_coop.get('/api/disbursements/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 0
        assert data['results'] == []

    def test_list_with_batches(self, api_client_coop, cooperative):
        DisbursementBatchFactory.create_batch(3, cooperative=cooperative)
        resp = api_client_coop.get('/api/disbursements/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 3
        assert len(data['results']) == 3

    def test_create(self, api_client_coop, cooperative):
        data = {'notes': 'Test batch'}
        resp = api_client_coop.post('/api/disbursements/', data)
        assert resp.status_code == 201
        assert resp.json()['status'] == 'PENDING'
        assert resp.json()['notes'] == ''

    def test_retrieve(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.get(f'/api/disbursements/{batch.pk}/')
        assert resp.status_code == 200
        assert resp.json()['id'] == str(batch.pk)

    def test_update(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.put(
            f'/api/disbursements/{batch.pk}/',
            {'notes': 'Updated notes', 'command_id': 'BusinessPayment'},
        )
        assert resp.status_code == 200
        assert resp.json()['notes'] == 'Updated notes'

    def test_partial_update(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.patch(
            f'/api/disbursements/{batch.pk}/',
            {'notes': 'Patched'},
        )
        assert resp.status_code == 200
        assert resp.json()['notes'] == 'Patched'

    def test_destroy_pending_allowed(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative, status='PENDING')
        resp = api_client_coop.delete(f'/api/disbursements/{batch.pk}/')
        assert resp.status_code == 204

    def test_destroy_failed_allowed(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative, status='FAILED')
        resp = api_client_coop.delete(f'/api/disbursements/{batch.pk}/')
        assert resp.status_code == 204

    def test_destroy_processing_rejected(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative, status='PROCESSING')
        resp = api_client_coop.delete(f'/api/disbursements/{batch.pk}/')
        assert resp.status_code == 400
        assert 'Only PENDING or FAILED' in resp.json()['detail'][0]

    def test_destroy_completed_rejected(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative, status='COMPLETED')
        resp = api_client_coop.delete(f'/api/disbursements/{batch.pk}/')
        assert resp.status_code == 400
        assert 'Only PENDING or FAILED' in resp.json()['detail'][0]


# =============================================================================
# Initiate Action Tests
# =============================================================================

class TestDisbursementAPIInitiate:
    def test_initiate_success(self, api_client_coop, locked_payment_cycle_with_payments):
        cycle = locked_payment_cycle_with_payments
        resp = api_client_coop.post('/api/disbursements/initiate/', {
            'payment_cycle': str(cycle.pk),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data['status'] == 'PENDING'
        assert data['payment_cycle'] == str(cycle.pk)
        assert data['total_transactions'] >= 1
        assert data['total_amount'] > 0

    def test_initiate_creates_transactions(self, api_client_coop, locked_payment_cycle_with_payments):
        cycle = locked_payment_cycle_with_payments
        resp = api_client_coop.post('/api/disbursements/initiate/', {
            'payment_cycle': str(cycle.pk),
        })
        assert resp.status_code == 201
        batch = DisbursementBatch.objects.get(pk=resp.json()['id'])
        assert batch.transactions.count() >= 1

    def test_initiate_rejects_non_locked_cycle(self, api_client_coop, cooperative):
        cycle = PaymentCycleFactory(cooperative=cooperative)
        resp = api_client_coop.post('/api/disbursements/initiate/', {
            'payment_cycle': str(cycle.pk),
        })
        assert resp.status_code == 400
        assert 'LOCKED' in resp.json()['payment_cycle'][0]

    def test_initiate_rejects_missing_cycle(self, api_client_coop):
        resp = api_client_coop.post('/api/disbursements/initiate/', {
            'payment_cycle': '00000000-0000-0000-0000-000000000000',
        })
        assert resp.status_code == 400
        assert 'not found' in resp.json()['payment_cycle'][0]

    def test_initiate_with_notes(self, api_client_coop, locked_payment_cycle_with_payments):
        resp = api_client_coop.post('/api/disbursements/initiate/', {
            'payment_cycle': str(locked_payment_cycle_with_payments.pk),
            'notes': 'Test disbursement',
        })
        assert resp.status_code == 201
        assert resp.json()['notes'] == 'Test disbursement'


# =============================================================================
# Approve Action Tests
# =============================================================================

class TestDisbursementAPIApprove:
    def test_approve_success(self, api_client_coop, manager_user, cooperative):
        api_client_coop.force_authenticate(user=manager_user)
        batch = DisbursementBatchFactory(cooperative=cooperative, status='PENDING')
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/approve/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'PROCESSING'
        batch.refresh_from_db()
        assert batch.approved_by == manager_user
        assert batch.approved_at is not None

    def test_approve_rejects_non_pending(self, api_client_coop, manager_user, cooperative):
        api_client_coop.force_authenticate(user=manager_user)
        batch = DisbursementBatchFactory(cooperative=cooperative, status='PROCESSING')
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/approve/')
        assert resp.status_code == 400
        assert 'Only PENDING' in resp.json()['detail']

    def test_approve_rejects_completed(self, api_client_coop, manager_user, cooperative):
        api_client_coop.force_authenticate(user=manager_user)
        batch = DisbursementBatchFactory(cooperative=cooperative, status='COMPLETED')
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/approve/')
        assert resp.status_code == 400

    def test_approve_rejects_failed(self, api_client_coop, manager_user, cooperative):
        api_client_coop.force_authenticate(user=manager_user)
        batch = DisbursementBatchFactory(cooperative=cooperative, status='FAILED')
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/approve/')
        assert resp.status_code == 400


# =============================================================================
# Live Action Tests
# =============================================================================

class TestDisbursementAPILive:
    @patch('apps.disbursement.views.process_batch_disbursements.delay')
    def test_live_success(self, mock_delay, api_client_coop, cooperative):
        mock_delay.return_value.id = 'mock-task-id'
        batch = DisbursementBatchFactory(
            cooperative=cooperative,
            status='PROCESSING',
            approved_by=UserFactory(),
        )
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/live/')
        assert resp.status_code == 200
        assert resp.json()['task_id'] == 'mock-task-id'
        assert resp.json()['status'] == 'processing'
        mock_delay.assert_called_once_with(str(batch.pk))

    @patch('apps.disbursement.views.process_batch_disbursements.delay')
    def test_live_rejects_non_processing(self, mock_delay, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(
            cooperative=cooperative,
            status='PENDING',
            approved_by=UserFactory(),
        )
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/live/')
        assert resp.status_code == 400
        assert 'PROCESSING' in resp.json()['detail']
        mock_delay.assert_not_called()

    @patch('apps.disbursement.views.process_batch_disbursements.delay')
    def test_live_rejects_unapproved(self, mock_delay, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(
            cooperative=cooperative,
            status='PROCESSING',
            approved_by=None,
        )
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/live/')
        assert resp.status_code == 400
        assert 'approved' in resp.json()['detail']
        mock_delay.assert_not_called()

    @patch('apps.disbursement.views.process_batch_disbursements.delay')
    def test_live_rejects_completed(self, mock_delay, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(
            cooperative=cooperative,
            status='COMPLETED',
            approved_by=UserFactory(),
        )
        resp = api_client_coop.post(f'/api/disbursements/{batch.pk}/live/')
        assert resp.status_code == 400
        mock_delay.assert_not_called()

    @patch('apps.disbursement.views.process_batch_disbursements.delay')
    def test_live_saves_celery_task_id(self, mock_delay, api_client_coop, cooperative):
        mock_delay.return_value.id = 'celery-task-456'
        batch = DisbursementBatchFactory(
            cooperative=cooperative,
            status='PROCESSING',
            approved_by=UserFactory(),
        )
        api_client_coop.post(f'/api/disbursements/{batch.pk}/live/')
        batch.refresh_from_db()
        assert batch.celery_task_id == 'celery-task-456'


# =============================================================================
# Retry Failed Action Tests
# =============================================================================

class TestDisbursementAPIRetryFailed:
    def test_retry_failed_success(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='FAILED',
            failure_reason='Timeout',
            result_code='1037',
            result_desc='Request cancelled',
            retry_count=2,
            failed_at=timezone.now(),
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/retry_failed/',
        )
        assert resp.status_code == 200
        assert resp.json()['retried'] == 1
        assert resp.json()['status'] == 'PENDING'
        tx.refresh_from_db()
        assert tx.status == 'PENDING'
        assert tx.failure_reason == ''
        assert tx.retry_count == 0

    def test_retry_failed_no_failed(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/retry_failed/',
        )
        assert resp.status_code == 400
        assert 'No failed transactions' in resp.json()['detail']

    def test_retry_failed_multiple(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        DisbursementTransactionFactory.create_batch(
            3, batch=batch, farmer=farmer, cooperative=cooperative,
            status='FAILED',
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/retry_failed/',
        )
        assert resp.status_code == 200
        assert resp.json()['retried'] == 3

    def test_retry_failed_ignores_non_failed(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='SUCCESS',
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/retry_failed/',
        )
        assert resp.status_code == 400


# =============================================================================
# CSV Action Tests
# =============================================================================

class TestDisbursementAPICSV:
    def test_csv_with_bank_txns(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='BANK', status='PENDING',
            recipient_identifier='1234567890',
            recipient_name='John Doe',
            amount=Decimal('5000.00'),
        )
        resp = api_client_coop.get(f'/api/disbursements/{batch.pk}/csv/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv'
        assert 'AccountNumber' in resp.content.decode()
        assert '1234567890' in resp.content.decode()

    def test_csv_no_bank_txns(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.get(
            f'/api/disbursements/{batch.pk}/csv/',
        )
        assert resp.status_code == 400
        assert 'No pending bank transactions' in resp.json()['detail']

    def test_csv_ignores_mpesa_txns(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='M_PESA', status='PENDING',
        )
        resp = api_client_coop.get(f'/api/disbursements/{batch.pk}/csv/')
        assert resp.status_code == 400

    def test_csv_content_disposition(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='BANK', status='PENDING',
            recipient_identifier='1234567890',
            recipient_name='Jane Doe',
            amount=Decimal('3000.00'),
        )
        resp = api_client_coop.get(f'/api/disbursements/{batch.pk}/csv/')
        assert resp.status_code == 200
        assert 'attachment; filename=' in resp['Content-Disposition']
        assert '.csv' in resp['Content-Disposition']


# =============================================================================
# Confirm Manual Action Tests
# =============================================================================

class TestDisbursementAPIConfirmManual:
    def test_confirm_manual_bank_success(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        fp = FarmerPaymentFactory(
            cycle=PaymentCycleFactory(cooperative=cooperative),
            farmer=farmer, cooperative=cooperative,
        )
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='BANK', status='PENDING',
            farmer_payment=fp,
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/confirm_manual/',
            {'transaction_ids': [str(tx.pk)]},
        )
        assert resp.status_code == 200
        assert resp.json()['confirmed'] == 1
        assert resp.json()['status'] == 'SUCCESS'
        tx.refresh_from_db()
        assert tx.status == 'SUCCESS'
        assert tx.completed_at is not None

    def test_confirm_manual_cash_success(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='CASH', status='PENDING',
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/confirm_manual/',
            {'transaction_ids': [str(tx.pk)]},
        )
        assert resp.status_code == 200
        assert resp.json()['confirmed'] == 1

    def test_confirm_manual_rejects_mpesa(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='M_PESA', status='PENDING',
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/confirm_manual/',
            {'transaction_ids': [str(tx.pk)]},
        )
        assert resp.status_code == 400
        assert 'No matching BANK/CASH' in resp.json()['detail']

    def test_confirm_manual_empty_ids(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/confirm_manual/',
            {'transaction_ids': []},
        )
        assert resp.status_code == 400

    def test_confirm_manual_with_notes(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='BANK', status='PENDING',
        )
        resp = api_client_coop.post(
            f'/api/disbursements/{batch.pk}/confirm_manual/',
            {'transaction_ids': [str(tx.pk)], 'notes': 'Paid in cash'},
        )
        assert resp.status_code == 200
        tx.refresh_from_db()
        assert tx.failure_reason == 'Paid in cash'

    def test_confirm_manual_updates_farmer_payment_paid(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        farmer = FarmerFactory(cooperative=cooperative)
        fp = FarmerPaymentFactory(
            cycle=PaymentCycleFactory(cooperative=cooperative),
            farmer=farmer, cooperative=cooperative,
            payment_status='PENDING',
        )
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='BANK', status='PENDING',
            farmer_payment=fp,
        )
        api_client_coop.post(
            f'/api/disbursements/{batch.pk}/confirm_manual/',
            {'transaction_ids': [str(tx.pk)]},
        )
        fp.refresh_from_db()
        assert fp.payment_status == 'PAID'


# =============================================================================
# Transactions Action Tests
# =============================================================================

class TestDisbursementAPITransactions:
    def test_transactions_empty(self, api_client_coop, cooperative):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        resp = api_client_coop.get(
            f'/api/disbursements/{batch.pk}/transactions/',
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data['results'] if 'results' in data else data
        assert items == []

    def test_transactions_list(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        DisbursementTransactionFactory.create_batch(
            2, batch=batch, farmer=farmer, cooperative=cooperative,
        )
        resp = api_client_coop.get(
            f'/api/disbursements/{batch.pk}/transactions/',
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data['results'] if 'results' in data else data
        assert len(items) == 2

    def test_transactions_filter_by_status(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='PENDING',
        )
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='SUCCESS',
        )
        resp = api_client_coop.get(
            f'/api/disbursements/{batch.pk}/transactions/',
            {'status': 'success'},
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data['results'] if 'results' in data else data
        assert len(items) == 1
        assert items[0]['status'] == 'SUCCESS'

    def test_transactions_filter_by_payment_method(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='M_PESA',
        )
        DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            payment_method='BANK',
        )
        resp = api_client_coop.get(
            f'/api/disbursements/{batch.pk}/transactions/',
            {'payment_method': 'bank'},
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data['results'] if 'results' in data else data
        assert len(items) == 1

    def test_transactions_includes_farmer_details(self, api_client_coop, cooperative, farmer):
        batch = DisbursementBatchFactory(cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=disbursement_batch, farmer=farmer,
            cooperative=disbursement_batch.cooperative,
        )
        resp = api_client_coop.get(
            f'/api/disbursements/{disbursement_batch.pk}/transactions/',
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data['results'] if 'results' in data else data
        assert items[0]['farmer'] == str(farmer.pk)
        assert 'farmer_name' in items[0]


# =============================================================================
# Task Tests
# =============================================================================

class TestUpdateBatchSummaryTask:
    def test_update_completed(self, disbursement_batch, farmer):
        DisbursementTransactionFactory(
            batch=disbursement_batch, farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            status='SUCCESS',
        )
        update_batch_summary(str(disbursement_batch.pk))
        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == 'COMPLETED'
        assert disbursement_batch.successful_count == 1
        assert disbursement_batch.failed_count == 0

    def test_update_partially_completed(self, disbursement_batch, farmer):
        DisbursementTransactionFactory(
            batch=disbursement_batch, farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            status='SUCCESS',
        )
        DisbursementTransactionFactory(
            batch=disbursement_batch, farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            status='FAILED',
        )
        update_batch_summary(str(disbursement_batch.pk))
        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == 'PARTIALLY_COMPLETED'
        assert disbursement_batch.successful_count == 1
        assert disbursement_batch.failed_count == 1

    def test_update_failed(self, disbursement_batch, farmer):
        DisbursementTransactionFactory(
            batch=disbursement_batch, farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            status='FAILED',
        )
        update_batch_summary(str(disbursement_batch.pk))
        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == 'FAILED'
        assert disbursement_batch.successful_count == 0
        assert disbursement_batch.failed_count == 1

    def test_update_with_cancelled_only(self, disbursement_batch, farmer):
        DisbursementTransactionFactory(
            batch=disbursement_batch, farmer=farmer,
            cooperative=disbursement_batch.cooperative,
            status='CANCELLED',
        )
        update_batch_summary(str(disbursement_batch.pk))
        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == 'COMPLETED'

    def test_update_marks_cycle_disbursed(self, cooperative):
        cycle = PaymentCycleFactory(
            cooperative=cooperative,
            status=CycleStatus.LOCKED,
        )
        batch = DisbursementBatchFactory(cooperative=cooperative, payment_cycle=cycle)
        farmer = FarmerFactory(cooperative=cooperative)
        fp = FarmerPaymentFactory(cycle=cycle, farmer=farmer, cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='SUCCESS', farmer_payment=fp,
        )
        update_batch_summary(str(batch.pk))
        cycle.refresh_from_db()
        assert cycle.status == 'DISBURSED'

    def test_update_sets_farmer_payment_paid(self, cooperative):
        cycle = PaymentCycleFactory(cooperative=cooperative, status=CycleStatus.LOCKED)
        batch = DisbursementBatchFactory(cooperative=cooperative, payment_cycle=cycle)
        farmer = FarmerFactory(cooperative=cooperative)
        fp = FarmerPaymentFactory(cycle=cycle, farmer=farmer, cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='SUCCESS', farmer_payment=fp,
        )
        update_batch_summary(str(batch.pk))
        fp.refresh_from_db()
        assert fp.payment_status == 'PAID'

    def test_update_sets_farmer_payment_failed(self, cooperative):
        cycle = PaymentCycleFactory(cooperative=cooperative, status=CycleStatus.LOCKED)
        batch = DisbursementBatchFactory(cooperative=cooperative, payment_cycle=cycle)
        farmer = FarmerFactory(cooperative=cooperative)
        fp = FarmerPaymentFactory(cycle=cycle, farmer=farmer, cooperative=cooperative)
        tx = DisbursementTransactionFactory(
            batch=batch, farmer=farmer, cooperative=cooperative,
            status='FAILED', farmer_payment=fp,
        )
        update_batch_summary(str(batch.pk))
        fp.refresh_from_db()
        assert fp.payment_status == 'FAILED'

    def test_update_batch_not_found(self):
        result = update_batch_summary('00000000-0000-0000-0000-000000000000')
        assert result is None
