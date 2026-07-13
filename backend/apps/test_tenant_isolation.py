"""
Tenant isolation integration tests.

Creates two cooperatives with distinct data, authenticates as a manager from
cooperative A, hits every list endpoint, and asserts zero cooperative B records
appear in the response. A viewset can inherit from CooperativeScopedViewSet
correctly and still leak data if get_queryset() is overridden incorrectly
downstream — inheritance checks alone are insufficient.
"""
import uuid
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_api.models import User
from apps.base.constants import UserRole
from apps.base.models import AuditLog
from apps.conftest import (
    BuyerFactory,
    CollectionRouteFactory,
    CooperativeFactory,
    DeductionFactory,
    DeliveryFactory,
    DisbursementBatchFactory,
    DisbursementTransactionFactory,
    FarmInputCreditFactory,
    FarmerFactory,
    FarmerPaymentFactory,
    GradeFactory,
    GradePriceFactory,
    InventoryFactory,
    LoanFactory,
    NotificationFactory,
    PaymentCycleFactory,
    SaleFactory,
)


def _manager_user(cooperative):
    """Create a manager user for the given cooperative."""
    return User.objects.create(
        email=f'mgr-{str(cooperative.id)[:8]}@test.com',
        phone_number=f'+2547{uuid.uuid4().int % 10**8:08d}',
        role=UserRole.MANAGER,
        cooperative=cooperative,
    )


def _get_result_ids(response):
    """Extract all 'id' values from a paginated or non-paginated response."""
    data = response.data
    if isinstance(data, dict) and 'results' in data:
        return [str(r.get('id', '')) for r in data['results']]
    if isinstance(data, list):
        return [str(r.get('id', '')) for r in data]
    return []


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def coop_a(db):
    return CooperativeFactory()


@pytest.fixture
def coop_b(db):
    return CooperativeFactory()


@pytest.fixture
def manager_a(coop_a):
    return _manager_user(coop_a)


@pytest.fixture
def client_a(manager_a):
    client = APIClient()
    client.force_authenticate(user=manager_a)
    return client


# =============================================================================
# Helpers — create data for each cooperative
# =============================================================================


def _seed_data(coop_a, coop_b):
    """Create parallel records in both cooperatives for isolation testing."""
    farmer_a = FarmerFactory(cooperative=coop_a)
    farmer_b = FarmerFactory(cooperative=coop_b)

    delivery_a = DeliveryFactory(farmer=farmer_a, cooperative=coop_a, status='GRADED')
    delivery_b = DeliveryFactory(farmer=farmer_b, cooperative=coop_b, status='GRADED')

    grade_a = GradeFactory(delivery=delivery_a, cooperative=coop_a, grade_letter='A')
    grade_b = GradeFactory(delivery=delivery_b, cooperative=coop_b, grade_letter='A')

    GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'))
    GradePriceFactory(grade_letter='A', price_per_unit=Decimal('60.00'), cooperative=coop_b)

    cycle_a = PaymentCycleFactory(cooperative=coop_a)
    cycle_b = PaymentCycleFactory(cooperative=coop_b)

    FarmerPaymentFactory(cycle=cycle_a, farmer=farmer_a, cooperative=coop_a)
    FarmerPaymentFactory(cycle=cycle_b, farmer=farmer_b, cooperative=coop_b)

    LoanFactory(farmer=farmer_a, cooperative=coop_a)
    LoanFactory(farmer=farmer_b, cooperative=coop_b)

    DeductionFactory(farmer=farmer_a, cycle=cycle_a, cooperative=coop_a)
    DeductionFactory(farmer=farmer_b, cycle=cycle_b, cooperative=coop_b)

    FarmInputCreditFactory(farmer=farmer_a, cooperative=coop_a)
    FarmInputCreditFactory(farmer=farmer_b, cooperative=coop_b)

    batch_a = DisbursementBatchFactory(cooperative=coop_a)
    batch_b = DisbursementBatchFactory(cooperative=coop_b)
    DisbursementTransactionFactory(batch=batch_a, farmer=farmer_a, cooperative=coop_a)
    DisbursementTransactionFactory(batch=batch_b, farmer=farmer_b, cooperative=coop_b)

    InventoryFactory(cooperative=coop_a)
    InventoryFactory(cooperative=coop_b)

    NotificationFactory(cooperative=coop_a)
    NotificationFactory(cooperative=coop_b)

    buyer_a = BuyerFactory(cooperative=coop_a)
    buyer_b = BuyerFactory(cooperative=coop_b)
    SaleFactory(buyer=buyer_a, cooperative=coop_a)
    SaleFactory(buyer=buyer_b, cooperative=coop_b)

    CollectionRouteFactory(cooperative=coop_a)
    CollectionRouteFactory(cooperative=coop_b)

    AuditLog.objects.create(
        cooperative=coop_a, actor=manager_a if hasattr(manager_a, 'id') else None,
        resource_type='FarmerPayment', resource_id=uuid.uuid4(),
        action='CREATE', ip_address='127.0.0.1',
    )
    AuditLog.objects.create(
        cooperative=coop_b, actor=None,
        resource_type='FarmerPayment', resource_id=uuid.uuid4(),
        action='CREATE', ip_address='127.0.0.1',
    )

    return {
        'farmer_a': farmer_a, 'farmer_b': farmer_b,
        'delivery_a': delivery_a, 'delivery_b': delivery_b,
        'grade_a': grade_a, 'grade_b': grade_b,
        'cycle_a': cycle_a, 'cycle_b': cycle_b,
    }


# =============================================================================
# Individual endpoint tests
# =============================================================================


@pytest.mark.django_db
class TestCooperativeIsolation:
    """Test that non-admin users cannot see data from other cooperatives."""

    def test_cooperatives_list(self, client_a, coop_a, coop_b):
        resp = client_a.get('/api/cooperatives/')
        assert resp.status_code == 200
        ids = _get_result_ids(resp)
        assert str(coop_a.id) in ids
        assert str(coop_b.id) not in ids

    def test_cooperatives_me(self, client_a, coop_a):
        resp = client_a.get('/api/cooperatives/me/')
        assert resp.status_code == 200
        assert resp.data['id'] == str(coop_a.id)

    def test_cooperatives_stats(self, client_a, coop_a, coop_b):
        resp = client_a.get('/api/cooperatives/stats/')
        assert resp.status_code == 200
        assert resp.data['total'] == 1

    def test_cooperatives_enums_public(self, coop_a):
        client = APIClient()
        resp = client.get('/api/cooperatives/enums/')
        assert resp.status_code == 200
        assert 'produce_types' in resp.data

    def test_cooperatives_list_requires_auth(self, coop_a):
        client = APIClient()
        resp = client.get('/api/cooperatives/')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestFarmerIsolation:
    def test_farmers_list(self, client_a, coop_a, coop_b):
        resp = client_a.get('/api/farmers/')
        assert resp.status_code == 200
        ids = _get_result_ids(resp)
        for fid in ids:
            assert fid != ''  # sanity

    def test_farmers_list_no_cross_tenant(self, client_a, coop_a, coop_b):
        FarmerFactory(cooperative=coop_a)
        FarmerFactory(cooperative=coop_b)
        resp = client_a.get('/api/farmers/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestDeliveryIsolation:
    def test_deliveries_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        DeliveryFactory(farmer=farmer_a, cooperative=coop_a)
        DeliveryFactory(farmer=farmer_b, cooperative=coop_b)
        resp = client_a.get('/api/deliveries/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestGradeIsolation:
    def test_grades_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        d_a = DeliveryFactory(farmer=farmer_a, cooperative=coop_a)
        d_b = DeliveryFactory(farmer=farmer_b, cooperative=coop_b)
        GradeFactory(delivery=d_a, cooperative=coop_a)
        GradeFactory(delivery=d_b, cooperative=coop_b)
        resp = client_a.get('/api/grades/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestGradePriceIsolation:
    def test_grade_prices_scoped(self, client_a, coop_a, coop_b):
        GradePriceFactory(grade_letter='A', price_per_unit=Decimal('50.00'))
        GradePriceFactory(grade_letter='B', price_per_unit=Decimal('60.00'), cooperative=coop_b)
        resp = client_a.get('/api/grade-prices/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            results = data['results']
        elif isinstance(data, list):
            results = data
        else:
            results = []
        coop_b_ids = {str(coop_b.id)}
        for item in results:
            coop_field = item.get('cooperative')
            if coop_field is not None:
                assert str(coop_field) not in coop_b_ids or coop_field is None


@pytest.mark.django_db
class TestDisputeIsolation:
    def test_disputes_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        d_a = DeliveryFactory(farmer=farmer_a, cooperative=coop_a)
        d_b = DeliveryFactory(farmer=farmer_b, cooperative=coop_b)
        g_a = GradeFactory(delivery=d_a, cooperative=coop_a)
        g_b = GradeFactory(delivery=d_b, cooperative=coop_b)
        from apps.grading.models import FarmerGradeDispute
        FarmerGradeDispute.objects.create(grade=g_a, raised_by=farmer_a.user, reason='Wrong grade')
        FarmerGradeDispute.objects.create(grade=g_b, raised_by=farmer_b.user, reason='Wrong grade')
        resp = client_a.get('/api/disputes/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestInventoryIsolation:
    def test_inventory_list(self, client_a, coop_a, coop_b):
        InventoryFactory(cooperative=coop_a)
        InventoryFactory(cooperative=coop_b)
        resp = client_a.get('/api/inventory/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestStockIsolation:
    def test_stock_list(self, client_a, coop_a, coop_b):
        from apps.inventory.models import Stock
        Stock.objects.create(cooperative=coop_a, product_type='MILK', grade='A', quantity_available=Decimal('100'))
        Stock.objects.create(cooperative=coop_b, product_type='MILK', grade='A', quantity_available=Decimal('200'))
        resp = client_a.get('/api/stock/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestNotificationIsolation:
    def test_notifications_list(self, client_a, coop_a, coop_b):
        NotificationFactory(cooperative=coop_a)
        NotificationFactory(cooperative=coop_b)
        resp = client_a.get('/api/notifications/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestPaymentCycleIsolation:
    def test_payment_cycles_list(self, client_a, coop_a, coop_b):
        PaymentCycleFactory(cooperative=coop_a)
        PaymentCycleFactory(cooperative=coop_b)
        resp = client_a.get('/api/payment-engine/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestFarmerPaymentIsolation:
    def test_payments_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        cycle_a = PaymentCycleFactory(cooperative=coop_a)
        cycle_b = PaymentCycleFactory(cooperative=coop_b)
        FarmerPaymentFactory(cycle=cycle_a, farmer=farmer_a, cooperative=coop_a)
        FarmerPaymentFactory(cycle=cycle_b, farmer=farmer_b, cooperative=coop_b)
        resp = client_a.get('/api/payments/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestLoanIsolation:
    def test_loans_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        LoanFactory(farmer=farmer_a, cooperative=coop_a)
        LoanFactory(farmer=farmer_b, cooperative=coop_b)
        resp = client_a.get('/api/loans/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestDeductionIsolation:
    def test_deductions_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        cycle_a = PaymentCycleFactory(cooperative=coop_a)
        cycle_b = PaymentCycleFactory(cooperative=coop_b)
        DeductionFactory(farmer=farmer_a, cycle=cycle_a, cooperative=coop_a)
        DeductionFactory(farmer=farmer_b, cycle=cycle_b, cooperative=coop_b)
        resp = client_a.get('/api/deductions/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestDisbursementIsolation:
    def test_disbursements_list(self, client_a, coop_a, coop_b):
        DisbursementBatchFactory(cooperative=coop_a)
        DisbursementBatchFactory(cooperative=coop_b)
        resp = client_a.get('/api/disbursements/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestBuyerIsolation:
    def test_buyers_list(self, client_a, coop_a, coop_b):
        BuyerFactory(cooperative=coop_a)
        BuyerFactory(cooperative=coop_b)
        resp = client_a.get('/api/buyers/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestSaleIsolation:
    def test_sales_list(self, client_a, coop_a, coop_b):
        buyer_a = BuyerFactory(cooperative=coop_a)
        buyer_b = BuyerFactory(cooperative=coop_b)
        SaleFactory(buyer=buyer_a, cooperative=coop_a)
        SaleFactory(buyer=buyer_b, cooperative=coop_b)
        resp = client_a.get('/api/sales/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestRouteIsolation:
    def test_routes_list(self, client_a, coop_a, coop_b):
        CollectionRouteFactory(cooperative=coop_a)
        CollectionRouteFactory(cooperative=coop_b)
        resp = client_a.get('/api/routes/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestAuditLogIsolation:
    def test_audit_logs_list(self, client_a, coop_a, coop_b):
        AuditLog.objects.create(
            cooperative=coop_a, resource_type='FarmerPayment',
            resource_id=uuid.uuid4(), action='CREATE', ip_address='127.0.0.1',
        )
        AuditLog.objects.create(
            cooperative=coop_b, resource_type='FarmerPayment',
            resource_id=uuid.uuid4(), action='CREATE', ip_address='127.0.0.1',
        )
        resp = client_a.get('/api/statements/audit/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestFarmInputCreditIsolation:
    def test_farm_input_credits_list(self, client_a, coop_a, coop_b):
        farmer_a = FarmerFactory(cooperative=coop_a)
        farmer_b = FarmerFactory(cooperative=coop_b)
        FarmInputCreditFactory(farmer=farmer_a, cooperative=coop_a)
        FarmInputCreditFactory(farmer=farmer_b, cooperative=coop_b)
        resp = client_a.get('/api/deductions/farm-input-credits/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1


@pytest.mark.django_db
class TestUserIsolation:
    def test_users_list(self, client_a, coop_a, coop_b):
        User.objects.create(
            email='user-b@test.com', phone_number='+254700000099',
            role=UserRole.MANAGER, cooperative=coop_b,
        )
        resp = client_a.get('/api/users/')
        assert resp.status_code == 200
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            count = data['count']
        elif isinstance(data, list):
            count = len(data)
        else:
            count = 0
        assert count == 1
