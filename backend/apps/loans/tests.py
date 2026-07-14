from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from rest_framework import status

from apps.base.constants import UserRole
from apps.conftest import positive_decimals, small_percentages
from apps.farmers.models import Farmer
from apps.loans.models import GuarantorStatus, Loan, LoanGuarantor, LoanRepayment, LoanStatus

pytestmark = pytest.mark.django_db


# =============================================================================
# Loan Model Tests
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
        for status_val in [LoanStatus.ACTIVE, LoanStatus.COMPLETED, LoanStatus.DEFAULTED]:
            loan.status = status_val
            loan.save()
            loan.refresh_from_db()
            assert loan.status == status_val

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
# Loan Guarantor Model Tests
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
        farmer2 = Farmer.objects.create(
            first_name='G', last_name='U',
            id_number='IDG001', phone_number='+25470000099',
            county='Nairobi', cooperative=loan.cooperative,
        )
        LoanGuarantor.objects.create(loan=loan, guarantor=farmer2, cooperative=loan.cooperative)
        with pytest.raises(Exception):
            LoanGuarantor.objects.create(loan=loan, guarantor=farmer2, cooperative=loan.cooperative)

    def test_str(self, loan):
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
# Loan Repayment Model Tests
# =============================================================================

class TestLoanRepayment:
    @pytest.fixture
    def farmer_payment(self, loan):
        from apps.payment_engine.models import PaymentCycle, CycleStatus, FarmerPayment
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


from django.contrib.auth import get_user_model
User = get_user_model()


@pytest.fixture
def accountant_api_client(db, cooperative):
    """API client authenticated as an accountant (needed for loan create/mutations)."""
    from rest_framework.test import APIClient
    user = User.objects.create_user(
        email='acct@loans.com', phone_number='+25470000999',
        first_name='Acct', last_name='Loan',
        password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def manager_api_client(db, cooperative):
    """API client authenticated as a manager."""
    from rest_framework.test import APIClient
    user = User.objects.create_user(
        email='mgr@loans.com', phone_number='+25470000888',
        first_name='Mgr', last_name='Loan',
        password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def coop_loan(db, cooperative):
    """A loan belonging to the cooperative fixture (not a separate SubFactory)."""
    from decimal import Decimal
    from apps.farmers.models import Farmer
    farmer = Farmer.objects.create(
        first_name='Coop', last_name='Farmer',
        id_number='IDCOOP001', phone_number='+25470000001',
        county='Nairobi', cooperative=cooperative,
    )
    return Loan.objects.create(
        farmer=farmer, cooperative=cooperative,
        amount_principal=Decimal('10000.00'), interest_rate=Decimal('10.00'),
        total_repayable=Decimal('11000.00'), installment_amount=Decimal('1833.33'),
        number_of_installments=6, status='PENDING',
    )


# =============================================================================
# Loan API Endpoint Tests
# =============================================================================

class TestLoanAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/loans/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, loan):
        resp = api_client.get('/api/loans/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) >= 1

    def test_retrieve(self, api_client, loan):
        resp = api_client.get(f'/api/loans/{loan.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(loan.id)

    def test_create(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/loans/', {
            'farmer': str(farmer.id),
            'amount_principal': '20000.00',
            'interest_rate': '10.00',
            'number_of_installments': 12,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data['amount_principal'] == '20000.00'
        assert data['interest_rate'] == '10.00'
        assert data['number_of_installments'] == 12
        # Verify the loan was created with PENDING status
        from apps.loans.models import Loan
        loan = Loan.objects.get(farmer=farmer)
        assert loan.status == 'PENDING'

    def test_create_negative_principal(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/loans/', {
            'farmer': str(farmer.id),
            'amount_principal': '-100.00',
            'interest_rate': '10.00',
            'number_of_installments': 6,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_negative_interest(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/loans/', {
            'farmer': str(farmer.id),
            'amount_principal': '10000.00',
            'interest_rate': '-5.00',
            'number_of_installments': 6,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_zero_installments(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/loans/', {
            'farmer': str(farmer.id),
            'amount_principal': '10000.00',
            'interest_rate': '10.00',
            'number_of_installments': 0,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_permission_admin_denied(self, api_client, farmer):
        resp = api_client.post('/api/loans/', {
            'farmer': str(farmer.id),
            'amount_principal': '10000.00',
            'interest_rate': '10.00',
            'number_of_installments': 6,
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, api_client, loan):
        resp = api_client.patch(f'/api/loans/{loan.id}/', {'notes': 'Updated notes'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        loan.refresh_from_db()
        assert 'Updated notes' in loan.notes

    def test_delete(self, api_client, loan):
        resp = api_client.delete(f'/api/loans/{loan.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_by_farmer(self, api_client, loan):
        resp = api_client.get(f'/api/loans/?farmer={loan.farmer_id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_status(self, api_client, loan):
        resp = api_client.get(f'/api/loans/?status=PENDING')
        assert resp.status_code == status.HTTP_200_OK


class TestLoanApprove:
    def test_approve_pending_loan_with_guarantor(self, manager_api_client, coop_loan):
        guarantor = Farmer.objects.create(
            first_name='Guar', last_name='Antor',
            id_number='IDG003', phone_number='+25470000097',
            county='Nairobi', cooperative=coop_loan.cooperative,
        )
        LoanGuarantor.objects.create(loan=coop_loan, guarantor=guarantor, cooperative=coop_loan.cooperative)
        resp = manager_api_client.post(f'/api/loans/{coop_loan.id}/approve/', format='json')
        assert resp.status_code == status.HTTP_200_OK
        coop_loan.refresh_from_db()
        assert coop_loan.status == 'ACTIVE'

    def test_approve_pending_loan_no_guarantor(self, manager_api_client, coop_loan):
        resp = manager_api_client.post(f'/api/loans/{coop_loan.id}/approve/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_non_pending_loan(self, manager_api_client, coop_loan):
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        resp = manager_api_client.post(f'/api/loans/{coop_loan.id}/approve/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_permission_farmer_denied(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        farmer_user = User.objects.create_user(
            email='farmer@test.com', phone_number='+25470000222',
            first_name='Farm', last_name='Test',
            password='testpass123', role=UserRole.FARMER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        resp = client.post(f'/api/loans/{coop_loan.id}/approve/', format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestLoanDisburse:
    def test_disburse_active_loan(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct_disburse@test.com', phone_number='+25470000333',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/disburse/', format='json')
        assert resp.status_code == status.HTTP_200_OK
        coop_loan.refresh_from_db()
        assert coop_loan.disbursed_at is not None

    def test_disburse_non_active_loan(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct2@test.com', phone_number='+25470000444',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/disburse/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Only ACTIVE loans' in resp.json()['detail']

    def test_disburse_already_disbursed(self, cooperative, coop_loan):
        from django.utils import timezone
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct3@test.com', phone_number='+25470000555',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.disbursed_at = timezone.now()
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/disburse/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already been disbursed' in resp.json()['detail']

    def test_disburse_permission_manager_denied(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr_dis@test.com', phone_number='+25470000666',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post(f'/api/loans/{coop_loan.id}/disburse/', format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestLoanGuarantorActions:
    def test_add_guarantor(self, accountant_api_client, coop_loan):
        other_farmer = Farmer.objects.create(
            first_name='Other', last_name='Farmer',
            id_number='IDG005', phone_number='+25470000095',
            county='Nairobi', cooperative=coop_loan.cooperative,
        )
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/add_guarantor/',
                                          {'guarantor_id': str(other_farmer.id)}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert coop_loan.guarantors.count() == 1

    def test_add_guarantor_duplicate(self, accountant_api_client, coop_loan):
        existing_guarantor = Farmer.objects.create(
            first_name='Dup', last_name='Guarantor',
            id_number='IDG007', phone_number='+25470000096',
            county='Nairobi', cooperative=coop_loan.cooperative,
        )
        LoanGuarantor.objects.create(loan=coop_loan, guarantor=existing_guarantor, cooperative=coop_loan.cooperative)
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/add_guarantor/',
                                          {'guarantor_id': str(existing_guarantor.id)}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_guarantor_self(self, accountant_api_client, coop_loan):
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/add_guarantor/',
                                          {'guarantor_id': str(coop_loan.farmer_id)}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_guarantor_nonexistent_farmer(self, accountant_api_client, coop_loan):
        from uuid import uuid4
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/add_guarantor/',
                                          {'guarantor_id': str(uuid4())}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_guarantor(self, accountant_api_client, coop_loan):
        g = Farmer.objects.create(
            first_name='Remove', last_name='Guarantor',
            id_number='IDG008', phone_number='+25470000097',
            county='Nairobi', cooperative=coop_loan.cooperative,
        )
        LoanGuarantor.objects.create(loan=coop_loan, guarantor=g, cooperative=coop_loan.cooperative)
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/remove_guarantor/',
                                          {'guarantor_id': str(g.id)}, format='json')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert coop_loan.guarantors.count() == 0

    def test_remove_guarantor_when_not_pending(self, accountant_api_client, coop_loan):
        g = Farmer.objects.create(
            first_name='NotPend', last_name='Guarantor',
            id_number='IDG009', phone_number='+25470000098',
            county='Nairobi', cooperative=coop_loan.cooperative,
        )
        LoanGuarantor.objects.create(loan=coop_loan, guarantor=g, cooperative=coop_loan.cooperative)
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/remove_guarantor/',
                                          {'guarantor_id': str(g.id)}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_guarantor_not_found(self, accountant_api_client, coop_loan):
        from uuid import uuid4
        resp = accountant_api_client.post(f'/api/loans/{coop_loan.id}/remove_guarantor/',
                                          {'guarantor_id': str(uuid4())}, format='json')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_add_guarantor_permission_admin_denied(self, api_client, coop_loan):
        other_farmer = Farmer.objects.create(
            first_name='AdminDeny', last_name='Test',
            id_number='IDG006', phone_number='+25470000094',
            county='Nairobi', cooperative=coop_loan.cooperative,
        )
        resp = api_client.post(f'/api/loans/{coop_loan.id}/add_guarantor/',
                               {'guarantor_id': str(other_farmer.id)}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestLoanMarkCompleted:
    def test_mark_completed(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct_mc@test.com', phone_number='+25470000777',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.installments_paid = coop_loan.number_of_installments
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_completed/', format='json')
        assert resp.status_code == status.HTTP_200_OK
        coop_loan.refresh_from_db()
        assert coop_loan.status == 'COMPLETED'

    def test_mark_completed_not_all_installments(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct_mc2@test.com', phone_number='+25470000888',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_completed/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_completed_not_active(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct_mc3@test.com', phone_number='+25470000999',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_completed/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_completed_permission_manager_denied(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr_mc@test.com', phone_number='+25470000111',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.installments_paid = coop_loan.number_of_installments
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_completed/', format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestLoanMarkDefaulted:
    def test_mark_defaulted(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr_md@test.com', phone_number='+25470000222',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_defaulted/',
                           {'reason': 'Failed to pay installments'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        coop_loan.refresh_from_db()
        assert coop_loan.status == 'DEFAULTED'

    def test_mark_defaulted_no_reason(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr_md2@test.com', phone_number='+25470000333',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_defaulted/', format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_defaulted_not_active(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr_md3@test.com', phone_number='+25470000444',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_defaulted/',
                           {'reason': 'Some reason'}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_defaulted_permission_accountant_denied(self, cooperative, coop_loan):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct_md@test.com', phone_number='+25470000555',
            first_name='Test', last_name='User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        coop_loan.status = 'ACTIVE'
        coop_loan.save()
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/loans/{coop_loan.id}/mark_defaulted/',
                           {'reason': 'test'}, format='json')
        assert resp.status_code == status.HTTP_200_OK


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
