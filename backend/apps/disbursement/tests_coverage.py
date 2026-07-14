import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.test import RequestFactory

from apps.conftest import (
    CooperativeFactory,
    DisbursementBatchFactory,
    DisbursementTransactionFactory,
    FarmerFactory,
    FarmerPaymentFactory,
    LoanFactory,
    LoanRepaymentFactory,
    DeductionFactory,
    PaymentCycleFactory,
)
from apps.disbursement.callbacks import (
    _validate_payload,
    _validate_callback_ip,
    mpesa_result_callback,
    mpesa_timeout_callback,
)
from apps.disbursement.models import DisbursementBatch, DisbursementTransaction
from apps.disbursement.tasks import reverse_deductions_on_failure, send_disbursement_sms
from apps.disbursement.utils import normalize_mpesa_number, validate_disbursement_window, compute_withholding_tax
from apps.loans.models import Loan, LoanRepayment

pytestmark = pytest.mark.django_db


class TestValidatePayload:
    def test_valid_payload_returns_no_errors(self):
        payload = {
            'Result': {
                'ResultCode': 0,
                'ResultDesc': 'Success',
                'ResultParameters': {'ResultParameter': []},
            }
        }
        assert _validate_payload(payload) == []

    def test_result_not_dict_returns_error(self):
        payload = {'Result': 'invalid'}
        errors = _validate_payload(payload)
        assert 'Result must be an object' in errors

    def test_result_code_wrong_type_returns_error(self):
        payload = {'Result': {'ResultCode': [1, 2, 3]}}
        errors = _validate_payload(payload)
        assert 'ResultCode must be an integer or string' in errors

    def test_result_desc_wrong_type_returns_error(self):
        payload = {'Result': {'ResultDesc': 123}}
        errors = _validate_payload(payload)
        assert 'ResultDesc must be a string' in errors

    def test_result_parameters_not_dict_returns_error(self):
        payload = {'Result': {'ResultParameters': 'bad'}}
        errors = _validate_payload(payload)
        assert 'ResultParameters must be an object' in errors


class TestValidateCallbackIp:
    def test_empty_whitelist_returns_true(self, settings):
        settings.MPESA_CALLBACK_IP_WHITELIST = ''
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='10.0.0.1')
        assert _validate_callback_ip(request) is True

    def test_ip_in_whitelist_returns_true(self, settings):
        settings.MPESA_CALLBACK_IP_WHITELIST = '10.0.0.0/8,192.168.0.0/16'
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='10.1.2.3')
        assert _validate_callback_ip(request) is True

    def test_ip_not_in_whitelist_returns_false(self, settings):
        settings.MPESA_CALLBACK_IP_WHITELIST = '10.0.0.0/8'
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='192.168.1.1')
        assert _validate_callback_ip(request) is False

    def test_invalid_ip_returns_false(self, settings):
        settings.MPESA_CALLBACK_IP_WHITELIST = '10.0.0.0/8'
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='not-an-ip')
        assert _validate_callback_ip(request) is False


class TestMpesaResultCallback:
    def _make_request(self, method='POST', body=None, **meta):
        rf = RequestFactory()
        content = json.dumps(body) if body is not None else ''
        if method == 'POST':
            request = rf.post('/callbacks/mpesa/', data=content, content_type='application/json', **meta)
        else:
            request = rf.get('/callbacks/mpesa/', **meta)
        return request

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks._verify_signature', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.send_disbursement_sms')
    def test_get_returns_405(self, mock_sms, mock_batch, mock_sig, mock_ip):
        request = self._make_request(method='GET')
        response = mpesa_result_callback(request)
        assert response.status_code == 405

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks._verify_signature', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.send_disbursement_sms')
    def test_invalid_json_returns_400(self, mock_sms, mock_batch, mock_sig, mock_ip):
        rf = RequestFactory()
        request = rf.post(
            '/callbacks/mpesa/',
            data='not json {{{',
            content_type='application/json',
        )
        response = mpesa_result_callback(request)
        assert response.status_code == 400

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks._verify_signature', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.send_disbursement_sms')
    def test_missing_conversation_and_transaction_id_returns_400(
        self, mock_sms, mock_batch, mock_sig, mock_ip
    ):
        body = {
            'Result': {
                'ResultCode': 0,
                'ResultDesc': 'Ok',
                'ConversationID': '',
                'TransactionID': '',
            }
        }
        request = self._make_request(body=body)
        response = mpesa_result_callback(request)
        assert response.status_code == 400

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks._verify_signature', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.send_disbursement_sms')
    def test_no_matching_transaction_returns_accepted(
        self, mock_sms, mock_batch, mock_sig, mock_ip
    ):
        body = {
            'Result': {
                'ResultCode': 0,
                'ResultDesc': 'Ok',
                'ConversationID': 'conv-99999',
                'TransactionID': 'txn-99999',
            }
        }
        request = self._make_request(body=body)
        response = mpesa_result_callback(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['accepted'] is True

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks._verify_signature', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.send_disbursement_sms')
    def test_matching_transaction_result_code_0_marks_success(
        self, mock_sms, mock_batch, mock_sig, mock_ip
    ):
        txn = DisbursementTransactionFactory(conversation_id='conv-ok-1')
        body = {
            'Result': {
                'ResultCode': 0,
                'ResultDesc': 'The service request is processed successfully.',
                'ConversationID': 'conv-ok-1',
                'TransactionID': 'QHK71G4YS0',
                'ResultParameters': {
                    'ResultParameter': [
                        {'Key': 'TransactionReceipt', 'Value': 'QHK71G4YS0'},
                        {'Key': 'TransactionAmount', 'Value': str(txn.amount)},
                        {'Key': 'ReceiverPartyPublicName', 'Value': 'Test Farmer'},
                    ]
                },
            }
        }
        request = self._make_request(body=body)
        response = mpesa_result_callback(request)
        assert response.status_code == 200
        txn.refresh_from_db()
        assert txn.status == 'SUCCESS'
        mock_batch.delay.assert_called_once_with(str(txn.batch_id))
        mock_sms.delay.assert_called_once()

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks._verify_signature', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.send_disbursement_sms')
    def test_matching_transaction_nonzero_result_code_marks_failed(
        self, mock_sms, mock_batch, mock_sig, mock_ip
    ):
        txn = DisbursementTransactionFactory(conversation_id='conv-fail-1')
        body = {
            'Result': {
                'ResultCode': 1,
                'ResultDesc': 'Insufficient balance.',
                'ConversationID': 'conv-fail-1',
                'TransactionID': '',
            }
        }
        request = self._make_request(body=body)
        response = mpesa_result_callback(request)
        assert response.status_code == 200
        txn.refresh_from_db()
        assert txn.status == 'FAILED'
        assert txn.failure_reason == 'Insufficient balance.'
        mock_batch.delay.assert_called_once_with(str(txn.batch_id))
        mock_sms.delay.assert_not_called()


class TestMpesaTimeoutCallback:
    def _make_request(self, method='POST', body=None):
        rf = RequestFactory()
        content = json.dumps(body) if body is not None else ''
        if method == 'POST':
            return rf.post('/callbacks/mpesa/timeout/', data=content, content_type='application/json')
        return rf.get('/callbacks/mpesa/timeout/')

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.reverse_deductions_on_failure')
    def test_get_returns_405(self, mock_rev, mock_batch, mock_ip):
        request = self._make_request(method='GET')
        response = mpesa_timeout_callback(request)
        assert response.status_code == 405

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.reverse_deductions_on_failure')
    def test_invalid_json_returns_400(self, mock_rev, mock_batch, mock_ip):
        rf = RequestFactory()
        request = rf.post(
            '/callbacks/mpesa/timeout/',
            data='{{{bad',
            content_type='application/json',
        )
        response = mpesa_timeout_callback(request)
        assert response.status_code == 400

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.reverse_deductions_on_failure')
    def test_no_matching_transaction_returns_accepted(self, mock_rev, mock_batch, mock_ip):
        body = {
            'Result': {
                'ConversationID': 'no-match',
                'TransactionID': 'no-match',
                'ResultDesc': 'Timed out',
            }
        }
        request = self._make_request(body=body)
        response = mpesa_timeout_callback(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['accepted'] is True

    @patch('apps.disbursement.callbacks._validate_callback_ip', return_value=True)
    @patch('apps.disbursement.callbacks.update_batch_summary')
    @patch('apps.disbursement.callbacks.reverse_deductions_on_failure')
    def test_matching_transaction_marks_failed(self, mock_rev, mock_batch, mock_ip):
        txn = DisbursementTransactionFactory(conversation_id='conv-timeout-1')
        body = {
            'Result': {
                'ConversationID': 'conv-timeout-1',
                'TransactionID': 'txn-timeout',
                'ResultDesc': 'Request cancelled by user',
            }
        }
        request = self._make_request(body=body)
        response = mpesa_timeout_callback(request)
        assert response.status_code == 200
        txn.refresh_from_db()
        assert txn.status == 'FAILED'
        assert txn.failure_reason == 'Request cancelled by user'
        mock_batch.delay.assert_called_with(str(txn.batch_id))


class TestReverseDeductionsOnFailure:
    def test_deletes_deductions(self):
        farmer = FarmerFactory()
        cycle = PaymentCycleFactory()
        DeductionFactory(farmer=farmer, cycle=cycle, deduction_type='LEVY', amount=Decimal('90.00'))
        DeductionFactory(farmer=farmer, cycle=cycle, deduction_type='INPUT_CREDIT', amount=Decimal('50.00'))
        farmer_payment = FarmerPaymentFactory(farmer=farmer, cycle=cycle)
        result = reverse_deductions_on_failure(str(farmer.id), str(farmer_payment.id))
        from apps.deductions.models import Deduction
        assert Deduction.objects.filter(farmer=farmer).count() == 0
        assert result['farmer_id'] == str(farmer.id)

    def test_reverses_loan_repayment(self):
        farmer = FarmerFactory()
        cycle = PaymentCycleFactory()
        loan = LoanFactory(farmer=farmer, installments_paid=3)
        farmer_payment = FarmerPaymentFactory(farmer=farmer, cycle=cycle)
        LoanRepaymentFactory(loan=loan, farmer_payment=farmer_payment)
        DeductionFactory(
            farmer=farmer, cycle=cycle, deduction_type='LOAN_REPAYMENT', amount=Decimal('1833.33'),
        )
        reverse_deductions_on_failure(str(farmer.id), str(farmer_payment.id))
        loan.refresh_from_db()
        assert loan.installments_paid == 2
        assert loan.status == 'ACTIVE'
        assert LoanRepayment.objects.filter(farmer_payment=farmer_payment).count() == 0

    def test_handles_no_deductions(self):
        farmer = FarmerFactory()
        farmer_payment = FarmerPaymentFactory(farmer=farmer)
        result = reverse_deductions_on_failure(str(farmer.id), str(farmer_payment.id))
        assert result['farmer_id'] == str(farmer.id)
        assert result['farmer_payment_id'] == str(farmer_payment.id)


class TestSendDisbursementSms:
    @patch('apps.notifications.utils.send_sms')
    def test_calls_send_sms_with_correct_args(self, mock_send_sms):
        mock_send_sms.return_value = {'success': True}
        send_disbursement_sms('+254712345678', 'John Doe', 4300.00)
        mock_send_sms.assert_called_once()
        args = mock_send_sms.call_args
        assert args[0][0] == '+254712345678'
        assert 'John Doe' in args[0][1]
        assert '4,300.00' in args[0][1]


class TestNormalizeMpesaNumber:
    def test_plus_254_prefix(self):
        assert normalize_mpesa_number('+254712345678') == '254712345678'

    def test_zero_prefix(self):
        assert normalize_mpesa_number('0712345678') == '254712345678'

    def test_bare_254_prefix(self):
        assert normalize_mpesa_number('254712345678') == '254712345678'

    def test_with_spaces(self):
        assert normalize_mpesa_number('0712 345 678') == '254712345678'

    def test_invalid_number_raises(self):
        with pytest.raises(ValueError, match='Invalid Kenyan phone number'):
            normalize_mpesa_number('12345')

    def test_letters_raises(self):
        with pytest.raises(ValueError, match='Invalid Kenyan phone number'):
            normalize_mpesa_number('abcdefg')


class TestValidateDisbursementWindow:
    @patch('apps.disbursement.utils.settings')
    def test_during_blackout_raises(self, mock_settings):
        mock_settings.MPESA_DISBURSEMENT_BLACKOUT_START = '01:00'
        mock_settings.MPESA_DISBURSEMENT_BLACKOUT_END = '04:00'
        with patch('apps.disbursement.utils.datetime') as mock_dt:
            mock_dt.now.return_value.time.return_value = __import__('datetime').time(2, 30)
            mock_dt.side_effect = lambda *a, **k: __import__('datetime').datetime(*a, **k)
            with pytest.raises(RuntimeError, match='unavailable'):
                validate_disbursement_window()

    @patch('apps.disbursement.utils.settings')
    def test_outside_blackout_passes(self, mock_settings):
        mock_settings.MPESA_DISBURSEMENT_BLACKOUT_START = '01:00'
        mock_settings.MPESA_DISBURSEMENT_BLACKOUT_END = '04:00'
        with patch('apps.disbursement.utils.datetime') as mock_dt:
            mock_dt.now.return_value.time.return_value = __import__('datetime').time(10, 0)
            mock_dt.side_effect = lambda *a, **k: __import__('datetime').datetime(*a, **k)
            validate_disbursement_window()

    @patch('apps.disbursement.utils.settings')
    def test_invalid_settings_defaults_to_1_4(self, mock_settings):
        mock_settings.MPESA_DISBURSEMENT_BLACKOUT_START = None
        mock_settings.MPESA_DISBURSEMENT_BLACKOUT_END = None
        with patch('apps.disbursement.utils.datetime') as mock_dt:
            mock_dt.now.return_value.time.return_value = __import__('datetime').time(2, 0)
            mock_dt.side_effect = lambda *a, **k: __import__('datetime').datetime(*a, **k)
            with pytest.raises(RuntimeError, match='unavailable'):
                validate_disbursement_window()


class TestComputeWithholdingTax:
    def test_below_threshold_returns_zero_tax(self):
        farmer = FarmerFactory()
        cycle = PaymentCycleFactory()
        FarmerPaymentFactory(farmer=farmer, cycle=cycle, net_amount=Decimal('20000.00'))
        tax, has_tax = compute_withholding_tax(str(farmer.id), str(cycle.id))
        assert tax == 0
        assert has_tax is False

    def test_above_threshold_returns_5_percent_of_excess(self):
        farmer = FarmerFactory()
        cycle = PaymentCycleFactory()
        FarmerPaymentFactory(farmer=farmer, cycle=cycle, net_amount=Decimal('30000.00'))
        tax, has_tax = compute_withholding_tax(str(farmer.id), str(cycle.id))
        expected = round((30000.0 - 24000.0) * 0.05, 2)
        assert tax == expected
        assert has_tax is True
