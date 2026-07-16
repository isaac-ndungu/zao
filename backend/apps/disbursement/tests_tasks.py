import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from apps.base.constants import UserRole
from apps.conftest import (
    CooperativeFactory,
    DisbursementBatchFactory,
    DisbursementTransactionFactory,
    FarmerFactory,
    FarmerPaymentFactory,
    LoanFactory,
    LoanRepaymentFactory,
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
from apps.disbursement.tasks import (
    process_batch_disbursements,
    reverse_deductions_on_failure,
    retry_batch_disbursements,
    send_single_mpesa_disbursement,
    update_batch_summary,
)
from apps.deductions.models import Deduction
from apps.loans.models import Loan, LoanRepayment
from apps.payment_engine.models import CycleStatus, FarmerPayment, PaymentCycle

pytestmark = pytest.mark.django_db


def _uid():
    return str(uuid.uuid4())


@pytest.fixture
def cooperative():
    return CooperativeFactory(mpesa_shortcode='12345')


@pytest.fixture
def farmer(cooperative):
    return FarmerFactory(cooperative=cooperative)


@pytest.fixture
def payment_cycle(cooperative):
    return PaymentCycleFactory(
        cooperative=cooperative,
        status=CycleStatus.LOCKED,
    )


@pytest.fixture
def farmer_payment(payment_cycle, farmer):
    return FarmerPaymentFactory(
        cycle=payment_cycle,
        farmer=farmer,
        gross_amount=Decimal('10000.00'),
        net_amount=Decimal('8500.00'),
        payment_status='PENDING',
    )


@pytest.fixture
def disbursement_batch(cooperative, payment_cycle):
    return DisbursementBatchFactory(
        cooperative=cooperative,
        payment_cycle=payment_cycle,
        status=BatchStatus.PENDING,
        command_id='BusinessPayment',
        total_amount=Decimal('10000.00'),
    )


@pytest.fixture
def pending_txn(disbursement_batch, farmer, farmer_payment):
    return DisbursementTransactionFactory(
        cooperative=disbursement_batch.cooperative,
        batch=disbursement_batch,
        farmer=farmer,
        farmer_payment=farmer_payment,
        amount=Decimal('5000.00'),
        payment_method=DisbursementPaymentMethod.M_PESA,
        recipient_identifier='+254712345678',
        recipient_name=str(farmer),
        status=TransactionStatus.PENDING,
        conversation_id=_uid(),
        transaction_id=_uid(),
    )


# =============================================================================
# send_single_mpesa_disbursement
# =============================================================================

class TestSendSingleMpesaDisbursement:
    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_successful_disbursement(self, MockClient, pending_txn, disbursement_batch):
        mock_client = MockClient.return_value
        mock_client.initiate_b2c.return_value = {
            'TransactionID': 'MPESA-123',
            'OriginatorConversationID': 'ORIG-456',
            'ResponseCode': '0',
            'ResponseDescription': 'Success',
        }

        with patch('apps.disbursement.tasks.validate_disbursement_window'):
            result = send_single_mpesa_disbursement(
                transaction_id=str(pending_txn.id),
                batch_id=str(disbursement_batch.id),
                phone_number='+254712345678',
                amount=Decimal('5000.00'),
                command_id='BusinessPayment',
                farmer_name='Test Farmer',
            )

        assert result['status'] == 'SENT'
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.SENT

    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_already_processed_skips(self, MockClient, pending_txn, disbursement_batch):
        pending_txn.status = TransactionStatus.SUCCESS
        pending_txn.save(update_fields=['status'])

        result = send_single_mpesa_disbursement(
            transaction_id=str(pending_txn.id),
            batch_id=str(disbursement_batch.id),
            phone_number='+254712345678',
            amount=Decimal('5000.00'),
            command_id='BusinessPayment',
            farmer_name='Test Farmer',
        )
        assert result['status'] == 'skipped'

    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_max_retries_exceeded(self, MockClient, pending_txn, disbursement_batch):
        pending_txn.retry_count = 3
        pending_txn.save(update_fields=['retry_count'])

        result = send_single_mpesa_disbursement(
            transaction_id=str(pending_txn.id),
            batch_id=str(disbursement_batch.id),
            phone_number='+254712345678',
            amount=Decimal('5000.00'),
            command_id='BusinessPayment',
            farmer_name='Test Farmer',
        )
        assert result['status'] == 'failed'
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.FAILED

    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_disbursement_window_failure(self, MockClient, pending_txn, disbursement_batch):
        with patch('apps.disbursement.tasks.validate_disbursement_window',
                    side_effect=RuntimeError('Outside disbursement window')):
            result = send_single_mpesa_disbursement(
                transaction_id=str(pending_txn.id),
                batch_id=str(disbursement_batch.id),
                phone_number='+254712345678',
                amount=Decimal('5000.00'),
                command_id='BusinessPayment',
                farmer_name='Test Farmer',
            )
        assert 'error' in result or 'Outside disbursement window' in str(result)
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.FAILED

    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_api_exception_marks_failed(self, MockClient, pending_txn, disbursement_batch):
        mock_client = MockClient.return_value
        mock_client.initiate_b2c.side_effect = Exception('Connection timeout')

        with patch('apps.disbursement.tasks.validate_disbursement_window'):
            with patch.object(
                send_single_mpesa_disbursement, 'retry',
                side_effect=send_single_mpesa_disbursement.MaxRetriesExceededError(),
            ):
                result = send_single_mpesa_disbursement(
                    transaction_id=str(pending_txn.id),
                    batch_id=str(disbursement_batch.id),
                    phone_number='+254712345678',
                    amount=Decimal('5000.00'),
                    command_id='BusinessPayment',
                    farmer_name='Test Farmer',
                )
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.FAILED
        assert 'Connection timeout' in (pending_txn.failure_reason or '')

    def test_nonexistent_transaction(self, disbursement_batch):
        result = send_single_mpesa_disbursement(
            transaction_id=str('00000000-0000-0000-0000-000000000000'),
            batch_id=str(disbursement_batch.id),
            phone_number='+254712345678',
            amount=Decimal('5000.00'),
            command_id='BusinessPayment',
            farmer_name='Test Farmer',
        )
        assert 'error' in result

    def test_nonexistent_batch(self, pending_txn):
        result = send_single_mpesa_disbursement(
            transaction_id=str(pending_txn.id),
            batch_id=str('00000000-0000-0000-0000-000000000000'),
            phone_number='+254712345678',
            amount=Decimal('5000.00'),
            command_id='BusinessPayment',
            farmer_name='Test Farmer',
        )
        assert 'error' in result


# =============================================================================
# process_batch_disbursements
# =============================================================================

class TestProcessBatchDisbursements:
    @patch('apps.disbursement.tasks.send_single_mpesa_disbursement.delay')
    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_processes_pending_transactions(self, MockClient, mock_delay,
                                             disbursement_batch, pending_txn):
        mock_client = MockClient.return_value
        mock_client.check_balance.return_value = (True, Decimal('100000'))

        with patch('apps.disbursement.tasks.validate_disbursement_window'):
            result = process_batch_disbursements(str(disbursement_batch.id))

        assert result['status'] == 'PROCESSING'
        assert result['queued'] == 1
        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == BatchStatus.PROCESSING

    def test_already_completed_batch_skips(self, disbursement_batch):
        disbursement_batch.status = BatchStatus.COMPLETED
        disbursement_batch.save(update_fields=['status'])

        result = process_batch_disbursements(str(disbursement_batch.id))
        assert result['status'] == 'skipped'

    def test_nonexistent_batch(self):
        result = process_batch_disbursements(
            str('00000000-0000-0000-0000-000000000000')
        )
        assert 'error' in result

    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_disbursement_window_failure_aborts(self, MockClient, disbursement_batch, pending_txn):
        with patch('apps.disbursement.tasks.validate_disbursement_window',
                    side_effect=RuntimeError('Outside disbursement window')):
            result = process_batch_disbursements(str(disbursement_batch.id))
        assert 'error' in result
        assert 'Outside disbursement window' in result['error']

    @patch('apps.disbursement.tasks.send_single_mpesa_disbursement.delay')
    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_insufficient_float_fails_all(self, MockClient, mock_delay,
                                           disbursement_batch, pending_txn):
        mock_client = MockClient.return_value
        mock_client.check_balance.return_value = (False, Decimal('100'))

        with patch('apps.disbursement.tasks.validate_disbursement_window'):
            result = process_batch_disbursements(str(disbursement_batch.id))

        assert 'error' in result
        assert 'float' in result['error'].lower()
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.FAILED

    @patch('apps.disbursement.tasks.send_single_mpesa_disbursement.delay')
    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_no_pending_transactions_completes(self, MockClient, mock_delay,
                                                disbursement_batch):
        with patch('apps.disbursement.tasks.validate_disbursement_window'):
            result = process_batch_disbursements(str(disbursement_batch.id))

        assert result['status'] == 'COMPLETED'
        assert result['processed'] == 0


# =============================================================================
# reverse_deductions_on_failure
# =============================================================================

class TestReverseDeductionsOnFailure:
    def test_reverses_loan_repayment(self, farmer, payment_cycle, farmer_payment, cooperative):
        loan = LoanFactory(
            farmer=farmer,
            cooperative=cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            number_of_installments=10,
            installments_paid=3,
            status='ACTIVE',
        )
        LoanRepaymentFactory(
            loan=loan,
            farmer_payment=farmer_payment,
            amount=Decimal('1000.00'),
        )
        Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=cooperative,
            deduction_type='LOAN_REPAYMENT',
            amount=Decimal('1000.00'),
        )

        result = reverse_deductions_on_failure(
            farmer_id=str(farmer.id),
            farmer_payment_id=str(farmer_payment.id),
        )

        assert result['farmer_id'] == str(farmer.id)
        loan.refresh_from_db()
        assert loan.installments_paid == 2

    def test_deletes_deductions(self, farmer, payment_cycle, farmer_payment, cooperative):
        Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=cooperative,
            deduction_type='LEVY',
            amount=Decimal('500.00'),
        )
        Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=cooperative,
            deduction_type='INPUT_CREDIT',
            amount=Decimal('200.00'),
        )

        reverse_deductions_on_failure(
            farmer_id=str(farmer.id),
            farmer_payment_id=str(farmer_payment.id),
        )

        assert Deduction.objects.filter(farmer=farmer).count() == 0

    def test_no_loan_repayment_still_deletes_deductions(self, farmer, payment_cycle, farmer_payment, cooperative):
        Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=cooperative,
            deduction_type='LEVY',
            amount=Decimal('300.00'),
        )

        reverse_deductions_on_failure(
            farmer_id=str(farmer.id),
            farmer_payment_id=str(farmer_payment.id),
        )

        assert Deduction.objects.filter(farmer=farmer).count() == 0

    def test_loan_restored_to_active_on_repayment_reversal(self, farmer, payment_cycle,
                                                            farmer_payment, cooperative):
        loan = LoanFactory(
            farmer=farmer,
            cooperative=cooperative,
            amount_principal=Decimal('5000.00'),
            interest_rate=Decimal('5.00'),
            number_of_installments=5,
            installments_paid=1,
            status='ACTIVE',
        )
        LoanRepaymentFactory(
            loan=loan,
            farmer_payment=farmer_payment,
            amount=Decimal('1000.00'),
        )

        reverse_deductions_on_failure(
            farmer_id=str(farmer.id),
            farmer_payment_id=str(farmer_payment.id),
        )

        loan.refresh_from_db()
        assert loan.installments_paid == 0
        assert loan.status == 'ACTIVE'

    def test_only_deletes_deductions_for_target_cycle(self, farmer, cooperative):
        from apps.base.models import AuditLog
        from apps.payment_engine.models import PaymentCycle

        cycle_a = PaymentCycle.objects.create(
            cooperative=cooperative, start_date='2026-01-01', end_date='2026-01-31',
        )
        cycle_b = PaymentCycle.objects.create(
            cooperative=cooperative, start_date='2026-02-01', end_date='2026-02-28',
        )
        farmer_payment_a = FarmerPayment.objects.create(
            cooperative=cooperative, farmer=farmer, cycle=cycle_a,
            payment_status='PENDING', gross_amount=Decimal('5000'),
            net_amount=Decimal('5000'), total_quantity=Decimal('100'),
        )
        FarmerPayment.objects.create(
            cooperative=cooperative, farmer=farmer, cycle=cycle_b,
            payment_status='PENDING', gross_amount=Decimal('3000'),
            net_amount=Decimal('3000'), total_quantity=Decimal('60'),
        )
        Deduction.objects.create(
            farmer=farmer, cycle=cycle_a, cooperative=cooperative,
            deduction_type='LEVY', amount=Decimal('100.00'),
        )
        ded_in_cycle_a = Deduction.objects.filter(farmer=farmer, cycle=cycle_a).first()
        Deduction.objects.create(
            farmer=farmer, cycle=cycle_b, cooperative=cooperative,
            deduction_type='LEVY', amount=Decimal('200.00'),
        )

        assert Deduction.objects.filter(farmer=farmer, cycle=cycle_a).count() == 1
        assert Deduction.objects.filter(farmer=farmer, cycle=cycle_b).count() == 1

        reverse_deductions_on_failure(
            farmer_id=str(farmer.id),
            farmer_payment_id=str(farmer_payment_a.id),
        )

        assert Deduction.objects.filter(farmer=farmer, cycle=cycle_a).count() == 0
        assert Deduction.objects.filter(farmer=farmer, cycle=cycle_b).count() == 1

    def test_creates_audit_log_for_each_deletion(self, farmer, cooperative, payment_cycle,
                                                   farmer_payment):
        from apps.base.models import AuditLog

        Deduction.objects.create(
            farmer=farmer, cycle=payment_cycle, cooperative=cooperative,
            deduction_type='LEVY', amount=Decimal('100.00'),
        )
        Deduction.objects.create(
            farmer=farmer, cycle=payment_cycle, cooperative=cooperative,
            deduction_type='INPUT_CREDIT', amount=Decimal('200.00'),
        )
        ded_ids = list(
            Deduction.objects.filter(farmer=farmer, cycle=payment_cycle).values_list('id', flat=True)
        )

        reverse_deductions_on_failure(
            farmer_id=str(farmer.id),
            farmer_payment_id=str(farmer_payment.id),
        )

        audit_logs = AuditLog.objects.filter(
            resource_type='deduction', action='DELETE',
            resource_id__in=[str(i) for i in ded_ids],
        )
        assert audit_logs.count() == 2
        for log in audit_logs:
            assert log.previous_value is not None
            assert 'deduction_type' in log.previous_value
            assert 'amount' in log.previous_value


# =============================================================================
# retry_batch_disbursements
# =============================================================================

class TestRetryBatchDisbursements:
    @patch('apps.disbursement.tasks.send_single_mpesa_disbursement.delay')
    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_retries_failed_transactions(self, MockClient, mock_delay,
                                          disbursement_batch, pending_txn, cooperative):
        pending_txn.status = TransactionStatus.FAILED
        pending_txn.failure_reason = 'Connection timeout'
        pending_txn.conversation_id = ''
        pending_txn.transaction_id = _uid()
        pending_txn.save(update_fields=['status', 'failure_reason', 'conversation_id', 'transaction_id'])

        result = retry_batch_disbursements(str(disbursement_batch.id))

        assert result['retried'] == 1
        assert result['checked'] == 1
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.PENDING

    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_already_success_detected(self, MockClient, disbursement_batch, pending_txn, cooperative):
        mock_client = MockClient.return_value
        mock_client.query_transaction_status.return_value = {
            'ResultCode': '0',
            'ResultDesc': 'The service request has been accepted successfully',
        }
        pending_txn.status = TransactionStatus.FAILED
        pending_txn.conversation_id = _uid()
        pending_txn.save(update_fields=['status', 'conversation_id'])

        result = retry_batch_disbursements(str(disbursement_batch.id))

        assert result['already_success'] == 1
        assert result['retried'] == 0
        pending_txn.refresh_from_db()
        assert pending_txn.status == TransactionStatus.SUCCESS

    @patch('apps.disbursement.tasks.send_single_mpesa_disbursement.delay')
    @patch('apps.disbursement.tasks.MpesaDarajaClient')
    def test_no_failed_transactions(self, MockClient, mock_delay, disbursement_batch, cooperative):
        result = retry_batch_disbursements(str(disbursement_batch.id))
        assert result['retried'] == 0
        assert result['checked'] == 0

    def test_nonexistent_batch(self):
        result = retry_batch_disbursements(
            str('00000000-0000-0000-0000-000000000000')
        )
        assert 'error' in result


# =============================================================================
# update_batch_summary
# =============================================================================

class TestUpdateBatchSummary:
    def test_all_successful_marks_completed(self, disbursement_batch, pending_txn,
                                              farmer_payment):
        pending_txn.status = TransactionStatus.SUCCESS
        pending_txn.save(update_fields=['status'])

        update_batch_summary(str(disbursement_batch.id))

        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == BatchStatus.COMPLETED
        assert disbursement_batch.successful_count == 1

    def test_all_failed_marks_failed(self, disbursement_batch, pending_txn, farmer_payment):
        pending_txn.status = TransactionStatus.FAILED
        pending_txn.failure_reason = 'API error'
        pending_txn.save(update_fields=['status', 'failure_reason'])

        update_batch_summary(str(disbursement_batch.id))

        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == BatchStatus.FAILED
        assert disbursement_batch.failed_count == 1

    def test_mixed_status_marks_partially_completed(self, disbursement_batch, farmer,
                                                      farmer_payment, cooperative):
        txn1 = DisbursementTransactionFactory(
            cooperative=cooperative,
            batch=disbursement_batch,
            farmer=farmer,
            farmer_payment=farmer_payment,
            amount=Decimal('3000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            status=TransactionStatus.SUCCESS,
            conversation_id=_uid(),
            transaction_id=_uid(),
        )
        txn2 = DisbursementTransactionFactory(
            cooperative=cooperative,
            batch=disbursement_batch,
            farmer=farmer,
            amount=Decimal('2000.00'),
            payment_method=DisbursementPaymentMethod.M_PESA,
            status=TransactionStatus.FAILED,
            failure_reason='Timeout',
            conversation_id=_uid(),
            transaction_id=_uid(),
        )

        update_batch_summary(str(disbursement_batch.id))

        disbursement_batch.refresh_from_db()
        assert disbursement_batch.status == BatchStatus.PARTIALLY_COMPLETED

    def test_unlocks_cycle_on_completion(self, disbursement_batch, pending_txn,
                                          farmer_payment, payment_cycle):
        pending_txn.status = TransactionStatus.SUCCESS
        pending_txn.save(update_fields=['status'])

        update_batch_summary(str(disbursement_batch.id))

        payment_cycle.refresh_from_db()
        assert payment_cycle.status == CycleStatus.DISBURSED

    def test_marks_farmer_payments_paid(self, disbursement_batch, pending_txn,
                                          farmer_payment):
        pending_txn.status = TransactionStatus.SUCCESS
        pending_txn.save(update_fields=['status'])

        update_batch_summary(str(disbursement_batch.id))

        farmer_payment.refresh_from_db()
        assert farmer_payment.payment_status == 'PAID'

    def test_marks_failed_payments_failed(self, disbursement_batch, pending_txn,
                                            farmer_payment):
        pending_txn.status = TransactionStatus.FAILED
        pending_txn.failure_reason = 'API error'
        pending_txn.save(update_fields=['status', 'failure_reason'])

        update_batch_summary(str(disbursement_batch.id))

        farmer_payment.refresh_from_db()
        assert farmer_payment.payment_status == 'FAILED'

    def test_nonexistent_batch(self):
        update_batch_summary(str('00000000-0000-0000-0000-000000000000'))
