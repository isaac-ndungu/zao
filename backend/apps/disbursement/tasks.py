import logging
import uuid
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, F, Sum, When
from django.db.models import IntegerField
from django.db.models.functions import Greatest
from django.forms.models import model_to_dict
from django.utils import timezone

from apps.base.constants import UserRole
from apps.notifications.email import send_stuck_payments_alert
from apps.payment_engine.models import FarmerPayment, PaymentCycle

from .models import BatchStatus, DisbursementBatch, DisbursementTransaction, FailedDisbursement
from .utils import normalize_mpesa_number, validate_disbursement_window
from .utils.mpesa import MpesaDarajaClient

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER_KEY = 'mpesa:circuit_breaker:open'
FAILURE_COUNT_KEY = 'mpesa:circuit_breaker:failures'
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_COOLDOWN = 900  # 15 minutes


def is_circuit_open() -> bool:
    return cache.get(CIRCUIT_BREAKER_KEY, False)


def record_failure() -> None:
    if cache.get(FAILURE_COUNT_KEY) is None:
        cache.set(FAILURE_COUNT_KEY, 0, timeout=CIRCUIT_BREAKER_COOLDOWN)
    failures = cache.incr(FAILURE_COUNT_KEY, 1)
    if failures >= CIRCUIT_BREAKER_THRESHOLD:
        cache.set(CIRCUIT_BREAKER_KEY, True, timeout=CIRCUIT_BREAKER_COOLDOWN)
        logger.warning(
            "M-Pesa circuit breaker OPENED — pausing disbursements for %ds",
            CIRCUIT_BREAKER_COOLDOWN,
        )


def record_success() -> None:
    cache.delete(FAILURE_COUNT_KEY)
    cache.delete(CIRCUIT_BREAKER_KEY)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=30,
    time_limit=60,
)
def send_single_mpesa_disbursement(
    self,
    transaction_id: str,
    batch_id: str,
    phone_number: str,
    amount: Decimal,
    command_id: str,
    farmer_name: str,
):
    from celery.exceptions import SoftTimeLimitExceeded

    try:
        # Phase 1: DB writes in transaction with idempotency guards
        with transaction.atomic():
            txn = DisbursementTransaction.objects.select_for_update().get(id=transaction_id)

            # Guard 1: Already processed — skip
            if txn.status not in ('PENDING', 'FAILED'):
                return {'status': 'skipped', 'reason': f'Already {txn.status}'}

            # Guard 2: Max retries exceeded
            if txn.retry_count >= 3:
                txn.status = 'FAILED'
                txn.failure_reason = 'Max retries exceeded'
                txn.save(update_fields=['status', 'failure_reason'])
                return {'status': 'failed', 'reason': 'max_retries'}

            batch = DisbursementBatch.objects.get(id=batch_id)

            try:
                validate_disbursement_window()
            except RuntimeError as e:
                txn.status = 'FAILED'
                txn.failure_reason = str(e)
                txn.failed_at = timezone.now()
                txn.save(update_fields=['status', 'failure_reason', 'failed_at'])
                return {'error': str(e), 'transaction_id': transaction_id}

            normalized_phone = normalize_mpesa_number(phone_number)

            txn.retry_count += 1
            txn.status = 'QUEUED'
            txn.queued_at = timezone.now()
            txn.recipient_identifier = normalized_phone
            txn.recipient_name = farmer_name
            txn.save(update_fields=[
                'status', 'queued_at', 'recipient_identifier',
                'recipient_name', 'retry_count',
            ])

        # Phase 2: M-Pesa API call OUTSIDE transaction
        if is_circuit_open():
            try:
                raise self.retry(countdown=300, max_retries=1)
            except self.MaxRetriesExceededError:
                logger.error("Circuit breaker open — retry exhausted for txn %s", transaction_id)
                return {'error': 'Circuit breaker open', 'transaction_id': transaction_id}

        coop_shortcode = batch.cooperative.mpesa_shortcode or None
        client = MpesaDarajaClient(shortcode=coop_shortcode)
        conversation_id = txn.conversation_id or str(txn.id)

        try:
            response = client.initiate_b2c(
                amount=amount,
                phone_number=normalized_phone,
                conversation_id=conversation_id,
                command_id=command_id,
                remarks=f'Coop payment batch {batch_id[:8]}',
                occasion=farmer_name[:100],
            )
        except SoftTimeLimitExceeded:
            # Task timed out — mark transaction for reconciliation
            with transaction.atomic():
                txn = DisbursementTransaction.objects.select_for_update().get(id=transaction_id)
                txn.status = 'QUEUED'
                txn.failure_reason = 'Timed out — pending reconciliation'
                txn.save(update_fields=['status', 'failure_reason'])
            logger.warning(
                "B2C timed out for txn %s, left as QUEUED for reconciliation",
                transaction_id,
            )
            return {'status': 'TIMEOUT', 'transaction_id': transaction_id}
        except Exception as exc:
            logger.error("Daraja B2C failed for txn %s: %s", transaction_id, exc)
            with transaction.atomic():
                txn = DisbursementTransaction.objects.select_for_update().get(id=transaction_id)
                txn.status = 'FAILED'
                txn.failure_reason = str(exc)
                txn.failed_at = timezone.now()
                txn.save(update_fields=['status', 'failure_reason', 'failed_at'])
            record_failure()
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error("Max retries exceeded for transaction %s", transaction_id)
                _move_to_dead_letter(transaction_id, batch_id, str(exc))
            return {'error': str(exc), 'transaction_id': transaction_id}

        # Phase 3: Update status after successful API call
        with transaction.atomic():
            txn = DisbursementTransaction.objects.select_for_update().get(id=transaction_id)
            txn.status = 'SENT'
            txn.sent_at = timezone.now()
            txn.conversation_id = conversation_id
            txn.transaction_id = response.get('TransactionID', '')
            txn.originator_conversation_id = response.get('OriginatorConversationID', '')
            txn.result_code = response.get('ResponseCode', '')
            txn.result_desc = response.get('ResponseDescription', '')
            txn.save(update_fields=[
                'status', 'sent_at', 'conversation_id', 'transaction_id',
                'originator_conversation_id', 'result_code', 'result_desc',
            ])

    except DisbursementTransaction.DoesNotExist:
        logger.error("Transaction %s not found", transaction_id)
        return {'error': 'Transaction not found'}
    except DisbursementBatch.DoesNotExist:
        logger.error("Batch %s not found", batch_id)
        return {'error': 'Batch not found'}

    logger.info(
        "B2C sent: %s to %s amount %.2f — OriginatorConvID: %s, TransactionID: %s",
        transaction_id, normalized_phone, amount,
        txn.originator_conversation_id, txn.transaction_id,
    )
    record_success()

    return {
        'status': 'SENT',
        'transaction_id': transaction_id,
        'originator_conversation_id': txn.originator_conversation_id,
        'transaction_id_mpesa': txn.transaction_id,
    }


@shared_task(bind=True, soft_time_limit=120, time_limit=180)
def process_batch_disbursements(self, batch_id: str):
    try:
        batch = DisbursementBatch.objects.select_related('cooperative').get(id=batch_id)
    except DisbursementBatch.DoesNotExist:
        logger.error("Batch %s not found", batch_id)
        return {'error': 'Batch not found'}

    if batch.status in ('COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'):
        logger.warning("Batch %s is already %s, skipping", batch_id, batch.status)
        return {'status': 'skipped', 'reason': f'Already {batch.status}'}

    if batch.status == 'REVIEW':
        logger.warning("Batch %s is in REVIEW — awaiting manual action", batch_id)
        return {'status': 'skipped', 'reason': 'Batch in REVIEW status'}

    try:
        validate_disbursement_window()
    except RuntimeError as e:
        logger.warning("Batch %s skipped: %s", batch_id, e)
        return {'error': str(e), 'batch_id': batch_id}

    if batch.status == 'PROCESSING':
        stuck_threshold = timezone.now() - timedelta(minutes=30)
        if batch.updated_at < stuck_threshold:
            logger.warning("Batch %s stuck in PROCESSING for >30 min — recovering", batch_id)
            pending_txns = batch.transactions.filter(status__in=['PENDING', 'QUEUED'])
            if not pending_txns.exists():
                update_batch_summary.delay(batch_id)
                return {'status': 'recovered', 'action': 'summary_only'}
            batch.status = BatchStatus.PENDING
            batch.celery_task_id = ''
            batch.save(update_fields=['status', 'celery_task_id'])
        else:
            logger.warning("Batch %s still processing — skipping duplicate", batch_id)
            return {'status': 'skipped', 'reason': 'Already PROCESSING'}

    pending_qs = DisbursementTransaction.objects.filter(
        batch=batch, status='PENDING', payment_method='M_PESA',
    ).select_related('farmer').order_by(
        Case(
            When(payment_method='M_PESA', then=0),
            When(payment_method='BANK', then=1),
            When(payment_method='CASH', then=2),
            output_field=IntegerField(),
        ),
        'created_at', 'id',
    )

    if not pending_qs.exists():
        logger.info("Batch %s: no pending M-PESA transactions", batch_id)
        batch.status = 'COMPLETED'
        batch.save(update_fields=['status'])
        return {'status': 'COMPLETED', 'batch_id': batch_id, 'processed': 0}

    total_pending = pending_qs.count()

    batch.status = 'PROCESSING'
    batch.celery_task_id = self.request.id or ''
    batch.save(update_fields=['status', 'celery_task_id'])

    total_mpesa_amount = pending_qs.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    coop_shortcode = batch.cooperative.mpesa_shortcode or None
    client = MpesaDarajaClient(shortcode=coop_shortcode)

    try:
        sufficient, available = client.check_balance(total_mpesa_amount)
    except Exception as exc:
        logger.error('Balance check failed for batch %s: %s — holding for review', batch_id, exc)
        batch.status = BatchStatus.REVIEW
        batch.notes = f'Balance check failed: {exc}'
        batch.save(update_fields=['status', 'notes'])
        _notify_accountant_async(batch_id, f'Balance check failed: {exc} — batch held for review')
        return {'error': 'Balance check failed', 'batch_id': batch_id, 'status': 'REVIEW'}

    if not sufficient:
        logger.warning(
            'Batch %s aborted: insufficient float. required=%s available=%s',
            batch_id, total_mpesa_amount, available,
        )
        pending_qs.update(
            status='FAILED',
            failure_reason=f'Insufficient float balance. Required: {total_mpesa_amount}, Available: {available}',
            failed_at=timezone.now(),
        )
        for txn in pending_qs.select_related('farmer'):
            if txn.farmer_payment_id:
                FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                    payment_status='FAILED',
                )
                reverse_deductions_on_failure.delay(
                    farmer_id=str(txn.farmer_id),
                    farmer_payment_id=str(txn.farmer_payment_id),
                )
        update_batch_summary.delay(str(batch.id))
        return {
            'error': 'Insufficient float balance',
            'required': str(total_mpesa_amount),
            'available': str(available),
            'batch_id': batch_id,
        }

    CHUNK_SIZE = 50
    CHUNK_DELAY = 30
    processed_count = 0
    pending_iter = pending_qs.iterator(chunk_size=CHUNK_SIZE)

    chunk = []
    for txn in pending_iter:
        chunk.append(txn)
        if len(chunk) >= CHUNK_SIZE:
            for t in chunk:
                mpesa_number = t.recipient_identifier
                try:
                    mpesa_number = normalize_mpesa_number(mpesa_number)
                except ValueError:
                    t.status = 'FAILED'
                    t.failure_reason = f'Invalid M-Pesa number: {mpesa_number}'
                    t.failed_at = timezone.now()
                    t.save(update_fields=['status', 'failure_reason', 'failed_at'])
                    continue

                send_single_mpesa_disbursement.delay(
                    transaction_id=str(t.id),
                    batch_id=str(batch.id),
                    phone_number=mpesa_number,
                    amount=t.amount,
                    command_id=batch.command_id,
                    farmer_name=str(t.farmer),
                )
                processed_count += 1

            update_batch_summary.apply_async(
                args=[str(batch.id)],
                countdown=CHUNK_DELAY,
            )
            chunk = []

    if chunk:
        for t in chunk:
            mpesa_number = t.recipient_identifier
            try:
                mpesa_number = normalize_mpesa_number(mpesa_number)
            except ValueError:
                t.status = 'FAILED'
                t.failure_reason = f'Invalid M-Pesa number: {mpesa_number}'
                t.failed_at = timezone.now()
                t.save(update_fields=['status', 'failure_reason', 'failed_at'])
                continue

            send_single_mpesa_disbursement.delay(
                transaction_id=str(t.id),
                batch_id=str(batch.id),
                phone_number=mpesa_number,
                amount=t.amount,
                command_id=batch.command_id,
                farmer_name=str(t.farmer),
            )
            processed_count += 1

    return {
        'status': 'PROCESSING',
        'batch_id': batch_id,
        'total_pending': total_pending,
        'queued': processed_count,
    }


@shared_task
def update_batch_summary(batch_id: str):
    try:
        batch = DisbursementBatch.objects.get(id=batch_id)
    except DisbursementBatch.DoesNotExist:
        logger.error("Batch %s not found", batch_id)
        return

    transactions = batch.transactions.all()
    total = transactions.count()
    successful = transactions.filter(status='SUCCESS').count()
    failed = transactions.filter(status='FAILED').count()
    sent = transactions.filter(status='SENT').count()
    queued = transactions.filter(status='QUEUED').count()
    pending = transactions.filter(status='PENDING').count()

    batch.total_transactions = total
    batch.successful_count = successful
    batch.failed_count = failed

    all_statuses = set(transactions.values_list('status', flat=True))
    terminal = {'SUCCESS', 'FAILED', 'CANCELLED'}
    non_active = {'PENDING', 'QUEUED'}

    all_terminal = all(s in terminal for s in all_statuses)
    all_idle = all(s in terminal | non_active | {'SENT'} for s in all_statuses) and sent == 0

    if all_terminal:
        if failed > 0 and successful == 0:
            batch.status = BatchStatus.FAILED
        elif successful > 0 and failed > 0:
            batch.status = BatchStatus.PARTIALLY_COMPLETED
        else:
            batch.status = BatchStatus.COMPLETED
    elif queued > 0 or pending > 0:
        batch.status = BatchStatus.PROCESSING
    elif all_idle:
        batch.status = BatchStatus.COMPLETED

    batch.save(update_fields=[
        'status', 'total_transactions', 'successful_count', 'failed_count',
    ])

    if batch.status in (BatchStatus.COMPLETED, BatchStatus.PARTIALLY_COMPLETED):
        from apps.payment_engine.models import PaymentCycle
        cycle = batch.payment_cycle
        if cycle and cycle.status == 'LOCKED':
            cycle.status = 'DISBURSED'
            cycle.save(update_fields=['status'])

        successful_txns = transactions.filter(status='SUCCESS')
        farmer_payment_ids = list(
            successful_txns.values_list('farmer_payment_id', flat=True)
        )
        FarmerPayment.objects.filter(
            id__in=farmer_payment_ids,
        ).update(payment_status='PAID')

    if batch.status in (BatchStatus.FAILED, BatchStatus.PARTIALLY_COMPLETED):
        failed_txns = transactions.filter(status='FAILED')
        for txn in failed_txns:
            if txn.farmer_payment_id:
                FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                    payment_status='FAILED',
                )

    logger.info("Batch %s summary: %s", batch_id, batch.status)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=300, time_limit=360)
def retry_batch_disbursements(self, batch_id: str):
    try:
        batch = DisbursementBatch.objects.select_related('cooperative').get(id=batch_id)
    except DisbursementBatch.DoesNotExist:
        logger.error("Batch %s not found", batch_id)
        return {'error': 'Batch not found'}

    failed_qs = DisbursementTransaction.objects.filter(
        batch=batch, status='FAILED', payment_method='M_PESA',
    ).select_related('farmer', 'batch__cooperative')

    if not failed_qs.exists():
        logger.info("Batch %s: no failed M-PESA transactions to retry", batch_id)
        return {'batch_id': batch_id, 'checked': 0, 'retried': 0}

    batch.status = 'PROCESSING'
    batch.celery_task_id = self.request.id or ''
    batch.save(update_fields=['status', 'celery_task_id'])

    retried = 0
    already_success = 0
    checked = failed_qs.count()

    for txn in failed_qs:
        coop_shortcode = txn.batch.cooperative.mpesa_shortcode or None
        client = MpesaDarajaClient(shortcode=coop_shortcode)

        if txn.conversation_id:
            try:
                response = client.query_transaction_status(txn.conversation_id)
                result_code = response.get('ResultCode', '-1')
                result_desc = response.get('ResultDesc', '')

                if result_code == '0':
                    txn.status = 'SUCCESS'
                    txn.completed_at = timezone.now()
                    txn.result_code = result_code
                    txn.result_desc = result_desc
                    txn.save(update_fields=['status', 'completed_at', 'result_code', 'result_desc'])
                    already_success += 1

                    if txn.farmer_payment_id:
                        FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                            payment_status='PAID',
                        )
                    update_batch_summary.delay(str(txn.batch_id))
                    continue
            except Exception as exc:
                logger.warning(
                    "Status query failed for txn %s conv %s: %s — proceeding with retry",
                    txn.id, txn.conversation_id, exc,
                )

        new_conversation_id = str(uuid.uuid4())
        txn.status = 'PENDING'
        txn.conversation_id = new_conversation_id
        txn.failure_reason = ''
        txn.result_code = ''
        txn.result_desc = ''
        txn.retry_count = 0
        txn.failed_at = None
        txn.save(update_fields=[
            'status', 'conversation_id', 'failure_reason',
            'result_code', 'result_desc', 'retry_count', 'failed_at',
        ])

        send_single_mpesa_disbursement.delay(
            transaction_id=str(txn.id),
            batch_id=str(batch.id),
            phone_number=txn.recipient_identifier,
            amount=txn.amount,
            command_id=batch.command_id,
            farmer_name=str(txn.farmer),
        )
        retried += 1

    logger.info(
        "Batch %s retry: checked=%d already_success=%d retried=%d",
        batch_id, checked, already_success, retried,
    )
    return {
        'batch_id': batch_id,
        'checked': checked,
        'already_success': already_success,
        'retried': retried,
    }


@shared_task
def reconcile_stuck_transactions():
    stuck_time = timezone.now() - timedelta(minutes=10)

    stuck = DisbursementTransaction.objects.filter(
        status__in=['QUEUED', 'SENT'],
        sent_at__lte=stuck_time,
    ).select_related('batch', 'batch__cooperative')

    reconciled = 0
    stuck_by_coop: dict[str, list[DisbursementTransaction]] = defaultdict(list)

    for txn in stuck:
        coop_shortcode = txn.batch.cooperative.mpesa_shortcode or None
        client = MpesaDarajaClient(shortcode=coop_shortcode)
        if not txn.conversation_id:
            txn.status = 'FAILED'
            txn.failure_reason = 'Stuck without conversation_id'
            txn.failed_at = timezone.now()
            txn.save(update_fields=['status', 'failure_reason', 'failed_at'])
            reconciled += 1
            stuck_by_coop[str(txn.batch.cooperative_id)].append(txn)
            continue

        try:
            response = client.query_transaction_status(txn.conversation_id)
        except Exception as exc:
            logger.warning(
                "Status query failed for txn %s conv %s: %s",
                txn.id, txn.conversation_id, exc,
            )
            continue

        result_code = response.get('ResultCode', '-1')
        result_desc = response.get('ResultDesc', '')

        if result_code == '0':
            txn.status = 'SUCCESS'
            txn.completed_at = timezone.now()
        else:
            txn.status = 'FAILED'
            txn.failure_reason = result_desc
            txn.failed_at = timezone.now()

        txn.result_code = result_code
        txn.result_desc = result_desc
        txn.save(update_fields=[
            'status', 'result_code', 'result_desc',
            'completed_at', 'failed_at',
        ])

        update_batch_summary.delay(str(txn.batch_id))
        reconciled += 1
        stuck_by_coop[str(txn.batch.cooperative_id)].append(txn)

        if txn.status == 'SUCCESS':
            send_disbursement_sms.delay(
                phone_number=txn.recipient_identifier,
                farmer_name=txn.recipient_name,
                amount=float(txn.amount),
                farner_payment_id=str(txn.farmer_payment_id) if txn.farmer_payment_id else '',
            )

    logger.info("Reconciled %d stuck transactions", reconciled)

    if reconciled:
        _send_stuck_alerts(stuck_by_coop)

    return {'reconciled': reconciled}


def _send_stuck_alerts(stuck_by_coop: dict[str, list[DisbursementTransaction]]) -> None:
    from apps.auth_api.models import User

    for coop_id, txns in stuck_by_coop.items():
        if not txns:
            continue

        recipient_emails = list(User.objects.filter(
            role=UserRole.ACCOUNTANT,
            cooperative_id=coop_id,
        ).values_list('email', flat=True))

        if not recipient_emails:
            recipient_emails = list(User.objects.filter(
                role=UserRole.MANAGER,
                cooperative_id=coop_id,
            ).values_list('email', flat=True))

        if not recipient_emails:
            continue

        send_stuck_payments_alert(recipient_emails, txns, getattr(settings, 'FRONTEND_URL', None))

        logger.info(
            'Sent stuck transaction alert for coop %s to %s',
            coop_id, ', '.join(recipient_emails),
        )


def _move_to_dead_letter(transaction_id: str, batch_id: str, reason: str) -> None:
    try:
        txn = DisbursementTransaction.objects.get(id=transaction_id)
        FailedDisbursement.objects.create(
            cooperative=txn.batch.cooperative if txn.batch else None,
            batch=txn.batch,
            transaction=txn,
            farmer=txn.farmer,
            amount=txn.amount,
            recipient_identifier=txn.recipient_identifier,
            recipient_name=txn.recipient_name,
            failure_reason=reason,
            conversation_id=txn.conversation_id,
            transaction_id_mpesa=txn.transaction_id,
        )
        logger.warning(
            "Moved txn %s to dead letter queue: %s",
            transaction_id, reason,
        )
    except Exception as exc:
        logger.error(
            "Failed to move txn %s to dead letter: %s",
            transaction_id, exc,
        )


def _notify_accountant_async(context_id: str, message: str) -> None:
    from apps.auth_api.models import User
    try:
        batch = DisbursementBatch.objects.select_related('cooperative').get(id=context_id)
        coop_id = str(batch.cooperative_id)
    except (DisbursementBatch.DoesNotExist, ValueError):
        coop_id = None

    recipients = []
    if coop_id:
        recipients = list(User.objects.filter(
            role__in=[UserRole.ACCOUNTANT, UserRole.MANAGER],
            cooperative_id=coop_id,
        ).values_list('email', flat=True))

    if not recipients:
        recipients = list(User.objects.filter(
            role=UserRole.ADMIN,
        ).values_list('email', flat=True))

    if recipients:
        send_stuck_payments_alert(
            recipients, [], getattr(settings, 'FRONTEND_URL', None),
        )
        logger.info("Notified accountant for %s: %s", context_id, message)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def reverse_deductions_on_failure(self, farmer_id: str, farmer_payment_id: str):
    try:
        from apps.base.utils import log_audit
        from apps.deductions.models import Deduction
        from apps.loans.models import Loan, LoanRepayment
        from apps.payment_engine.models import FarmerPayment

        farmer_payment = FarmerPayment.objects.filter(
            id=farmer_payment_id,
        ).first()

        loan_repayment = LoanRepayment.objects.filter(
            farmer_payment_id=farmer_payment_id,
        ).first()

        deductions = Deduction.objects.filter(
            farmer_id=farmer_id,
            cycle_id=farmer_payment.cycle_id,
        )
        for ded in deductions:
            if ded.deduction_type == 'LOAN_REPAYMENT':
                LoanRepayment.objects.filter(farmer_payment_id=farmer_payment_id).delete()
            log_audit(
                actor=None,
                resource_type='deduction',
                resource_id=str(ded.id),
                action='DELETE',
                previous_value=model_to_dict(ded),
                cooperative_id=str(ded.cooperative_id) if ded.cooperative_id else None,
            )
        deductions.delete()

        if loan_repayment:
            Loan.objects.filter(id=loan_repayment.loan_id).update(
                installments_paid=Greatest(F('installments_paid') - 1, 0),
                status='ACTIVE',
            )

        logger.info(
            "Reversed deductions for farmer %s on payment %s",
            farmer_id, farmer_payment_id,
        )
    except Exception as e:
        logger.error(
            "Failed to reverse deductions for payment %s: %s",
            farmer_payment_id, e,
        )
        _notify_accountant_async(
            farmer_payment_id,
            f'CRITICAL: Failed to reverse deductions for payment {farmer_payment_id}. '
            f'Error: {e}. Manual intervention required.',
        )
        raise

    return {'farmer_id': farmer_id, 'farmer_payment_id': farmer_payment_id}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_disbursement_sms(self, phone_number: str, farmer_name: str, amount: float, farner_payment_id: str = ''):
    message = (
        f"Dear {farmer_name}, your payment of KES {amount:,.2f} "
        f"has been sent to your M-Pesa. Thank you for partnering with us."
    )

    from apps.notifications.utils import send_sms
    result = send_sms(phone_number, message)
    if result['success']:
        logger.info('Payment SMS sent to %s', phone_number)
    else:
        logger.error('Failed to send payment SMS to %s: %s', phone_number, result['error'])
        raise RuntimeError(f'Payment SMS failed: {result["error"]}')
