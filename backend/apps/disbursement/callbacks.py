import base64
import hmac
import ipaddress
import json
import logging
from hashlib import sha256
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .tasks import send_disbursement_sms, update_batch_summary, reverse_deductions_on_failure

from .models import DisbursementTransaction

logger = logging.getLogger(__name__)


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """Verify M-Pesa callback signature using Safaricom's public certificate."""
    if not signature_header:
        return False
    cert_path = getattr(settings, 'MPESA_PUBLIC_CERT_PATH', None)
    if not cert_path or not Path(cert_path).exists():
        logger.warning('M-Pesa public cert not available — skipping signature verification')
        return True
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        cert = x509.load_pem_x509_certificate(Path(cert_path).read_bytes())
        public_key = cert.public_key()
        signature = base64.b64decode(signature_header)
        public_key.verify(
            signature,
            body,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as exc:
        logger.error('M-Pesa signature verification failed: %s', exc)
        return False


def _validate_payload(payload: dict) -> list[str]:
    """Validate callback payload structure and return any error messages."""
    errors: list[str] = []
    result = payload.get('Result', payload)
    if not isinstance(result, dict):
        errors.append('Result must be an object')
        return errors
    result_code = result.get('ResultCode')
    if result_code is not None and not isinstance(result_code, (int, str)):
        errors.append('ResultCode must be an integer or string')
    result_desc = result.get('ResultDesc')
    if result_desc is not None and not isinstance(result_desc, str):
        errors.append('ResultDesc must be a string')
    result_params = result.get('ResultParameters', {})
    if result_params and not isinstance(result_params, dict):
        errors.append('ResultParameters must be an object')
    return errors


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

    raw_body = request.body
    sig_header = request.META.get('HTTP_X_SIGNATURE', '')

    if not _verify_signature(raw_body, sig_header):
        logger.warning('Daraja callback: invalid signature')
        return JsonResponse({'error': 'Invalid signature'}, status=403)

    hmac_secret = getattr(settings, 'MPESA_CALLBACK_HMAC_SECRET', '')
    if hmac_secret:
        expected_sig = hmac.new(
            hmac_secret.encode(), raw_body, sha256,
        ).hexdigest()
        given_sig = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
        if not hmac.compare_digest(expected_sig, given_sig):
            logger.warning('Daraja callback: HMAC signature mismatch')
            return JsonResponse({'error': 'Invalid HMAC'}, status=403)

    try:
        body = json.loads(raw_body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error('Daraja callback: invalid JSON — %s', e)
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    validation_errors = _validate_payload(body)
    if validation_errors:
        logger.error('Daraja callback: payload validation failed — %s', validation_errors)
        return JsonResponse({'error': 'Invalid payload', 'details': validation_errors}, status=400)

    result = body.get('Result', body)
    result_code_raw = result.get('ResultCode', -1)
    result_code = str(result_code_raw) if result_code_raw is not None else '-1'
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

    if result_code == '0':
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
            try:
                from apps.notifications.models import Notification, NotificationChannel, NotificationType
                from apps.farmers.models import Farmer
                farmer = txn.farmer
                if farmer:
                    Notification.objects.create(
                        cooperative=txn.batch.cooperative,
                        recipient=farmer,
                        channel=NotificationChannel.IN_APP,
                        notification_type=NotificationType.PAYMENT_SENT,
                        content=f'Payment of KES {float(txn.amount):,.2f} has been sent to your M-Pesa.',
                        status='PENDING',
                    )
            except Exception:
                logger.warning('Failed to create PAYMENT_SENT notification for farmer %s', txn.farmer_id)
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
        try:
            from apps.notifications.models import Notification, NotificationChannel, NotificationType
            from apps.farmers.models import Farmer
            farmer = txn.farmer
            if farmer:
                Notification.objects.create(
                    cooperative=txn.batch.cooperative,
                    recipient=farmer,
                    channel=NotificationChannel.IN_APP,
                    notification_type=NotificationType.PAYMENT_FAILED,
                    content=f'Your payment of KES {float(txn.amount):,.2f} has failed. Please contact your cooperative.',
                    status='PENDING',
                )
        except Exception:
            logger.warning('Failed to create PAYMENT_FAILED notification for farmer %s', txn.farmer_id)

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
