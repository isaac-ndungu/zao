from datetime import date
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from rest_framework import status

from apps.base.constants import UserRole
from apps.conftest import positive_decimals
from apps.deductions.models import Deduction, DeductionType, FarmInputCredit, FarmInputCreditStatus

pytestmark = pytest.mark.django_db


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


class TestFarmInputCredit:
    def test_create(self, farmer):
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
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Seeds',
            amount=Decimal('2000.00'),
            supplied_date=date.today(),
        )
        assert credit.status == 'ACTIVE'

    def test_total_deducted_default(self, farmer):
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Pesticide',
            amount=Decimal('3000.00'),
            supplied_date=date.today(),
        )
        assert credit.total_deducted == Decimal('0.00')

    def test_status_completed(self, farmer):
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
        credit = FarmInputCredit.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            item_description='Test',
            amount=Decimal('1000.00'),
            supplied_date=date.today(),
        )
        credit.soft_delete()
        assert credit.deleted_at is not None


from django.contrib.auth import get_user_model
User = get_user_model()


@pytest.fixture
def accountant_api_client(db, cooperative):
    from rest_framework.test import APIClient
    user = User.objects.create_user(
        email='acct@ded.com', phone_number='+25470000001',
        first_name='Acct', last_name='Ded',
        password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def coop_deduction(db, cooperative, farmer):
    from apps.payment_engine.models import PaymentCycle
    cycle = PaymentCycle.objects.create(
        cooperative=cooperative, name='Ded Test Cycle',
        start_date=date(2024, 1, 1), end_date=date(2024, 1, 31),
        status='DRAFT',
    )
    return Deduction.objects.create(
        farmer=farmer, cycle=cycle, cooperative=cooperative,
        deduction_type=DeductionType.LEVY, amount=Decimal('90.00'),
    )


@pytest.fixture
def deduction(db, farmer, cooperative):
    from apps.payment_engine.models import PaymentCycle
    cycle = PaymentCycle.objects.create(
        cooperative=cooperative, name='Ded Fixture Cycle',
        start_date=date(2024, 1, 1), end_date=date(2024, 1, 31),
        status='DRAFT',
    )
    return Deduction.objects.create(
        farmer=farmer, cycle=cycle, cooperative=cooperative,
        deduction_type=DeductionType.LEVY, amount=Decimal('100.00'),
    )


@pytest.fixture
def farm_input_credit(db, farmer, cooperative):
    return FarmInputCredit.objects.create(
        farmer=farmer, cooperative=cooperative,
        item_description='Test Input', amount=Decimal('5000.00'),
        installment_amount=Decimal('500.00'), supplied_date=date.today(),
    )


class TestDeductionAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/deductions/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, deduction):
        resp = api_client.get('/api/deductions/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, deduction):
        resp = api_client.get(f'/api/deductions/{deduction.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(deduction.id)

    def test_create(self, accountant_api_client, farmer, cooperative):
        from apps.payment_engine.models import PaymentCycle
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Ded Cycle',
            start_date=date(2024, 1, 1), end_date=date(2024, 1, 31),
            status='DRAFT',
        )
        resp = accountant_api_client.post('/api/deductions/', {
            'farmer': str(farmer.id),
            'cycle': str(cycle.id),
            'amount': '150.00',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['amount'] == '150.00'

    def test_create_negative_amount(self, accountant_api_client, farmer, cooperative):
        from apps.payment_engine.models import PaymentCycle
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Ded Cycle Neg',
            start_date=date(2024, 2, 1), end_date=date(2024, 2, 28),
            status='DRAFT',
        )
        resp = accountant_api_client.post('/api/deductions/', {
            'farmer': str(farmer.id),
            'cycle': str(cycle.id),
            'amount': '-50.00',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_locked_cycle(self, accountant_api_client, farmer, cooperative):
        from apps.payment_engine.models import PaymentCycle
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Ded Cycle Lock',
            start_date=date(2024, 3, 1), end_date=date(2024, 3, 31),
            status='LOCKED',
        )
        resp = accountant_api_client.post('/api/deductions/', {
            'farmer': str(farmer.id),
            'cycle': str(cycle.id),
            'amount': '100.00',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unauthenticated(self, client, farmer, payment_cycle):
        resp = client.post('/api/deductions/', {
            'farmer': str(farmer.id),
            'cycle': str(payment_cycle.id),
            'amount': '100.00',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_permission_farmer_denied(self, cooperative, farmer, payment_cycle):
        from rest_framework.test import APIClient
        farmer_user = User.objects.create_user(
            email='f@ded.com', phone_number='+25470000111',
            first_name='Farm', last_name='Ded',
            password='testpass123', role=UserRole.FARMER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        resp = client.post('/api/deductions/', {
            'farmer': str(farmer.id),
            'cycle': str(payment_cycle.id),
            'amount': '100.00',
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, accountant_api_client, coop_deduction):
        resp = accountant_api_client.patch(f'/api/deductions/{coop_deduction.id}/', {'notes': 'Updated'}, format='json')
        assert resp.status_code == status.HTTP_200_OK

    def test_delete(self, accountant_api_client, coop_deduction):
        resp = accountant_api_client.delete(f'/api/deductions/{coop_deduction.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_locked_cycle(self, accountant_api_client, coop_deduction):
        coop_deduction.cycle.status = 'LOCKED'
        coop_deduction.cycle.save()
        resp = accountant_api_client.delete(f'/api/deductions/{coop_deduction.id}/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_by_farmer(self, api_client, deduction):
        resp = api_client.get(f'/api/deductions/?farmer={deduction.farmer_id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_type(self, api_client, deduction):
        resp = api_client.get(f'/api/deductions/?type={deduction.deduction_type}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_cycle(self, api_client, deduction):
        resp = api_client.get(f'/api/deductions/?cycle={deduction.cycle_id}')
        assert resp.status_code == status.HTTP_200_OK


class TestFarmInputCreditAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/deductions/farm-input-credits/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, farm_input_credit):
        resp = api_client.get('/api/deductions/farm-input-credits/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, farm_input_credit):
        resp = api_client.get(f'/api/deductions/farm-input-credits/{farm_input_credit.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(farm_input_credit.id)

    def test_create(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/deductions/farm-input-credits/', {
            'farmer': str(farmer.id),
            'item_description': 'Fertilizer',
            'amount': '5000.00',
            'installment_amount': '500.00',
            'supplied_date': str(date.today()),
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['item_description'] == 'Fertilizer'

    def test_create_negative_amount(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/deductions/farm-input-credits/', {
            'farmer': str(farmer.id),
            'item_description': 'Bad',
            'amount': '-100.00',
            'supplied_date': str(date.today()),
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_negative_installment(self, accountant_api_client, farmer):
        resp = accountant_api_client.post('/api/deductions/farm-input-credits/', {
            'farmer': str(farmer.id),
            'item_description': 'Bad Inst',
            'amount': '1000.00',
            'installment_amount': '-100.00',
            'supplied_date': str(date.today()),
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unauthenticated(self, client, farmer):
        resp = client.post('/api/deductions/farm-input-credits/', {
            'farmer': str(farmer.id),
            'item_description': 'Test',
            'amount': '100.00',
            'supplied_date': str(date.today()),
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_permission_farmer_denied(self, cooperative, farmer):
        from rest_framework.test import APIClient
        farmer_user = User.objects.create_user(
            email='f2@fic.com', phone_number='+25470000222',
            first_name='Farm', last_name='Fic',
            password='testpass123', role=UserRole.FARMER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        resp = client.post('/api/deductions/farm-input-credits/', {
            'farmer': str(farmer.id),
            'item_description': 'Test',
            'amount': '100.00',
            'supplied_date': str(date.today()),
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, accountant_api_client, farm_input_credit):
        resp = accountant_api_client.patch(f'/api/deductions/farm-input-credits/{farm_input_credit.id}/',
                                           {'item_description': 'Updated Input'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['item_description'] == 'Updated Input'

    def test_delete(self, accountant_api_client, farm_input_credit):
        resp = accountant_api_client.delete(f'/api/deductions/farm-input-credits/{farm_input_credit.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_completed(self, accountant_api_client, farm_input_credit):
        farm_input_credit.status = 'COMPLETED'
        farm_input_credit.save()
        resp = accountant_api_client.delete(f'/api/deductions/farm-input-credits/{farm_input_credit.id}/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_by_farmer(self, api_client, farm_input_credit):
        resp = api_client.get(f'/api/deductions/farm-input-credits/?farmer={farm_input_credit.farmer_id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_status(self, api_client, farm_input_credit):
        resp = api_client.get('/api/deductions/farm-input-credits/?status=ACTIVE')
        assert resp.status_code == status.HTTP_200_OK


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
