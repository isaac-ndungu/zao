from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.conftest import CooperativeFactory, FarmerFactory, FarmerPaymentFactory, PaymentCycleFactory
from apps.cooperatives.models import PaymentModel
from apps.payment_engine.models import FarmerPayment, PaymentCycle

pytestmark = pytest.mark.django_db


# =============================================================================
# PaymentCycle.clean()
# =============================================================================


class TestPaymentCycleClean:
    def test_empty_totals_passes(self):
        coop = CooperativeFactory()
        cycle = PaymentCycleFactory(cooperative=coop, totals={})
        cycle.clean()

    def test_totals_with_all_required_keys_passes(self):
        coop = CooperativeFactory()
        cycle = PaymentCycleFactory(
            cooperative=coop,
            totals={
                'total_quantity': 100,
                'total_gross': 4500,
                'total_net': 4300,
                'farmer_count': 1,
            },
        )
        cycle.clean()

    def test_missing_single_key_raises(self):
        coop = CooperativeFactory()
        cycle = PaymentCycleFactory(
            cooperative=coop,
            totals={
                'total_quantity': 100,
                'total_gross': 4500,
                'total_net': 4300,
            },
        )
        with pytest.raises(ValidationError) as exc_info:
            cycle.clean()
        assert 'farmer_count' in str(exc_info.value)

    def test_missing_multiple_keys_raises(self):
        coop = CooperativeFactory()
        cycle = PaymentCycleFactory(
            cooperative=coop,
            totals={'total_quantity': 100},
        )
        with pytest.raises(ValidationError) as exc_info:
            cycle.clean()
        msg = str(exc_info.value)
        assert 'total_gross' in msg
        assert 'total_net' in msg
        assert 'farmer_count' in msg

    def test_extra_keys_with_all_required_pass(self):
        coop = CooperativeFactory()
        cycle = PaymentCycleFactory(
            cooperative=coop,
            totals={
                'total_quantity': 100,
                'total_gross': 4500,
                'total_net': 4300,
                'farmer_count': 1,
                'extra_field': 'ok',
            },
        )
        cycle.clean()

    def test_none_totals_passes(self):
        coop = CooperativeFactory()
        cycle = PaymentCycleFactory(cooperative=coop)
        cycle.totals = None
        cycle.clean()


# =============================================================================
# FarmerPayment.clean() — grade breakdown
# =============================================================================


class TestFarmerPaymentGradeBreakdownFixedPrice:
    def _make(self, grade_breakdown, payment_model=PaymentModel.FIXED_PRICE):
        coop = CooperativeFactory(payment_model=payment_model)
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        return FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            grade_breakdown=grade_breakdown,
        )

    def test_valid_fixed_price_breakdown(self):
        fp = self._make({'A': {'kg': '100.00', 'amount': '4500.00'}})
        fp.clean()

    def test_valid_fixed_price_multiple_grades(self):
        fp = self._make({
            'A': {'kg': '100.00', 'amount': '4500.00'},
            'B': {'kg': '50.00', 'amount': '1800.00'},
        })
        fp.clean()

    def test_empty_breakdown_passes(self):
        fp = self._make({})
        fp.clean()

    def test_fixed_price_missing_kg_key(self):
        fp = self._make({'A': {'amount': '4500.00'}})
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'grade_breakdown' in exc_info.value.message_dict

    def test_fixed_price_missing_amount_key(self):
        fp = self._make({'A': {'kg': '100.00'}})
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'grade_breakdown' in exc_info.value.message_dict

    def test_fixed_price_value_not_dict(self):
        fp = self._make({'A': '100.00'})
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'grade_breakdown' in exc_info.value.message_dict

    def test_breakdown_not_dict_raises(self):
        coop = CooperativeFactory(payment_model=PaymentModel.FIXED_PRICE)
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        fp = FarmerPaymentFactory(
            cycle=cycle, farmer=farmer, cooperative=coop,
            grade_breakdown='not-a-dict',
        )
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'grade_breakdown' in exc_info.value.message_dict


class TestFarmerPaymentGradeBreakdownRevenueShare:
    def _make(self, grade_breakdown):
        coop = CooperativeFactory(payment_model=PaymentModel.REVENUE_SHARE)
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        return FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            grade_breakdown=grade_breakdown,
        )

    def test_valid_revenue_share_numeric(self):
        fp = self._make({'A': 100.0, 'B': 50.0})
        fp.clean()

    def test_valid_revenue_share_integer(self):
        fp = self._make({'A': 100})
        fp.clean()

    def test_valid_revenue_share_float(self):
        fp = self._make({'A': 100.0})
        fp.clean()

    def test_revenue_share_non_numeric_raises(self):
        fp = self._make({'A': '100.00'})
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'grade_breakdown' in exc_info.value.message_dict

    def test_revenue_share_dict_value_raises(self):
        fp = self._make({'A': {'kg': 100}})
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'grade_breakdown' in exc_info.value.message_dict

    def test_empty_breakdown_passes(self):
        fp = self._make({})
        fp.clean()


# =============================================================================
# FarmerPayment.clean() — deductions
# =============================================================================


class TestFarmerPaymentDeductions:
    def _make(self, deductions):
        coop = CooperativeFactory()
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        return FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            deductions=deductions,
        )

    def test_valid_deductions(self):
        fp = self._make({
            'levy': '90.00',
            'monthly_fee': '100.00',
            'loan_repayment': '0.00',
            'input_credit': '10.00',
        })
        fp.clean()

    def test_empty_deductions_passes(self):
        fp = self._make({})
        fp.clean()

    def test_deductions_not_dict_raises(self):
        fp = self._make('not-a-dict')
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'deductions' in exc_info.value.message_dict

    def test_missing_levy_raises(self):
        fp = self._make({
            'monthly_fee': '100.00',
            'loan_repayment': '0.00',
            'input_credit': '10.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'levy' in str(exc_info.value)

    def test_missing_monthly_fee_raises(self):
        fp = self._make({
            'levy': '90.00',
            'loan_repayment': '0.00',
            'input_credit': '10.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'monthly_fee' in str(exc_info.value)

    def test_missing_loan_repayment_raises(self):
        fp = self._make({
            'levy': '90.00',
            'monthly_fee': '100.00',
            'input_credit': '10.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'loan_repayment' in str(exc_info.value)

    def test_missing_input_credit_raises(self):
        fp = self._make({
            'levy': '90.00',
            'monthly_fee': '100.00',
            'loan_repayment': '0.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'input_credit' in str(exc_info.value)

    def test_extra_keys_with_required_pass(self):
        fp = self._make({
            'levy': '90.00',
            'monthly_fee': '100.00',
            'loan_repayment': '0.00',
            'input_credit': '10.00',
            'bonus': '50.00',
        })
        fp.clean()


# =============================================================================
# FarmerPayment.clean() — computation_log
# =============================================================================


class TestFarmerPaymentComputationLog:
    def _make(self, computation_log):
        coop = CooperativeFactory()
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        return FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            computation_log=computation_log,
        )

    def test_valid_computation_log(self):
        fp = self._make({
            'method': 'fixed_price',
            'total_quantity': '100.00',
            'gross_amount': '4500.00',
            'deductions_applied': '200.00',
            'net_amount': '4300.00',
            'withholding_tax': '0.00',
        })
        fp.clean()

    def test_empty_computation_log_passes(self):
        fp = self._make({})
        fp.clean()

    def test_computation_log_not_dict_raises(self):
        fp = self._make('not-a-dict')
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'computation_log' in exc_info.value.message_dict

    def test_missing_method_raises(self):
        fp = self._make({
            'total_quantity': '100.00',
            'gross_amount': '4500.00',
            'deductions_applied': '200.00',
            'net_amount': '4300.00',
            'withholding_tax': '0.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'method' in str(exc_info.value)

    def test_missing_total_quantity_raises(self):
        fp = self._make({
            'method': 'fixed_price',
            'gross_amount': '4500.00',
            'deductions_applied': '200.00',
            'net_amount': '4300.00',
            'withholding_tax': '0.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'total_quantity' in str(exc_info.value)

    def test_missing_gross_amount_raises(self):
        fp = self._make({
            'method': 'fixed_price',
            'total_quantity': '100.00',
            'deductions_applied': '200.00',
            'net_amount': '4300.00',
            'withholding_tax': '0.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'gross_amount' in str(exc_info.value)

    def test_missing_deductions_applied_raises(self):
        fp = self._make({
            'method': 'fixed_price',
            'total_quantity': '100.00',
            'gross_amount': '4500.00',
            'net_amount': '4300.00',
            'withholding_tax': '0.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'deductions_applied' in str(exc_info.value)

    def test_missing_net_amount_raises(self):
        fp = self._make({
            'method': 'fixed_price',
            'total_quantity': '100.00',
            'gross_amount': '4500.00',
            'deductions_applied': '200.00',
            'withholding_tax': '0.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'net_amount' in str(exc_info.value)

    def test_missing_withholding_tax_raises(self):
        fp = self._make({
            'method': 'fixed_price',
            'total_quantity': '100.00',
            'gross_amount': '4500.00',
            'deductions_applied': '200.00',
            'net_amount': '4300.00',
        })
        with pytest.raises(ValidationError) as exc_info:
            fp.clean()
        assert 'withholding_tax' in str(exc_info.value)

    def test_extra_keys_with_required_pass(self):
        fp = self._make({
            'method': 'fixed_price',
            'total_quantity': '100.00',
            'gross_amount': '4500.00',
            'deductions_applied': '200.00',
            'net_amount': '4300.00',
            'withholding_tax': '0.00',
            'computed_at': '2024-01-31',
        })
        fp.clean()


# =============================================================================
# FarmerPayment.clean() — all sub-validators together
# =============================================================================


class TestFarmerPaymentCleanFull:
    def test_all_valid_data_passes(self):
        coop = CooperativeFactory(payment_model=PaymentModel.FIXED_PRICE)
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        fp = FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            grade_breakdown={'A': {'kg': '100.00', 'amount': '4500.00'}},
            deductions={
                'levy': '90.00',
                'monthly_fee': '100.00',
                'loan_repayment': '0.00',
                'input_credit': '10.00',
            },
            computation_log={
                'method': 'fixed_price',
                'total_quantity': '100.00',
                'gross_amount': '4500.00',
                'deductions_applied': '200.00',
                'net_amount': '4300.00',
                'withholding_tax': '0.00',
            },
        )
        fp.clean()

    def test_invalid_grade_breakdown_fails_even_with_valid_deductions(self):
        coop = CooperativeFactory(payment_model=PaymentModel.FIXED_PRICE)
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        fp = FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            grade_breakdown='bad',
            deductions={
                'levy': '90.00',
                'monthly_fee': '100.00',
                'loan_repayment': '0.00',
                'input_credit': '10.00',
            },
            computation_log={
                'method': 'fixed_price',
                'total_quantity': '100.00',
                'gross_amount': '4500.00',
                'deductions_applied': '200.00',
                'net_amount': '4300.00',
                'withholding_tax': '0.00',
            },
        )
        with pytest.raises(ValidationError):
            fp.clean()

    def test_empty_everything_passes(self):
        coop = CooperativeFactory()
        farmer = FarmerFactory(cooperative=coop)
        cycle = PaymentCycleFactory(cooperative=coop)
        fp = FarmerPaymentFactory(
            cycle=cycle,
            farmer=farmer,
            cooperative=coop,
            grade_breakdown={},
            deductions={},
            computation_log={},
        )
        fp.clean()
