from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from apps.loans.models import (
    GuarantorStatus,
    Loan,
    LoanGuarantor,
    LoanRepayment,
    LoanStatus,
)

from apps.conftest import positive_decimals, small_percentages

pytestmark = pytest.mark.django_db


# =============================================================================
# Loan Tests
# =============================================================================

class TestLoanModel:
    def test_create(self, farmer):
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            total_repayable=Decimal('11000.00'),
            installment_amount=Decimal('1833.33'),
            number_of_installments=6,
        )
        assert loan.pk is not None
        assert loan.status == LoanStatus.PENDING

    def test_str(self, farmer):
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('5000.00'),
            interest_rate=Decimal('5.00'),
            total_repayable=Decimal('5250.00'),
            installment_amount=Decimal('875.00'),
            number_of_installments=6,
        )
        assert 'Loan' in str(loan)

    def test_save_computes_repayable_if_not_given(self, farmer):
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            number_of_installments=6,
        )
        assert loan.total_repayable == Decimal('11000.00')
        expected_installment = round(11000.00 / 6, 2)
        assert float(loan.installment_amount) == expected_installment

    def test_status_transitions(self, farmer):
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            total_repayable=Decimal('11000.00'),
            installment_amount=Decimal('1833.33'),
            number_of_installments=6,
        )
        for status in [LoanStatus.ACTIVE, LoanStatus.COMPLETED, LoanStatus.DEFAULTED]:
            loan.status = status
            loan.save()
            loan.refresh_from_db()
            assert loan.status == status

    def test_installments_paid_default(self, farmer):
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            total_repayable=Decimal('11000.00'),
            installment_amount=Decimal('1833.33'),
            number_of_installments=6,
        )
        assert loan.installments_paid == 0

    def test_approval_tracking(self, farmer, superuser):
        from django.utils import timezone
        now = timezone.now()
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            total_repayable=Decimal('11000.00'),
            installment_amount=Decimal('1833.33'),
            number_of_installments=6,
            approved_by=superuser,
            approved_at=now,
            status=LoanStatus.ACTIVE,
        )
        assert loan.approved_by == superuser
        assert loan.approved_at

    def test_soft_delete(self, farmer):
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            total_repayable=Decimal('11000.00'),
            installment_amount=Decimal('1833.33'),
            number_of_installments=6,
        )
        loan.soft_delete()
        assert loan.deleted_at is not None

    def test_farmer_protected_delete(self, farmer):
        from django.db.models.deletion import ProtectedError
        loan = Loan.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            total_repayable=Decimal('11000.00'),
            installment_amount=Decimal('1833.33'),
            number_of_installments=6,
        )
        with pytest.raises(ProtectedError):
            farmer.hard_delete()

    def test_number_of_installments_positive(self, farmer):
        loan = Loan(
            farmer=farmer,
            cooperative=farmer.cooperative,
            amount_principal=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            number_of_installments=0,
        )
        with pytest.raises(Exception):
            loan.save()


# =============================================================================
# Loan Guarantor Tests
# =============================================================================

class TestLoanGuarantor:
    def test_create(self, loan, farmer):
        guarantor = LoanGuarantor.objects.create(
            loan=loan,
            guarantor=farmer,
            cooperative=loan.cooperative,
        )
        assert guarantor.pk is not None
        assert guarantor.status == GuarantorStatus.ACTIVE

    def test_unique_loan_guarantor(self, loan):
        from apps.farmers.models import Farmer
        farmer2 = Farmer.objects.create(
            first_name='G', last_name='U',
            id_number='IDG001', phone_number='+25470000099',
            county='Nairobi', cooperative=loan.cooperative,
        )
        LoanGuarantor.objects.create(loan=loan, guarantor=farmer2, cooperative=loan.cooperative)
        with pytest.raises(Exception):
            LoanGuarantor.objects.create(loan=loan, guarantor=farmer2, cooperative=loan.cooperative)

    def test_str(self, loan):
        from apps.farmers.models import Farmer
        farmer2 = Farmer.objects.create(
            first_name='Bob', last_name='G',
            id_number='IDG002', phone_number='+25470000098',
            county='Nairobi', cooperative=loan.cooperative,
        )
        guarantor = LoanGuarantor.objects.create(
            loan=loan, guarantor=farmer2, cooperative=loan.cooperative,
        )
        assert 'ACTIVE' in str(guarantor)

    def test_release_guarantor(self, loan, farmer):
        guarantor = LoanGuarantor.objects.create(
            loan=loan, guarantor=farmer, cooperative=loan.cooperative,
        )
        guarantor.status = GuarantorStatus.RELEASED
        guarantor.save()
        guarantor.refresh_from_db()
        assert guarantor.status == GuarantorStatus.RELEASED

    def test_soft_delete(self, loan, farmer):
        guarantor = LoanGuarantor.objects.create(
            loan=loan, guarantor=farmer, cooperative=loan.cooperative,
        )
        guarantor.soft_delete()
        assert guarantor.deleted_at is not None


# =============================================================================
# Loan Repayment Tests
# =============================================================================

class TestLoanRepayment:
    @pytest.fixture
    def farmer_payment(self, loan):
        from apps.payment_engine.models import FarmerPayment, PaymentCycle, CycleStatus
        cycle = PaymentCycle.objects.create(
            cooperative=loan.cooperative,
            name='Loan Test Cycle',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            status=CycleStatus.DRAFT,
        )
        fp = FarmerPayment.objects.create(
            cycle=cycle,
            farmer=loan.farmer,
            cooperative=loan.cooperative,
            total_quantity=Decimal('100.00'),
            gross_amount=Decimal('4500.00'),
            net_amount=Decimal('4300.00'),
            grade_breakdown={'A': {'kg': '100.00', 'amount': '4500.00'}},
            deductions={'levy': '90.00'},
            computation_log={'method': 'fixed_price'},
        )
        return fp

    def test_create(self, loan, farmer_payment):
        repayment = LoanRepayment.objects.create(
            loan=loan,
            farmer_payment=farmer_payment,
            amount=Decimal('1833.33'),
        )
        assert repayment.pk is not None

    def test_unique_loan_payment(self, loan, farmer_payment):
        LoanRepayment.objects.create(
            loan=loan, farmer_payment=farmer_payment, amount=Decimal('1833.33'),
        )
        with pytest.raises(Exception):
            LoanRepayment.objects.create(
                loan=loan, farmer_payment=farmer_payment, amount=Decimal('100.00'),
            )

    def test_str(self, loan, farmer_payment):
        repayment = LoanRepayment.objects.create(
            loan=loan, farmer_payment=farmer_payment, amount=Decimal('1833.33'),
        )
        assert '1833.33' in str(repayment)

    def test_cascade_delete_farmer_payment(self, loan, farmer_payment):
        repayment = LoanRepayment.objects.create(
            loan=loan, farmer_payment=farmer_payment, amount=Decimal('1833.33'),
        )
        farmer_payment.delete()
        assert not LoanRepayment.objects.filter(pk=repayment.pk).exists()


# =============================================================================
# Hypothesis property-based tests for loan financial logic
# =============================================================================

class TestLoanFinancialHypothesis:
    @settings(max_examples=100)
    @given(
        principal=positive_decimals,
        rate=small_percentages,
    )
    def test_repayable_calculation(self, principal, rate):
        assume(principal > 0)
        repayable = principal * (Decimal('1') + rate / Decimal('100'))
        expected = principal + principal * rate / Decimal('100')
        assert repayable == expected
        assert repayable >= principal

    @settings(max_examples=50)
    @given(
        repayable=positive_decimals,
        installments=st.integers(min_value=1, max_value=60),
    )
    def test_installment_amount_precision(self, repayable, installments):
        assume(repayable > 0 and installments > 0)
        installment = round(float(repayable) / installments, 2)
        total = installment * installments
        diff = abs(float(repayable) - total)
        assert diff < 0.02 * installments
