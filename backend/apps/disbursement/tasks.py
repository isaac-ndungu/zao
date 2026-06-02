import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Case, When
from django.db.models import IntegerField
from django.core.mail import send_mail
from django.utils import timezone

from apps.base.constants import UserRole
from apps.payment_engine.models import FarmerPayment, PaymentCycle

from .models import DisbursementBatch, DisbursementTransaction
from .utils import normalize_mpesa_number, validate_disbursement_window
from .utils.mpesa import MpesaDarajaClient

logger = logging.getLogger(__name__)


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
        client = MpesaDarajaClient()
        conversation_id = str(txn.id)

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
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error("Max retries exceeded for transaction %s", transaction_id)
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

    if batch.status in ('PROCESSING', 'COMPLETED', 'FAILED'):
        logger.warning("Batch %s is already %s, skipping", batch_id, batch.status)
        return {'status': 'skipped', 'reason': f'Already {batch.status}'}

    try:
        validate_disbursement_window()
    except RuntimeError as e:
        logger.warning("Batch %s skipped: %s", batch_id, e)
        return {'error': str(e), 'batch_id': batch_id}

    pending = list(
        DisbursementTransaction.objects.filter(
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
    )

    if not pending:
        logger.info("Batch %s: no pending M-PESA transactions", batch_id)
        batch.status = 'COMPLETED'
        batch.save(update_fields=['status'])
        return {'status': 'COMPLETED', 'batch_id': batch_id, 'processed': 0}

    batch.status = 'PROCESSING'
    batch.celery_task_id = self.request.id or ''
    batch.save(update_fields=['status', 'celery_task_id'])

    CHUNK_SIZE = 50
    CHUNK_DELAY = 30
    processed_count = 0
    chunks = [pending[i:i + CHUNK_SIZE] for i in range(0, len(pending), CHUNK_SIZE)]

    for chunk_index, chunk in enumerate(chunks):
        for txn in chunk:
            mpesa_number = txn.farmer.mpesa_number
            try:
                mpesa_number = normalize_mpesa_number(mpesa_number)
            except ValueError:
                txn.status = 'FAILED'
                txn.failure_reason = f'Invalid M-Pesa number: {mpesa_number}'
                txn.failed_at = timezone.now()
                txn.save(update_fields=['status', 'failure_reason', 'failed_at'])
                continue

            send_single_mpesa_disbursement.delay(
                transaction_id=str(txn.id),
                batch_id=str(batch.id),
                phone_number=mpesa_number,
                amount=txn.amount,
                command_id=batch.command_id,
                farmer_name=str(txn.farmer),
            )
            processed_count += 1

        if chunk_index < len(chunks) - 1:
            update_batch_summary.apply_async(
                args=[str(batch.id)],
                countdown=CHUNK_DELAY,
            )

    return {
        'status': 'PROCESSING',
        'batch_id': batch_id,
        'total_pending': len(pending),
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

    batch.total_transactions = total
    batch.successful_count = successful
    batch.failed_count = failed

    all_terminal = all(
        s in ('SUCCESS', 'FAILED', 'CANCELLED')
        for s in transactions.values_list('status', flat=True)
    )
    if all_terminal:
        if failed > 0 and successful == 0:
            batch.status = 'FAILED'
        elif successful > 0 and failed > 0:
            batch.status = 'PARTIALLY_COMPLETED'
        elif successful > 0 and failed == 0:
            batch.status = 'COMPLETED'
        else:
            batch.status = 'COMPLETED'
    elif sent == 0 and all(
        s in ('PENDING', 'CANCELLED') for s in transactions.values_list('status', flat=True)
    ):
        batch.status = 'COMPLETED'

    batch.save(update_fields=[
        'status', 'total_transactions', 'successful_count', 'failed_count',
    ])

    if batch.status in ('COMPLETED', 'PARTIALLY_COMPLETED'):
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

    if batch.status in ('FAILED', 'PARTIALLY_COMPLETED'):
        failed_txns = transactions.filter(status='FAILED')
        for txn in failed_txns:
            if txn.farmer_payment_id:
                FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                    payment_status='FAILED',
                )

    logger.info("Batch %s summary: %s", batch_id, batch.status)


@shared_task
def reconcile_stuck_transactions():
    stuck_time = timezone.now() - timedelta(minutes=10)

    stuck = DisbursementTransaction.objects.filter(
        status__in=['QUEUED', 'SENT'],
        sent_at__lte=stuck_time,
    ).select_related('batch')

    client = MpesaDarajaClient()
    reconciled = 0
    stuck_by_coop: dict[str, list[DisbursementTransaction]] = defaultdict(list)

    for txn in stuck:
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

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

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

        details = '\n'.join(
            f'  • {txn.id} — {txn.recipient_name or "Unknown"} — '
            f'KES {txn.amount} — {txn.status}'
            for txn in txns
        )

        send_mail(
            f'[ACTION REQUIRED] {len(txns)} Stuck Payment(s) Need Attention',
            (
                f'The following {len(txns)} disbursement transaction(s) were found stuck '
                f'in the reconciliation check and have been processed:\n\n'
                f'{details}\n\n'
                f'Please review the disbursement dashboard for full details.'
            ),
            from_email,
            recipient_emails,
            fail_silently=True,
        )

        logger.info(
            'Sent stuck transaction alert for coop %s to %s',
            coop_id, ', '.join(recipient_emails),
        )


@shared_task
def reverse_deductions_on_failure(farmer_id: str, farmer_payment_id: str):
    from apps.deductions.models import Deduction
    from apps.loans.models import LoanRepayment

    deductions = Deduction.objects.filter(
        farmer=farmer_id,
    )
    for ded in deductions:
        if ded.deduction_type == 'LOAN_REPAYMENT':
            LoanRepayment.objects.filter(farmer_payment_id=farmer_payment_id).delete()
    deductions.delete()

    logger.info(
        "Reversed deductions for farmer %s on payment %s",
        farmer_id, farmer_payment_id,
    )
    return {'farmer_id': farmer_id, 'farmer_payment_id': farmer_payment_id}


@shared_task
def send_disbursement_sms(phone_number: str, farmer_name: str, amount: float, farner_payment_id: str = ''):
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
