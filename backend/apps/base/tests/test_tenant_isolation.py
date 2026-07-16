"""
Tenant isolation regression tests.

Verifies that cooperative-scoped viewsets correctly filter data by tenant,
and that the admin bypass uses is_superuser (not role='admin') to prevent
cross-tenant data leakage.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient

from apps.auth_api.models import User
from apps.base.constants import UserRole
from apps.cooperatives.models import Cooperative
from apps.deliveries.models import Delivery
from apps.grading.models import GradePrice
from apps.inventory.models import Inventory, Stock
from apps.farmers.models import Farmer
from apps.notifications.models import Notification


pytestmark = pytest.mark.django_db


def _auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def coop_a():
    return Cooperative.objects.create(
        name='Coop A',
        registration_number='COOP90001',
        county='Nairobi',
        produce_type='DAIRY',
        payment_model='FIXED_PRICE',
        levy_percentage=Decimal('2.00'),
        monthly_fee=Decimal('100.00'),
        is_active=True,
        prefix='CA',
        mpesa_shortcode='111111',
    )


@pytest.fixture
def coop_b():
    return Cooperative.objects.create(
        name='Coop B',
        registration_number='COOP90002',
        county='Kiambu',
        produce_type='COFFEE',
        payment_model='REVENUE_SHARE',
        levy_percentage=Decimal('3.00'),
        monthly_fee=Decimal('200.00'),
        is_active=True,
        prefix='CB',
        mpesa_shortcode='222222',
    )


@pytest.fixture
def admin_not_superuser(coop_a):
    return User.objects.create_user(
        email='admin_no_su@test.com',
        phone_number='+254700009001',
        first_name='Admin',
        last_name='NoSU',
        password='testpass123',
        role=UserRole.ADMIN,
        cooperative=coop_a,
        is_staff=False,
        is_superuser=False,
    )


@pytest.fixture
def superuser_user(coop_a):
    return User.objects.create_user(
        email='su@test.com',
        phone_number='+254700009002',
        first_name='Super',
        last_name='User',
        password='testpass123',
        role=UserRole.ADMIN,
        cooperative=coop_a,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def delivery_a(coop_a):
    farmer_user = User.objects.create_user(
        email='farmer_a@test.com',
        phone_number='+254700009003',
        first_name='Farmer',
        last_name='A',
        password='testpass123',
        role=UserRole.FARMER,
        cooperative=coop_a,
    )
    return Delivery.objects.create(
        cooperative=coop_a,
        farmer=farmer_user,
        product_type='MILK',
        quantity_kg=Decimal('100.00'),
        status='PENDING',
        batch_id='BAT90001',
    )


@pytest.fixture
def delivery_b(coop_b):
    farmer_user = User.objects.create_user(
        email='farmer_b@test.com',
        phone_number='+254700009004',
        first_name='Farmer',
        last_name='B',
        password='testpass123',
        role=UserRole.FARMER,
        cooperative=coop_b,
    )
    return Delivery.objects.create(
        cooperative=coop_b,
        farmer=farmer_user,
        product_type='COFFEE',
        quantity_kg=Decimal('200.00'),
        status='PENDING',
        batch_id='BAT90002',
    )


@pytest.fixture
def grade_price_a(coop_a):
    return GradePrice.objects.create(
        cooperative=coop_a,
        grade_letter='A',
        price_per_unit=Decimal('45.00'),
        effective_from='2026-01-01',
    )


@pytest.fixture
def grade_price_b(coop_b):
    return GradePrice.objects.create(
        cooperative=coop_b,
        grade_letter='A',
        price_per_unit=Decimal('60.00'),
        effective_from='2026-01-01',
    )


@pytest.fixture
def inventory_a(coop_a):
    return Inventory.objects.create(
        cooperative=coop_a,
        batch_id='INV90001',
        product_type='MILK',
        grade='A',
        unit='kg',
        quantity_in=Decimal('1000'),
        quantity_out=Decimal('500'),
    )


@pytest.fixture
def inventory_b(coop_b):
    return Inventory.objects.create(
        cooperative=coop_b,
        batch_id='INV90002',
        product_type='COFFEE',
        grade='A',
        unit='kg',
        quantity_in=Decimal('2000'),
        quantity_out=Decimal('800'),
    )


@pytest.fixture
def stock_a(coop_a):
    return Stock.objects.create(
        cooperative=coop_a,
        product_type='MILK',
        grade='A',
        quantity_available=Decimal('500'),
    )


@pytest.fixture
def stock_b(coop_b):
    return Stock.objects.create(
        cooperative=coop_b,
        product_type='COFFEE',
        grade='A',
        quantity_available=Decimal('1200'),
    )


@pytest.fixture
def notification_a(coop_a):
    farmer = Farmer.objects.create(
        cooperative=coop_a,
        first_name='NotifFarmer',
        last_name='A',
        id_number='12345678',
        phone_number='+254700009005',
        county='Nairobi',
        is_active=True,
    )
    return Notification.objects.create(
        cooperative=coop_a,
        recipient=farmer,
        channel='SMS',
        notification_type='GENERAL',
        content='Test notification A',
        status='SENT',
    )


@pytest.fixture
def notification_b(coop_b):
    farmer = Farmer.objects.create(
        cooperative=coop_b,
        first_name='NotifFarmer',
        last_name='B',
        id_number='87654321',
        phone_number='+254700009006',
        county='Kiambu',
        is_active=True,
    )
    return Notification.objects.create(
        cooperative=coop_b,
        recipient=farmer,
        channel='SMS',
        notification_type='GENERAL',
        content='Test notification B',
        status='SENT',
    )


class TestTenantIsolationCooperativeViewSet:
    def test_admin_not_superuser_scoped_to_own_coop(self, admin_not_superuser, coop_a, coop_b):
        client = _auth_client(admin_not_superuser)
        resp = client.get('/api/cooperatives/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [c['id'] for c in resp.data['results']]
        assert str(coop_a.id) in ids
        assert str(coop_b.id) not in ids

    def test_superuser_sees_all_coops(self, superuser_user, coop_a, coop_b):
        client = _auth_client(superuser_user)
        resp = client.get('/api/cooperatives/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [c['id'] for c in resp.data['results']]
        assert str(coop_a.id) in ids
        assert str(coop_b.id) in ids


class TestTenantIsolationGradePriceViewSet:
    def test_admin_not_superuser_scoped(self, admin_not_superuser, grade_price_a, grade_price_b):
        client = _auth_client(admin_not_superuser)
        resp = client.get('/api/grade-prices/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [g['id'] for g in resp.data['results']]
        assert str(grade_price_a.id) in ids
        assert str(grade_price_b.id) not in ids

    def test_superuser_sees_all(self, superuser_user, grade_price_a, grade_price_b):
        client = _auth_client(superuser_user)
        resp = client.get('/api/grade-prices/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [g['id'] for g in resp.data['results']]
        assert str(grade_price_a.id) in ids
        assert str(grade_price_b.id) in ids


class TestTenantIsolationInventoryViewSet:
    def test_admin_not_superuser_scoped(self, admin_not_superuser, inventory_a, inventory_b):
        client = _auth_client(admin_not_superuser)
        resp = client.get('/api/inventory/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [i['id'] for i in resp.data['results']]
        assert str(inventory_a.id) in ids
        assert str(inventory_b.id) not in ids

    def test_superuser_sees_all(self, superuser_user, inventory_a, inventory_b):
        client = _auth_client(superuser_user)
        resp = client.get('/api/inventory/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [i['id'] for i in resp.data['results']]
        assert str(inventory_a.id) in ids
        assert str(inventory_b.id) in ids


class TestTenantIsolationStockViewSet:
    def test_admin_not_superuser_scoped(self, admin_not_superuser, stock_a, stock_b):
        client = _auth_client(admin_not_superuser)
        resp = client.get('/api/stock/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [s['id'] for s in resp.data['results']]
        assert str(stock_a.id) in ids
        assert str(stock_b.id) not in ids

    def test_superuser_sees_all(self, superuser_user, stock_a, stock_b):
        client = _auth_client(superuser_user)
        resp = client.get('/api/stock/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [s['id'] for s in resp.data['results']]
        assert str(stock_a.id) in ids
        assert str(stock_b.id) in ids


class TestTenantIsolationNotificationLogViewSet:
    def test_admin_not_superuser_scoped(self, admin_not_superuser, notification_a, notification_b):
        client = _auth_client(admin_not_superuser)
        resp = client.get('/api/notifications/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [n['id'] for n in resp.data['results']]
        assert str(notification_a.id) in ids
        assert str(notification_b.id) not in ids

    def test_superuser_sees_all(self, superuser_user, notification_a, notification_b):
        client = _auth_client(superuser_user)
        resp = client.get('/api/notifications/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [n['id'] for n in resp.data['results']]
        assert str(notification_a.id) in ids
        assert str(notification_b.id) in ids
