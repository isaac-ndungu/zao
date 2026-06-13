import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import factory
import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone
from hypothesis import strategies as st
from rest_framework.test import APIClient

from apps.auth_api.managers import UserManager
from apps.base.constants import UserRole
from apps.base.models import AuditLog


# =============================================================================
# Factories
# =============================================================================


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'auth_api.User'
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    phone_number = factory.Sequence(lambda n: f'+2547{n:08d}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = UserRole.ADMIN
    is_active = True
    is_staff = True
    is_superuser = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        password = kwargs.pop('password', 'testpass123')
        user = manager.create_superuser(*args, **kwargs, password=password)
        user.raw_password = password
        return user


class CooperativeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'cooperatives.Cooperative'
        django_get_or_create = ('registration_number',)

    name = factory.Sequence(lambda n: f'Test Coop {n}')
    registration_number = factory.Sequence(lambda n: f'COOP{n:05d}')
    county = 'Nairobi'
    sub_county = 'Westlands'
    produce_type = 'DAIRY'
    payment_model = 'FIXED_PRICE'
    levy_percentage = Decimal('2.00')
    monthly_fee = Decimal('100.00')
    is_active = True
    prefix = factory.Sequence(lambda n: f'TC{n}')
    mpesa_shortcode = '123456'


class FarmerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'farmers.Farmer'

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Sequence(lambda n: f'farmer{n}@example.com')
    id_number = factory.Sequence(lambda n: f'ID{n:08d}')
    phone_number = factory.Sequence(lambda n: f'+2547{n:08d}')
    county = 'Nairobi'
    sub_county = 'Westlands'
    ward = 'Ward A'
    village = 'Village 1'
    is_active = True
    cooperative = factory.SubFactory(CooperativeFactory)

    @factory.post_generation
    def create_membership(obj, create, extracted, **kwargs):
        if create and not obj.memberships.exists():
            FarmerCooperativeMembershipFactory(
                farmer=obj,
                cooperative=obj.cooperative,
                member_number=kwargs.get('member_number') or f'FM{str(obj.id)[:8].upper()}',
            )


class FarmerCooperativeMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'farmers.FarmerCooperativeMembership'

    farmer = factory.SubFactory(FarmerFactory)
    cooperative = factory.SubFactory(CooperativeFactory)
    member_number = factory.Sequence(lambda n: f'MEM{n:06d}')
    payment_method = 'M-PESA'
    mpesa_number = factory.Sequence(lambda n: f'+2547{n:08d}')
    is_active = True


class DeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'deliveries.Delivery'

    farmer = factory.SubFactory(FarmerFactory)
    cooperative = factory.SelfAttribute('farmer.cooperative')
    product_type = 'MILK'
    quantity_kg = Decimal('100.00')
    volume_litres = None
    status = 'PENDING'
    date_delivered = factory.LazyFunction(timezone.now)
    batch_id = factory.Sequence(lambda n: f'BAT{n:06d}')


class GradeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'grading.Grade'

    delivery = factory.SubFactory(DeliveryFactory)
    cooperative = factory.SelfAttribute('delivery.cooperative')
    grade_letter = 'A'
    price_per_unit = Decimal('45.00')


class GradePriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'grading.GradePrice'

    grade_letter = 'A'
    price_per_unit = Decimal('45.00')
    effective_from = factory.LazyFunction(date.today)


class GradeImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'grading.GradeImage'

    image = factory.django.ImageField(filename='test_grade.jpg')


class PaymentCycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'payment_engine.PaymentCycle'

    cooperative = factory.SubFactory(CooperativeFactory)
    name = factory.Sequence(lambda n: f'Cycle {n}')
    start_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: date.today() - timedelta(days=1))
    status = 'DRAFT'


class FarmerPaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'payment_engine.FarmerPayment'

    cycle = factory.SubFactory(PaymentCycleFactory)
    farmer = factory.SubFactory(FarmerFactory)
    cooperative = factory.SelfAttribute('cycle.cooperative')
    total_quantity = Decimal('100.00')
    gross_amount = Decimal('4500.00')
    net_amount = Decimal('4300.00')
    grade_breakdown = {'A': {'kg': '100.00', 'amount': '4500.00'}}
    deductions = {'levy': '90.00', 'monthly_fee': '100.00', 'loan_repayment': '0.00', 'input_credit': '10.00'}
    computation_log = {
        'method': 'fixed_price',
        'total_quantity': '100.00',
        'gross_amount': '4500.00',
        'deductions_applied': '200.00',
        'net_amount': '4300.00',
        'withholding_tax': '0.00',
    }


class LoanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'loans.Loan'

    farmer = factory.SubFactory(FarmerFactory)
    cooperative = factory.SelfAttribute('farmer.cooperative')
    amount_principal = Decimal('10000.00')
    interest_rate = Decimal('10.00')
    total_repayable = Decimal('11000.00')
    installment_amount = Decimal('1833.33')
    number_of_installments = 6
    status = 'PENDING'


class LoanGuarantorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'loans.LoanGuarantor'

    loan = factory.SubFactory(LoanFactory)
    guarantor = factory.SubFactory(FarmerFactory)
    cooperative = factory.SelfAttribute('loan.cooperative')


class LoanRepaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'loans.LoanRepayment'

    loan = factory.SubFactory(LoanFactory)
    farmer_payment = factory.SubFactory(FarmerPaymentFactory)
    amount = Decimal('1833.33')


class DeductionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'deductions.Deduction'

    farmer = factory.SubFactory(FarmerFactory)
    cycle = factory.SubFactory(PaymentCycleFactory)
    cooperative = factory.SelfAttribute('cycle.cooperative')
    deduction_type = 'LEVY'
    amount = Decimal('90.00')


class FarmInputCreditFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'deductions.FarmInputCredit'

    farmer = factory.SubFactory(FarmerFactory)
    cooperative = factory.SelfAttribute('farmer.cooperative')
    item_description = 'Fertilizer'
    amount = Decimal('5000.00')
    installment_amount = Decimal('500.00')
    supplied_date = factory.LazyFunction(date.today)


class DisbursementBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'disbursement.DisbursementBatch'

    cooperative = factory.SubFactory(CooperativeFactory)
    status = 'PENDING'
    command_id = 'SalaryPayment'


class DisbursementTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'disbursement.DisbursementTransaction'

    batch = factory.SubFactory(DisbursementBatchFactory)
    farmer = factory.SubFactory(FarmerFactory)
    cooperative = factory.SelfAttribute('batch.cooperative')
    amount = Decimal('4300.00')
    payment_method = 'M_PESA'
    recipient_identifier = factory.Sequence(lambda n: f'+2547{n:08d}')
    recipient_name = factory.Faker('name')


class BuyerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'sales.Buyer'

    cooperative = factory.SubFactory(CooperativeFactory)
    name = factory.Sequence(lambda n: f'Buyer {n}')
    phone_number = factory.Sequence(lambda n: f'+2547{n:08d}')
    is_active = True


class SaleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'sales.Sale'

    buyer = factory.SubFactory(BuyerFactory)
    cooperative = factory.SelfAttribute('buyer.cooperative')
    product_type = 'MILK'
    grade_letter = 'A'
    unit = 'kg'
    quantity = Decimal('100.00')
    price_per_unit = Decimal('45.00')
    total_amount = Decimal('4500.00')
    status = 'PENDING'
    sale_date = factory.LazyFunction(date.today)


class InventoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'inventory.Inventory'

    cooperative = factory.SubFactory(CooperativeFactory)
    batch_id = factory.Sequence(lambda n: f'INV{n:06d}')
    product_type = 'MILK'
    grade = 'A'
    unit = 'kg'
    quantity_in = Decimal('1000.00')


class CollectionRouteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'routes.CollectionRoute'

    cooperative = factory.SubFactory(CooperativeFactory)
    name = factory.Sequence(lambda n: f'Route {n}')
    path = {'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]}
    is_active = True
    day_of_week = 'MONDAY'


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'notifications.Notification'

    cooperative = factory.SubFactory(CooperativeFactory)
    channel = 'SMS'
    notification_type = 'GENERAL'
    content = factory.Faker('sentence')
    status = 'PENDING'


class TwoFactorOTPFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'auth_api.TwoFactorOTP'

    user = factory.SubFactory(UserFactory)
    otp_code = '123456'
    purpose = 'LOGIN'
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=5))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def disable_audit_log():
    """Prevent AuditLog writes during tests to avoid DB noise."""
    with patch.object(AuditLog, 'save', side_effect=ValueError('AuditLog disabled in tests')):
        yield


@pytest.fixture
def superuser(db):
    return UserFactory(is_superuser=True, is_staff=True, role=UserRole.ADMIN)


@pytest.fixture
def api_client(db):
    client = APIClient()
    user = UserFactory(is_superuser=True, is_staff=True, role=UserRole.ADMIN)
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def cooperative(db):
    return CooperativeFactory()


@pytest.fixture
def farmer(db):
    return FarmerFactory()


@pytest.fixture
def delivery(db):
    return DeliveryFactory()


@pytest.fixture
def grade(db):
    return GradeFactory()


@pytest.fixture
def payment_cycle(db):
    return PaymentCycleFactory()


@pytest.fixture
def loan(db):
    return LoanFactory()


@pytest.fixture
def buyer(db):
    return BuyerFactory()


@pytest.fixture
def sale(db):
    return SaleFactory()


@pytest.fixture
def disbursement_batch(db):
    return DisbursementBatchFactory()


# =============================================================================
# Hypothesis strategies
# =============================================================================

positive_decimals = st.decimals(
    min_value=Decimal('0.01'),
    max_value=Decimal('999999999.99'),
    places=2,
)

nonnegative_decimals = st.decimals(
    min_value=Decimal('0.00'),
    max_value=Decimal('999999999.99'),
    places=2,
)

small_percentages = st.decimals(
    min_value=Decimal('0.00'),
    max_value=Decimal('100.00'),
    places=2,
)


def installments_strategy():
    return st.integers(min_value=1, max_value=60)
