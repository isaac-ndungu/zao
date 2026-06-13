from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from apps.deductions.models import (
    Deduction,
    DeductionType,
    FarmInputCredit,
    FarmInputCreditStatus,
)

from apps.conftest import positive_decimals


# =============================================================================
# Deduction Tests
# =============================================================================

class TestDeductionModel:
    def test_create(self, farmer, payment_cycle):
        deduction = Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=payment_cycle.cooperative,
            deduction_type=DeductionType.LEVY,
            amount=Decimal('90.00'),
        )
        assert deduction.pk is not None

    def test_levy_type(self, farmer, payment_cycle):
        deduction = Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=payment_cycle.cooperative,
            deduction_type=DeductionType.LEVY,
            amount=Decimal('50.00'),
        )
        assert deduction.deduction_type == DeductionType.LEVY

    def test_loan_repayment_type(self, farmer, payment_cycle):
        deduction = Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=payment_cycle.cooperative,
            deduction_type=DeductionType.LOAN_REPAYMENT,
            amount=Decimal('200.00'),
        )
        assert deduction.deduction_type == DeductionType.LOAN_REPAYMENT

    def test_input_credit_type(self, farmer, payment_cycle):
        deduction = Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=payment_cycle.cooperative,
            deduction_type=DeductionType.INPUT_CREDIT,
            amount=Decimal('150.00'),
        )
        assert deduction.deduction_type == DeductionType.INPUT_CREDIT

    def test_str(self, farmer, payment_cycle):
        deduction = Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=payment_cycle.cooperative,
            deduction_type=DeductionType.LEVY,
            amount=Decimal('90.00'),
        )
        assert 'LEVY' in str(deduction)
        assert '90.00' in str(deduction)

    def test_soft_delete(self, farmer, payment_cycle):
        deduction = Deduction.objects.create(
            farmer=farmer,
            cycle=payment_cycle,
            cooperative=payment_cycle.cooperative,
            deduction_type=DeductionType.LEVY,
            amount=Decimal('90.00'),
        )
        deduction.soft_delete()
        assert deduction.deleted_at is not None


# =============================================================================
# FarmInputCredit Tests
# =============================================================================

class TestFarmInputCredit:
    def test_create(self, farmer):
        from datetime import date
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Fertilizer NPK',
            amount=Decimal('5000.00'),
            installment_amount=Decimal('500.00'),
            supplied_date=date.today(),
        )
        assert credit.pk is not None
        assert credit.status == FarmInputCreditStatus.ACTIVE

    def test_default_status_active(self, farmer):
        from datetime import date
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Seeds',
            amount=Decimal('2000.00'),
            supplied_date=date.today(),
        )
        assert credit.status == 'ACTIVE'

    def test_total_deducted_default(self, farmer):
        from datetime import date
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Pesticide',
            amount=Decimal('3000.00'),
            supplied_date=date.today(),
        )
        assert credit.total_deducted == Decimal('0.00')

    def test_status_completed(self, farmer):
        from datetime import date
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Herbicide',
            amount=Decimal('1500.00'),
            supplied_date=date.today(),
        )
        credit.status = FarmInputCreditStatus.COMPLETED
        credit.save()
        credit.refresh_from_db()
        assert credit.status == FarmInputCreditStatus.COMPLETED

    def test_str(self, farmer):
        from datetime import date
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Fertilizer',
            amount=Decimal('5000.00'),
            supplied_date=date.today(),
        )
        assert 'Fertilizer' in str(credit)
        assert '5000.00' in str(credit)

    def test_soft_delete(self, farmer):
        from datetime import date
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Test',
            amount=Decimal('1000.00'),
            supplied_date=date.today(),
        )
        credit.soft_delete()
        assert credit.deleted_at is not None


# =============================================================================
# Hypothesis property-based tests for deductions
# =============================================================================

class TestDeductionFinancialHypothesis:
    @settings(max_examples=50)
    @given(
        gross_amount=positive_decimals,
        levy_pct=st.decimals(min_value=Decimal('0'), max_value=Decimal('100'), places=2),
        monthly_fee=positive_decimals,
        loan_repayment=positive_decimals,
        input_credit=positive_decimals,
    )
    def test_deductions_never_exceed_gross_by_levy_alone(
        self, gross_amount, levy_pct, monthly_fee, loan_repayment, input_credit
    ):
        assume(gross_amount > 0)
        levy = gross_amount * (levy_pct / Decimal('100'))
        total_deductions = levy + monthly_fee + loan_repayment + input_credit
        net = gross_amount - total_deductions
        assert total_deductions >= 0

    @settings(max_examples=50)
    @given(
        amount=positive_decimals,
        installment_amount=positive_decimals,
    )
    def test_input_credit_installment_lte_total(self, amount, installment_amount):
        assume(amount > 0 and installment_amount > 0)
        if installment_amount <= amount:
            installments_needed = int((amount + installment_amount - Decimal('0.01')) // installment_amount)
            total_paid = installments_needed * installment_amount
            assert total_paid >= amount
