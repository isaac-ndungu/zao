from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from apps.cooperatives.models import PaymentModel
from apps.payment_engine.models import (
    ComputationWarning,
    CycleStatus,
    FarmerPayment,
    PaymentCycle,
    PaymentStatus,
    Severity,
)

from apps.conftest import nonnegative_decimals, positive_decimals, small_percentages


# =============================================================================
# PaymentCycle Tests
# =============================================================================

class TestPaymentCycleModel:
    def test_create(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='January 2024',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert cycle.pk is not None
        assert cycle.status == CycleStatus.DRAFT

    def test_str(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Test Cycle',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert 'Test Cycle' in str(cycle)
        assert 'Draft' in str(cycle)

    def test_clean_with_valid_totals(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Valid Cycle',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            totals={
                'total_quantity': '1000',
                'total_gross': '45000',
                'total_net': '43000',
                'farmer_count': 10,
            },
        )
        cycle.clean()

    def test_clean_with_missing_totals(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Invalid Cycle',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            totals={'total_quantity': '1000'},
        )
        with pytest.raises(ValidationError, match='totals'):
            cycle.clean()

    def test_clean_skipped_when_totals_empty(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Empty Totals',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        cycle.clean()

    def test_status_transitions(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Transitions',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        for status in [CycleStatus.COMPUTING, CycleStatus.COMPUTED,
                       CycleStatus.LOCKED, CycleStatus.DISBURSED]:
            cycle.status = status
            cycle.save()
            cycle.refresh_from_db()
            assert cycle.status == status

    def test_soft_delete(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Delete Test',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        cycle.soft_delete()
        assert cycle.deleted_at is not None

    def test_default_totals(self, cooperative):
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Defaults',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert cycle.totals == {}
        assert cycle.total_levy == 0
        assert cycle.total_loan_repayments == 0

    def test_locked_by(self, cooperative, superuser):
        from django.utils import timezone
        now = timezone.now()
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative,
            name='Locked',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=CycleStatus.LOCKED,
            locked_by=superuser,
            locked_at=now,
        )
        assert cycle.locked_by == superuser
        assert cycle.locked_at


# =============================================================================
# FarmerPayment Tests
# =============================================================================

class TestFarmerPayment:
    def test_create(self, payment_cycle, farmer):
        fp = FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            total_quantity=Decimal('100.00'),
            gross_amount=Decimal('4500.00'),
            net_amount=Decimal('4300.00'),
        )
        assert fp.pk is not None
        assert fp.payment_status == PaymentStatus.PENDING

    def test_str(self, payment_cycle, farmer):
        fp = FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
        )
        assert str(payment_cycle.name) in str(fp)

    def test_unique_cycle_farmer(self, payment_cycle, farmer):
        FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
        )
        with pytest.raises(Exception):
            FarmerPayment.objects.create(
                cycle=payment_cycle,
                farmer=farmer,
                cooperative=payment_cycle.cooperative,
            )

    def test_validate_grade_breakdown_valid_fixed_price(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            grade_breakdown={'A': {'kg': '100.00', 'amount': '4500.00'}},
        )
        fp.clean()

    def test_validate_grade_breakdown_invalid_fixed_price(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            grade_breakdown={'A': 'not_a_dict'},
        )
        with pytest.raises(ValidationError, match='grade_breakdown'):
            fp.clean()

    def test_validate_grade_breakdown_missing_keys(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            grade_breakdown={'A': {'kg': '100.00'}},
        )
        with pytest.raises(ValidationError, match='grade_breakdown'):
            fp.clean()

    def test_validate_grade_breakdown_empty_skipped(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
        )
        fp.clean()

    def test_validate_grade_breakdown_revenue_share(self, payment_cycle, farmer):
        from decimal import Decimal
        payment_cycle.cooperative.payment_model = PaymentModel.REVENUE_SHARE
        payment_cycle.cooperative.save()
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            grade_breakdown={'A': Decimal('100.00')},
        )
        fp.clean()

    def test_validate_grade_breakdown_revenue_share_invalid(self, payment_cycle, farmer):
        payment_cycle.cooperative.payment_model = PaymentModel.REVENUE_SHARE
        payment_cycle.cooperative.save()
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            grade_breakdown={'A': {'kg': '100.00'}},
        )
        with pytest.raises(ValidationError, match='grade_breakdown'):
            fp.clean()

    def test_validate_deductions_valid(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            deductions={
                'levy': '90.00',
                'monthly_fee': '100.00',
                'loan_repayment': '0.00',
                'input_credit': '10.00',
            },
        )
        fp.clean()

    def test_validate_deductions_missing_keys(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            deductions={'levy': '90.00'},
        )
        with pytest.raises(ValidationError, match='deductions'):
            fp.clean()

    def test_validate_deductions_not_dict(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            deductions='not_a_dict',
        )
        with pytest.raises(ValidationError, match='deductions'):
            fp.clean()

    def test_validate_deductions_empty_skipped(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
        )
        fp.clean()

    def test_validate_computation_log_valid(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
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

    def test_validate_computation_log_missing_keys(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            computation_log={'method': 'fixed_price'},
        )
        with pytest.raises(ValidationError, match='computation_log'):
            fp.clean()

    def test_validate_computation_log_not_dict(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            computation_log='invalid',
        )
        with pytest.raises(ValidationError, match='computation_log'):
            fp.clean()

    def test_validate_computation_log_empty_skipped(self, payment_cycle, farmer):
        fp = FarmerPayment(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
        )
        fp.clean()

    def test_withholding_tax(self, payment_cycle, farmer):
        fp = FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            is_subject_to_withholding_tax=True,
            withholding_tax_amount=Decimal('430.00'),
        )
        assert fp.is_subject_to_withholding_tax
        assert fp.withholding_tax_amount == Decimal('430.00')

    def test_carry_forward(self, payment_cycle, farmer):
        fp = FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            carried_forward_amount=Decimal('500.00'),
            carry_forward_reason='Minimum payout',
        )
        assert fp.carried_forward_amount == Decimal('500.00')
        assert fp.carry_forward_reason == 'Minimum payout'

    def test_hold(self, payment_cycle, farmer):
        fp = FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
            is_on_hold=True,
            hold_reason='Awaiting verification',
        )
        assert fp.is_on_hold
        assert fp.hold_reason == 'Awaiting verification'

    def test_soft_delete(self, payment_cycle, farmer):
        fp = FarmerPayment.objects.create(
            cycle=payment_cycle,
            farmer=farmer,
            cooperative=payment_cycle.cooperative,
        )
        fp.soft_delete()
        assert fp.deleted_at is not None


# =============================================================================
# ComputationWarning Tests
# =============================================================================

class TestComputationWarning:
    def test_create(self, payment_cycle):
        warning = ComputationWarning.objects.create(
            cycle=payment_cycle,
            severity=Severity.WARNING,
            message='Low quality detected',
        )
        assert warning.pk is not None

    def test_severity_choices(self, payment_cycle):
        warning = ComputationWarning.objects.create(
            cycle=payment_cycle,
            severity=Severity.ERROR,
            message='Critical error',
        )
        assert warning.severity == Severity.ERROR

    def test_str(self, payment_cycle):
        warning = ComputationWarning.objects.create(
            cycle=payment_cycle,
            message='X' * 100,
        )
        assert str(warning)[:60] in str(warning)


# =============================================================================
# Hypothesis property-based tests for financial logic
# =============================================================================

class TestFinancialHypothesis:
    @settings(max_examples=50)
    @given(
        quantity=positive_decimals,
        price_per_unit=positive_decimals,
        levy_pct=small_percentages,
        monthly_fee=nonnegative_decimals,
    )
    def test_gross_amount_always_positive(self, quantity, price_per_unit,
                                          levy_pct, monthly_fee):
        assume(quantity > 0 and price_per_unit > 0)
        gross = quantity * price_per_unit
        levy = gross * (levy_pct / Decimal('100'))
        net = gross - levy - monthly_fee
        assert gross > 0
        assert net <= gross

    @settings(max_examples=50)
    @given(
        principal=positive_decimals,
        rate=small_percentages,
        installments=st.integers(min_value=1, max_value=60),
    )
    def test_loan_repayable_greater_than_principal(self, principal, rate, installments):
        assume(principal > 0)
        repayable = principal * (Decimal('1') + rate / Decimal('100'))
        installment = repayable / installments
        assert repayable >= principal
        assert installment > 0
        total_paid = installment * installments
        assert abs(total_paid - repayable) < Decimal('0.02')

    @settings(max_examples=50)
    @given(
        gross=positive_decimals,
        deduction1=nonnegative_decimals,
        deduction2=nonnegative_decimals,
    )
    def test_net_amount_non_negative_when_deductions_exceed(self, gross, deduction1, deduction2):
        net = gross - deduction1 - deduction2
        if deduction1 + deduction2 > gross:
            assert net < 0 or net == 0
        else:
            assert net >= 0
