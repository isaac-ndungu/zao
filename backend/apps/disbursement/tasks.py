import json
import logging
from datetime import timedelta
from decimal import Decimal
from urllib.error import URLError
from urllib.request import Request, urlopen

from celery import shared_task
from decouple import config
from django.utils import timezone

from apps.payment_engine.models import FarmerPayment, PaymentCycle

from .models import DisbursementBatch, DisbursementTransaction
from .utils import normalize_mpesa_number, validate_disbursement_window
from .utils.mpesa import MpesaDarajaClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_single_mpesa_disbursement(
    self,
    transaction_id: str,
    batch_id: str,
    phone_number: str,
    amount: Decimal,
    command_id: str,
    farmer_name: str,
):
    try:
        txn = DisbursementTransaction.objects.select_related('batch').get(id=transaction_id)
    except DisbursementTransaction.DoesNotExist:
        logger.error("Transaction %s not found", transaction_id)
        return {'error': 'Transaction not found'}

    try:
        batch = DisbursementBatch.objects.get(id=batch_id)
    except DisbursementBatch.DoesNotExist:
        logger.error("Batch %s not found", batch_id)
        return {'error': 'Batch not found'}

    try:
        validate_disbursement_window()
    except RuntimeError as e:
        txn.status = 'FAILED'
        txn.failure_reason = str(e)
        txn.failed_at = timezone.now()
        txn.save(update_fields=['status', 'failure_reason', 'failed_at'])
        return {'error': str(e), 'transaction_id': transaction_id}

    normalized_phone = normalize_mpesa_number(phone_number)

    txn.status = 'QUEUED'
    txn.queued_at = timezone.now()
    txn.recipient_identifier = normalized_phone
    txn.recipient_name = farmer_name
    txn.save(update_fields=['status', 'queued_at', 'recipient_identifier', 'recipient_name'])

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
    except Exception as exc:
        logger.error("Daraja B2C failed for txn %s: %s", transaction_id, exc)
        txn.status = 'FAILED'
        txn.failure_reason = str(exc)
        txn.failed_at = timezone.now()
        txn.retry_count += 1
        txn.save(update_fields=[
            'status', 'failure_reason', 'failed_at', 'retry_count',
        ])
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for transaction %s", transaction_id)
        return {'error': str(exc), 'transaction_id': transaction_id}

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


@shared_task(bind=True)
def process_batch_disbursements(self, batch_id: str):
    try:
        batch = DisbursementBatch.objects.select_related('cooperative').get(id=batch_id)
    except DisbursementBatch.DoesNotExist:
        logger.error("Batch %s not found", batch_id)
        return {'error': 'Batch not found'}

    try:
        validate_disbursement_window()
    except RuntimeError as e:
        logger.warning("Batch %s skipped: %s", batch_id, e)
        return {'error': str(e), 'batch_id': batch_id}

    pending = list(
        DisbursementTransaction.objects.filter(
            batch=batch, status='PENDING', payment_method='M_PESA',
        ).select_related('farmer').order_by('created_at')
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

    for txn in stuck:
        if not txn.conversation_id:
            txn.status = 'FAILED'
            txn.failure_reason = 'Stuck without conversation_id'
            txn.failed_at = timezone.now()
            txn.save(update_fields=['status', 'failure_reason', 'failed_at'])
            reconciled += 1
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

        if txn.status == 'SUCCESS':
            send_disbursement_sms.delay(
                phone_number=txn.recipient_identifier,
                farmer_name=txn.recipient_name,
                amount=float(txn.amount),
                farner_payment_id=str(txn.farmer_payment_id) if txn.farmer_payment_id else '',
            )

    logger.info("Reconciled %d stuck transactions", reconciled)
    return {'reconciled': reconciled}


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
    api_key = config('AT_API_KEY', default='')
    username = config('AT_USERNAME', default='')

    if not api_key or not username:
        logger.warning(
            'AT_API_KEY or AT_USERNAME not set. SMS not sent to %s',
            phone_number,
        )
        return

    message = (
        f"Dear {farmer_name}, your payment of KES {amount:,.2f} "
        f"has been sent to your M-Pesa. Thank you for partnering with us."
    )

    payload = json.dumps({
        'username': username,
        'to': phone_number,
        'message': message,
    }).encode('utf-8')

    headers = {
        'ApiKey': api_key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        req = Request(
            'https://api.africastalking.com/version1/messaging',
            data=payload,
            headers=headers,
            method='POST',
        )
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode('utf-8'))
            logger.info('Payment SMS sent to %s: %s', phone_number, body)
    except URLError as e:
        logger.error('Failed to send payment SMS to %s: %s', phone_number, e)
