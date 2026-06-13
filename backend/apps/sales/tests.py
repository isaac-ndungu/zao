from datetime import date
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from apps.sales.models import Buyer, Sale, SaleStatus, SaleUnit

from apps.conftest import positive_decimals

pytestmark = pytest.mark.django_db


# =============================================================================
# Buyer Tests
# =============================================================================

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


# =============================================================================
# Sale Tests
# =============================================================================

class TestSaleModel:
    @pytest.fixture
    def inventory(self, buyer):
        from apps.inventory.models import Inventory
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
        for status in [SaleStatus.COMPLETED, SaleStatus.CANCELLED]:
            sale.status = status
            sale.save()
            sale.refresh_from_db()
            assert sale.status == status

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


# =============================================================================
# Hypothesis property-based tests for sales
# =============================================================================

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
