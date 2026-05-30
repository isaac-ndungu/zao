import json
import logging
from decimal import Decimal
from urllib.error import URLError
from urllib.request import Request, urlopen
from base64 import b64encode

from django.conf import settings

logger = logging.getLogger(__name__)


class MpesaDarajaClient:
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.passkey = settings.MPESA_PASSKEY
        self.shortcode = settings.MPESA_SHORTCODE
        self.environment = settings.MPESA_ENVIRONMENT or 'sandbox'
        self._base_url = (
            'https://sandbox.safaricom.co.ke'
            if self.environment == 'sandbox'
            else 'https://api.safaricom.co.ke'
        )
        self._token = None

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
        if self._token:
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
                if not self._token:
                    raise RuntimeError(f'OAuth token missing from response: {result}')
                return self._token
        except URLError as e:
            logger.error('OAuth token request failed: %s', e)
            raise

    def _build_security_credential(self) -> str:
        credential = f'{self.shortcode}{self.passkey}'
        return b64encode(credential.encode('utf-8')).decode('utf-8')

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
            'InitiatorName': 'testapi',
            'SecurityCredential': self._build_security_credential(),
            'CommandID': command_id,
            'Amount': int(amount),
            'PartyA': self.shortcode,
            'PartyB': phone_number,
            'Remarks': remarks,
            'QueueTimeOutURL': settings.MPESA_B2C_TIMEOUT_URL,
            'ResultURL': settings.MPESA_B2C_RESULT_URL,
            'Occasion': occasion or remarks,
        }

        logger.info(
            'Initiating B2C: %s to %s amount %s conv %s',
            command_id, phone_number, amount, conversation_id,
        )
        return self._request(
            '/mpesa/b2c/v1/paymentrequest',
            data=payload,
            token=token,
        )

    def query_transaction_status(self, conversation_id: str) -> dict:
        token = self.get_oauth_token()
        payload = {
            'InitiatorName': 'testapi',
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
            'InitiatorName': 'testapi',
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
