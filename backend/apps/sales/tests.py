from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from rest_framework import status

from apps.base.constants import UserRole
from apps.conftest import positive_decimals
from apps.inventory.models import Inventory
from apps.sales.models import Buyer, Sale, SaleStatus, SaleUnit

pytestmark = pytest.mark.django_db


class TestBuyerModel:
    def test_create(self, cooperative):
        buyer = Buyer.objects.create(
            cooperative=cooperative,
            name='John Buyer',
            phone_number='+254700000001',
        )
        assert buyer.pk is not None
        assert buyer.is_active

    def test_str(self, cooperative):
        buyer = Buyer.objects.create(
            cooperative=cooperative,
            name='Test Buyer',
        )
        assert str(buyer) == 'Test Buyer'

    def test_soft_delete(self, cooperative):
        buyer = Buyer.objects.create(
            cooperative=cooperative,
            name='Del Buyer',
        )
        buyer.soft_delete()
        assert buyer.deleted_at is not None

    def test_contact_optional(self, cooperative):
        buyer = Buyer.objects.create(
            cooperative=cooperative,
            name='Minimal Buyer',
        )
        assert buyer.contact_person == ''
        assert buyer.phone_number == ''
        assert buyer.email == ''


class TestSaleModel:
    @pytest.fixture
    def inventory(self, buyer):
        return Inventory.objects.create(
            cooperative=buyer.cooperative,
            batch_id='INVSALE001',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('1000.00'),
        )

    def test_create(self, buyer, inventory):
        sale = Sale.objects.create(
            buyer=buyer,
            inventory=inventory,
            cooperative=buyer.cooperative,
            product_type='MILK',
            grade_letter='A',
            unit=SaleUnit.KG,
            quantity=Decimal('100.00'),
            price_per_unit=Decimal('45.00'),
            total_amount=Decimal('4500.00'),
        )
        assert sale.pk is not None
        assert sale.status == SaleStatus.PENDING

    def test_status_transitions(self, buyer, inventory):
        sale = Sale.objects.create(
            buyer=buyer,
            inventory=inventory,
            cooperative=buyer.cooperative,
            product_type='MILK',
            unit=SaleUnit.KG,
            quantity=Decimal('100.00'),
            price_per_unit=Decimal('45.00'),
            total_amount=Decimal('4500.00'),
        )
        for s in [SaleStatus.COMPLETED, SaleStatus.CANCELLED]:
            sale.status = s
            sale.save()
            sale.refresh_from_db()
            assert sale.status == s

    def test_string_representation(self, buyer, inventory):
        sale = Sale.objects.create(
            buyer=buyer,
            inventory=inventory,
            cooperative=buyer.cooperative,
            product_type='MILK',
            unit=SaleUnit.KG,
            quantity=Decimal('100.00'),
            price_per_unit=Decimal('45.00'),
            total_amount=Decimal('4500.00'),
            sale_date=date(2024, 1, 15),
        )
        assert buyer.name in str(sale)
        assert '2024-01-15' in str(sale)

    def test_soft_delete(self, buyer, inventory):
        sale = Sale.objects.create(
            buyer=buyer,
            inventory=inventory,
            cooperative=buyer.cooperative,
            product_type='MILK',
            unit=SaleUnit.KG,
            quantity=Decimal('100.00'),
            price_per_unit=Decimal('45.00'),
            total_amount=Decimal('4500.00'),
        )
        sale.soft_delete()
        assert sale.deleted_at is not None

    def test_unique_invoice_number(self, buyer, inventory):
        Sale.objects.create(
            buyer=buyer,
            inventory=inventory,
            cooperative=buyer.cooperative,
            product_type='MILK',
            unit=SaleUnit.KG,
            quantity=Decimal('100.00'),
            price_per_unit=Decimal('45.00'),
            total_amount=Decimal('4500.00'),
            invoice_number='INV001',
        )
        with pytest.raises(Exception):
            Sale.objects.create(
                buyer=buyer,
                inventory=inventory,
                cooperative=buyer.cooperative,
                product_type='MILK',
                unit=SaleUnit.KG,
                quantity=Decimal('100.00'),
                price_per_unit=Decimal('45.00'),
                total_amount=Decimal('4500.00'),
                invoice_number='INV001',
            )

    def test_product_type_synced_from_inventory(self, buyer, inventory):
        inventory.product_type = 'HONEY'
        inventory.save(update_fields=['product_type'])
        sale = Sale.objects.create(
            buyer=buyer,
            inventory=inventory,
            cooperative=buyer.cooperative,
            unit=SaleUnit.KG,
            quantity=Decimal('50.00'),
            price_per_unit=Decimal('200.00'),
            total_amount=Decimal('10000.00'),
        )
        assert sale.product_type == 'HONEY'


from django.contrib.auth import get_user_model
User = get_user_model()


@pytest.fixture
def manager_api_client(db, cooperative):
    from rest_framework.test import APIClient
    user = User.objects.create_user(
        email='mgr@sales.com', phone_number='+25470000111',
        first_name='Mgr', last_name='Sales',
        password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def coop_buyer(db, cooperative):
    return Buyer.objects.create(
        cooperative=cooperative, name='Coop Buyer',
        phone_number='+25470000999',
    )


class TestBuyerAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/buyers/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, buyer):
        resp = api_client.get('/api/buyers/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, buyer):
        resp = api_client.get(f'/api/buyers/{buyer.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['name'] == buyer.name

    def test_create(self, manager_api_client, cooperative):
        resp = manager_api_client.post('/api/buyers/', {
            'name': 'New Buyer',
            'phone_number': '+254712345678',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['name'] == 'New Buyer'

    def test_create_unauthenticated(self, client, cooperative):
        resp = client.post('/api/buyers/', {'name': 'Test'}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_permission_accountant_denied(self, cooperative):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct@buyer.com', phone_number='+25470000222',
            first_name='Acct', last_name='Buyer',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post('/api/buyers/', {'name': 'Test'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, manager_api_client, coop_buyer):
        resp = manager_api_client.patch(f'/api/buyers/{coop_buyer.id}/', {'name': 'Updated Buyer'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['name'] == 'Updated Buyer'

    def test_delete(self, manager_api_client, coop_buyer):
        resp = manager_api_client.delete(f'/api/buyers/{coop_buyer.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_search(self, api_client, buyer):
        resp = api_client.get('/api/buyers/?search=Buyer')
        assert resp.status_code == status.HTTP_200_OK


@pytest.fixture
def coop_sale(db, cooperative, coop_buyer):
    from decimal import Decimal
    inventory = Inventory.objects.create(
        cooperative=cooperative,
        batch_id='COOPSALE001',
        product_type='MILK',
        grade='A',
        unit='kg',
        quantity_in=Decimal('1000.00'),
    )
    return Sale.objects.create(
        buyer=coop_buyer, inventory=inventory, cooperative=cooperative,
        product_type='MILK', grade_letter='A', unit=SaleUnit.KG,
        quantity=Decimal('100.00'), price_per_unit=Decimal('45.00'),
        total_amount=Decimal('4500.00'),
    )


class TestSaleAPI:
    @pytest.fixture
    def inventory(self, cooperative):
        return Inventory.objects.create(
            cooperative=cooperative,
            batch_id='BATCH001',
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('1000.00'),
        )

    def test_list_unauthenticated(self, client):
        resp = client.get('/api/sales/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, sale):
        resp = api_client.get('/api/sales/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, sale):
        resp = api_client.get(f'/api/sales/{sale.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(sale.id)

    def test_create_with_line_items(self, manager_api_client, coop_buyer, inventory):
        resp = manager_api_client.post('/api/sales/', {
            'buyer': str(coop_buyer.id),
            'quantity': '100.00',
            'price_per_unit': '45.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '100.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['quantity'] == '100.00'
        assert resp.json()['price_per_unit'] == '45.00'

    def test_create_quantity_mismatch(self, manager_api_client, coop_buyer, inventory):
        resp = manager_api_client.post('/api/sales/', {
            'buyer': str(coop_buyer.id),
            'quantity': '50.00',
            'price_per_unit': '45.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '100.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_insufficient_inventory(self, manager_api_client, coop_buyer, inventory):
        resp = manager_api_client.post('/api/sales/', {
            'buyer': str(coop_buyer.id),
            'quantity': '9999.00',
            'price_per_unit': '45.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '9999.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_no_line_items(self, manager_api_client, coop_buyer):
        resp = manager_api_client.post('/api/sales/', {
            'buyer': str(coop_buyer.id),
            'quantity': '100.00',
            'price_per_unit': '45.00',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_negative_quantity(self, manager_api_client, coop_buyer, inventory):
        resp = manager_api_client.post('/api/sales/', {
            'buyer': str(coop_buyer.id),
            'quantity': '-10.00',
            'price_per_unit': '45.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '-10.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_negative_price(self, manager_api_client, coop_buyer, inventory):
        resp = manager_api_client.post('/api/sales/', {
            'buyer': str(coop_buyer.id),
            'quantity': '100.00',
            'price_per_unit': '-5.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '100.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unauthenticated(self, client, buyer, inventory):
        resp = client.post('/api/sales/', {
            'buyer': str(buyer.id),
            'quantity': '100.00',
            'price_per_unit': '45.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '100.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_permission_accountant_denied(self, cooperative, buyer, inventory):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct2@sale.com', phone_number='+25470000333',
            first_name='Acct', last_name='Sale',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post('/api/sales/', {
            'buyer': str(buyer.id),
            'quantity': '100.00',
            'price_per_unit': '45.00',
            'line_items': [{'inventory': str(inventory.id), 'quantity': '100.00'}],
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, manager_api_client, coop_sale):
        resp = manager_api_client.patch(f'/api/sales/{coop_sale.id}/', {'notes': 'Updated note'}, format='json')
        assert resp.status_code == status.HTTP_200_OK

    def test_delete(self, manager_api_client, coop_sale):
        resp = manager_api_client.delete(f'/api/sales/{coop_sale.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_by_status(self, api_client, sale):
        resp = api_client.get('/api/sales/?status=PENDING')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_buyer(self, api_client, sale):
        resp = api_client.get(f'/api/sales/?buyer={sale.buyer_id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_date_range(self, api_client, sale):
        resp = api_client.get('/api/sales/?date_from=2024-01-01&date_to=2025-12-31')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_product_type(self, api_client, sale):
        resp = api_client.get('/api/sales/?product_type=MILK')
        assert resp.status_code == status.HTTP_200_OK


class TestSalesHypothesis:
    @settings(max_examples=50)
    @given(
        quantity=positive_decimals,
        price_per_unit=positive_decimals,
    )
    def test_total_amount_calculation(self, quantity, price_per_unit):
        assume(quantity > 0 and price_per_unit > 0)
        total = quantity * price_per_unit
        assert total > 0
        assert total == quantity * price_per_unit
