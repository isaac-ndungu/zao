from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from apps.disbursement.models import (
    BatchStatus,
    CommandId,
    DisbursementBatch,
    DisbursementPaymentMethod,
    DisbursementTransaction,
    TransactionStatus,
)

from apps.conftest import positive_decimals


# =============================================================================
# DisbursementBatch Tests
# =============================================================================

class TestDisbursementBatch:
    def test_create(self, cooperative):
        batch = DisbursementBatch.objects.create(
            cooperative=cooperative,
        )
        assert batch.pk is not None
        assert batch.status == BatchStatus.PENDING

    def test_str(self, cooperative):
        batch = DisbursementBatch.objects.create(
            cooperative=cooperative,
        )
        assert 'Batch' in str(batch)
        assert 'Pending' in str(batch)

    def test_default_command_id(self, cooperative):
        batch = DisbursementBatch.objects.create(
            cooperative=cooperative,
        )
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
        from django.utils import timezone
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


# =============================================================================
# DisbursementTransaction Tests
# =============================================================================

class TestDisbursementTransaction:
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


# =============================================================================
# Hypothesis property-based tests for disbursement
# =============================================================================

class TestDisbursementHypothesis:
    @settings(max_examples=50)
    @given(
        amount=positive_decimals,
        withholding_tax=positive_decimals,
    )
    def test_disbursement_net_never_exceeds_amount(self, amount, withholding_tax):
        assume(amount > 0 and withholding_tax > 0)
        net = amount - withholding_tax
        assert net <= amount
        assert net >= amount - withholding_tax
