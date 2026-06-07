import ipaddress
import json
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .tasks import send_disbursement_sms, update_batch_summary, reverse_deductions_on_failure

from .models import DisbursementTransaction

logger = logging.getLogger(__name__)


def _validate_callback_ip(request) -> bool:
    whitelist = getattr(settings, 'MPESA_CALLBACK_IP_WHITELIST', '')
    if not whitelist:
        return True
    remote_ip = request.META.get('REMOTE_ADDR', '')
    try:
        addr = ipaddress.ip_address(remote_ip)
    except ValueError:
        logger.warning('Invalid callback remote address: %s', remote_ip)
        return False
    for cidr in whitelist.split(','):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            logger.warning('Invalid CIDR in whitelist: %s', cidr)
    logger.warning('Callback from %s rejected — not in whitelist', remote_ip)
    return False


@csrf_exempt
def mpesa_result_callback(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    if not _validate_callback_ip(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error('Daraja callback: invalid JSON — %s', e)
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    result = body.get('Result', body)
    result_code = str(result.get('ResultCode', '-1'))
    result_desc = result.get('ResultDesc', '')
    conversation_id = result.get('ConversationID', '')
    transaction_id = result.get('TransactionID', '')

    logger.info(
        'Daraja callback: ResultCode=%s Desc=%s Conv=%s Txn=%s',
        result_code, result_desc, conversation_id, transaction_id,
    )

    if not conversation_id and not transaction_id:
        logger.warning('Daraja callback: no conversation or transaction ID')
        return JsonResponse({'error': 'Missing IDs'}, status=400)

    params = {}
    result_params = result.get('ResultParameters', {})
    for param in result_params.get('ResultParameter', []):
        if isinstance(param, dict):
            params[param.get('Key')] = param.get('Value')

    txns = DisbursementTransaction.objects.filter(
        conversation_id=conversation_id,
    ) if conversation_id else DisbursementTransaction.objects.none()

    if not txns.exists() and transaction_id:
        txns = DisbursementTransaction.objects.filter(
            transaction_id=transaction_id,
        )

    if not txns.exists():
        logger.warning(
            'Daraja callback: no match for conv=%s txn=%s',
            conversation_id, transaction_id,
        )
        return JsonResponse({'accepted': True, 'note': 'No matching transaction found'})

    txn = txns.first()

    completed_date = params.get('TransactionCompletedDateTime', '')
    amount = params.get('TransactionAmount', '')
    receipt = params.get('TransactionReceipt', '')
    recipient_name = params.get('ReceiverPartyPublicName', '')

    if result_code == '0' or result_code == 0:
        txn.status = 'SUCCESS'
        txn.completed_at = timezone.now()
        if recipient_name:
            txn.recipient_name = recipient_name
        if receipt:
            txn.transaction_id = receipt
        update_fields = ['status', 'completed_at', 'result_code', 'result_desc']

        if txn.farmer_payment_id:
            from apps.payment_engine.models import FarmerPayment
            FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                payment_status='PAID',
            )
    else:
        txn.status = 'FAILED'
        txn.failure_reason = result_desc
        txn.failed_at = timezone.now()
        update_fields = ['status', 'failure_reason', 'failed_at', 'result_code', 'result_desc']

    txn.result_code = result_code
    txn.result_desc = result_desc
    txn.save(update_fields=update_fields)

    update_batch_summary.delay(str(txn.batch_id))

    if txn.status == 'SUCCESS':
        send_disbursement_sms.delay(
            phone_number=txn.recipient_identifier,
            farmer_name=txn.recipient_name or str(txn.farmer),
            amount=float(txn.amount),
            farner_payment_id=str(txn.farmer_payment_id) if txn.farmer_payment_id else '',
        )
    elif txn.farmer_payment_id:
        reverse_deductions_on_failure.delay(
            farmer_id=str(txn.farmer_id),
            farmer_payment_id=str(txn.farmer_payment_id),
        )
        from apps.payment_engine.models import FarmerPayment
        FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
            payment_status='FAILED',
        )

    return JsonResponse({'accepted': True})


@csrf_exempt
def mpesa_timeout_callback(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    if not _validate_callback_ip(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error('Daraja timeout: invalid JSON — %s', e)
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    result = body.get('Result', body)
    conversation_id = result.get('ConversationID', '')
    transaction_id = result.get('TransactionID', '')
    result_desc = result.get('ResultDesc', 'Request cancelled by user')

    logger.warning(
        'Daraja timeout: Conv=%s Txn=%s Desc=%s',
        conversation_id, transaction_id, result_desc,
    )

    txns = DisbursementTransaction.objects.filter(
        conversation_id=conversation_id,
    ) if conversation_id else DisbursementTransaction.objects.none()

    if not txns.exists():
        logger.warning(
            'Daraja timeout: no match for conv=%s', conversation_id,
        )
        return JsonResponse({'accepted': True})

    for txn in txns:
        txn.status = 'FAILED'
        txn.failure_reason = result_desc or 'Request timed out'
        txn.failed_at = timezone.now()
        txn.result_desc = result_desc
        txn.save(update_fields=['status', 'failure_reason', 'failed_at', 'result_desc'])

        if txn.farmer_payment_id:
            from apps.payment_engine.models import FarmerPayment
            FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                payment_status='FAILED',
            )
            reverse_deductions_on_failure.delay(
                farmer_id=str(txn.farmer_id),
                farmer_payment_id=str(txn.farmer_payment_id),
            )

        update_batch_summary.delay(str(txn.batch_id))

    return JsonResponse({'accepted': True})
