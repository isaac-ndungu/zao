import json
import logging
import time
from decimal import Decimal
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from base64 import b64encode

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from django.conf import settings

logger = logging.getLogger(__name__)


class MpesaDarajaClient:
    def __init__(self, shortcode: str | None = None):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = shortcode or settings.MPESA_SHORTCODE
        self.initiator_name = settings.MPESA_INITIATOR_NAME
        self.initiator_password = settings.MPESA_INITIATOR_PASSWORD
        self.environment = settings.MPESA_ENVIRONMENT or 'sandbox'
        self._base_url = (
            'https://sandbox.safaricom.co.ke'
            if self.environment == 'sandbox'
            else 'https://api.safaricom.co.ke'
        )
        self._token = None
        self._token_expiry = 0.0
        self._public_key = None

    def _request(self, path: str, data: dict = None, method: str = 'POST', token: str = None) -> dict:
        url = f'{self._base_url}{path}'
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        body = json.dumps(data).encode('utf-8') if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except URLError as e:
            logger.error('Daraja request failed: %s %s — %s', method, url, e)
            raise
        except json.JSONDecodeError as e:
            logger.error('Daraja response parse failed: %s', e)
            raise

    def get_oauth_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token

        auth_str = f'{self.consumer_key}:{self.consumer_secret}'
        encoded = b64encode(auth_str.encode('utf-8')).decode('utf-8')

        headers = {'Authorization': f'Basic {encoded}'}
        url = f'{self._base_url}/oauth/v1/generate?grant_type=client_credentials'
        req = Request(url, headers=headers, method='GET')

        try:
            with urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                self._token = result.get('access_token')
                expires_in = result.get('expires_in', 3600)
                self._token_expiry = time.time() + expires_in - 60  # 60s buffer
                if not self._token:
                    raise RuntimeError(f'OAuth token missing from response: {result}')
                return self._token
        except URLError as e:
            logger.error('OAuth token request failed: %s', e)
            raise

    def _load_public_key(self):
        if self._public_key is not None:
            return self._public_key
        cert_path = Path(settings.MPESA_PUBLIC_CERT_PATH)
        if not cert_path.exists():
            raise RuntimeError(
                f'MPESA public certificate not found at {cert_path}. '
                f'Download from Daraja portal and save to this path, '
                f'or set MPESA_PUBLIC_CERT_PATH in settings.'
            )
        cert_data = cert_path.read_bytes()
        cert = load_pem_x509_certificate(cert_data)
        self._public_key = cert.public_key()
        return self._public_key

    def _build_security_credential(self) -> str:
        public_key = self._load_public_key()
        encrypted = public_key.encrypt(
            self.initiator_password.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return b64encode(encrypted).decode('utf-8')

    def initiate_b2c(
        self,
        amount: Decimal,
        phone_number: str,
        conversation_id: str,
        command_id: str = 'SalaryPayment',
        remarks: str = 'Cooperative payment',
        occasion: str = '',
    ) -> dict:
        token = self.get_oauth_token()

        payload = {
            'OriginatorConversationID': conversation_id,
            'InitiatorName': self.initiator_name,
            'SecurityCredential': self._build_security_credential(),
            'CommandID': command_id,
            'Amount': int(amount),
            'PartyA': self.shortcode,
            'PartyB': phone_number,
            'Remarks': remarks,
            'QueueTimeOutURL': settings.MPESA_B2C_TIMEOUT_URL,
            'ResultURL': settings.MPESA_B2C_RESULT_URL,
            'Occassion': occasion or remarks,
        }

        logger.info(
            'Initiating B2C: %s to %s amount %s conv %s',
            command_id, phone_number, amount, conversation_id,
        )
        return self._request(
            '/mpesa/b2c/v3/paymentrequest/',
            data=payload,
            token=token,
        )

    def query_transaction_status(self, conversation_id: str) -> dict:
        token = self.get_oauth_token()
        payload = {
            'InitiatorName': self.initiator_name,
            'SecurityCredential': self._build_security_credential(),
            'CommandID': 'TransactionStatusQuery',
            'PartyA': self.shortcode,
            'IdentifierType': '4',
            'Remarks': 'Status query',
            'Occasion': '',
            'QueueTimeOutURL': settings.MPESA_B2C_TIMEOUT_URL,
            'ResultURL': settings.MPESA_B2C_RESULT_URL,
            'TransactionID': conversation_id,
        }
        return self._request(
            '/mpesa/transactionstatus/v1/query',
            data=payload,
            token=token,
        )

    def query_account_balance(self) -> dict:
        token = self.get_oauth_token()
        payload = {
            'InitiatorName': self.initiator_name,
            'SecurityCredential': self._build_security_credential(),
            'CommandID': 'AccountBalance',
            'PartyA': self.shortcode,
            'IdentifierType': '4',
            'Remarks': 'Balance query',
            'QueueTimeOutURL': settings.MPESA_B2C_TIMEOUT_URL,
            'ResultURL': settings.MPESA_B2C_RESULT_URL,
        }
        return self._request(
            '/mpesa/accountbalance/v1/query',
            data=payload,
            token=token,
        )

    def get_account_balance(self) -> dict:
        response = self.query_account_balance()
        result_code = response.get('ResultCode', '-1')
        result_desc = response.get('ResultDesc', '')
        if result_code != '0':
            raise RuntimeError(f"Account balance query failed: {result_desc}")
        params = response.get('ResultParameters', {})
        return {
            'balance': Decimal(params.get('Balance', 0)),
            'available_balance': Decimal(params.get('AvailableBalance', 0)),
            'min_req_time': params.get('MinReqTime', ''),
        }

    def check_balance(self, required_amount: Decimal) -> tuple[bool, Decimal]:
        info = self.get_account_balance()
        available = info['available_balance']
        sufficient = available >= required_amount
        if not sufficient:
            logger.warning(
                'Insufficient float balance: required=%s available=%s',
                required_amount, available,
            )
        return sufficient, available
