from decimal import Decimal

import pytest
from rest_framework import status

from apps.base.constants import UserRole
from apps.inventory.models import Inventory

pytestmark = pytest.mark.django_db


# =============================================================================
# Inventory Model Tests
# =============================================================================

class TestInventoryModel:
    def test_create(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV001',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('1000.00'),
        )
        assert inv.pk is not None

    def test_running_balance(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV002',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('1000.00'),
            quantity_out=Decimal('200.00'),
        )
        assert inv.running_balance == Decimal('800.00')

    def test_running_balance_no_out(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV003',
            product_type='MILK',
            grade='B',
            unit='litres',
            quantity_in=Decimal('500.00'),
        )
        assert inv.running_balance == Decimal('500.00')

    def test_running_balance_zero(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV004',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('100.00'),
            quantity_out=Decimal('100.00'),
        )
        assert inv.running_balance == Decimal('0.00')

    def test_str(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV005',
            product_type='MILK',
            grade='PREMIUM',
            unit='kg',
            quantity_in=Decimal('500.00'),
        )
        assert 'INV005' in str(inv)
        assert 'PREMIUM' in str(inv)

    def test_default_is_sold_false(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV006',
            product_type='MILK',
            unit='kg',
            quantity_in=Decimal('100.00'),
        )
        assert not inv.is_sold

    def test_soft_delete(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV007',
            product_type='MILK',
            unit='kg',
            quantity_in=Decimal('100.00'),
        )
        inv.soft_delete()
        assert inv.deleted_at is not None

    def test_cooperative_scoped(self, cooperative):
        inv = Inventory.objects.create(
            cooperative=cooperative,
            batch_id='INV008',
            product_type='MILK',
            unit='kg',
            quantity_in=Decimal('100.00'),
        )
        assert inv.cooperative == cooperative


# =============================================================================
# Inventory API Endpoint Tests
# =============================================================================

from django.contrib.auth import get_user_model
User = get_user_model()


class TestInventoryAPI:
    @pytest.fixture
    def inventory(self, cooperative):
        return Inventory.objects.create(
            cooperative=cooperative,
            batch_id='APIINV001',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('1000.00'),
        )

    def test_list_unauthenticated(self, client):
        resp = client.get('/api/inventory/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, inventory):
        resp = api_client.get('/api/inventory/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, inventory):
        resp = api_client.get(f'/api/inventory/{inventory.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(inventory.id)

    def test_retrieve_not_found(self, api_client):
        from uuid import uuid4
        resp = api_client.get(f'/api/inventory/{uuid4()}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_create_not_allowed(self, api_client):
        resp = api_client.post('/api/inventory/', {'batch_id': 'X'}, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_not_allowed(self, api_client, inventory):
        resp = api_client.patch(f'/api/inventory/{inventory.id}/', {'quantity_in': '999'}, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_not_allowed(self, api_client, inventory):
        resp = api_client.delete(f'/api/inventory/{inventory.id}/')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_filter_by_product_type(self, api_client, inventory):
        resp = api_client.get('/api/inventory/?product_type=MILK')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) >= 1

    def test_filter_by_grade(self, api_client, inventory):
        resp = api_client.get('/api/inventory/?grade=A')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_batch_id(self, api_client, inventory):
        resp = api_client.get(f'/api/inventory/?batch_id={inventory.batch_id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_search(self, api_client, inventory):
        resp = api_client.get('/api/inventory/?search=MILK')
        assert resp.status_code == status.HTTP_200_OK


class TestInventorySummary:
    @pytest.fixture
    def inventory(self, cooperative):
        return Inventory.objects.create(
            cooperative=cooperative,
            batch_id='SUMINV001',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('1000.00'),
            quantity_out=Decimal('200.00'),
        )

    def test_summary(self, api_client, inventory):
        resp = api_client.get('/api/inventory/summary/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'total_records' in data
        assert 'total_quantity_in' in data
        assert 'total_quantity_out' in data
        assert 'by_product_type' in data
        assert 'by_grade' in data
        assert data['total_records'] >= 1
        assert float(data['total_quantity_in']) >= 1000.0


class TestInventoryAlerts:
    @pytest.fixture
    def low_inventory(self, cooperative):
        return Inventory.objects.create(
            cooperative=cooperative,
            batch_id='LOWINV001',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('50.00'),
        )

    @pytest.fixture
    def high_inventory(self, cooperative):
        return Inventory.objects.create(
            cooperative=cooperative,
            batch_id='HIGHINV001',
            product_type='MILK',
            grade='B',
            unit='kg',
            quantity_in=Decimal('5000.00'),
        )

    def test_alerts_get(self, api_client, low_inventory, high_inventory):
        resp = api_client.get('/api/inventory/alerts/?threshold=100')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] >= 1
        assert data['threshold'] == 100.0
        batch_ids = [r['batch_id'] for r in data['results']]
        assert 'LOWINV001' in batch_ids
        assert 'HIGHINV001' not in batch_ids

    def test_alerts_post(self, api_client, low_inventory):
        resp = api_client.post('/api/inventory/alerts/', {'threshold': 100}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] >= 1

    def test_alerts_filter_by_product_type(self, api_client, low_inventory, high_inventory):
        high_inventory.product_type = 'HONEY'
        high_inventory.save()
        resp = api_client.get('/api/inventory/alerts/?threshold=100&product_type=MILK')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['product_type'] == 'MILK'
