from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.conftest import (
    BuyerFactory,
    CooperativeFactory,
    InventoryFactory,
    PaymentCycleFactory,
    SaleFactory,
)
from apps.inventory.models import Inventory, Stock
from apps.sales.models import Sale, SaleInventoryLineItem
from apps.sales.tasks import decrement_inventory_on_sale, reverse_inventory_on_cancellation

pytestmark = pytest.mark.django_db


@pytest.fixture
def cooperative():
    return CooperativeFactory()


@pytest.fixture
def stock(cooperative):
    return Stock.objects.create(
        cooperative=cooperative,
        product_type='MILK',
        grade='A',
        unit='kg',
        quantity_available=Decimal('500.00'),
    )


@pytest.fixture
def buyer(cooperative):
    return BuyerFactory(cooperative=cooperative)


@pytest.fixture
def sale(buyer, stock):
    return SaleFactory(
        buyer=buyer,
        cooperative=buyer.cooperative,
        stock=stock,
        product_type='MILK',
        grade_letter='A',
        unit='kg',
        quantity=Decimal('50.00'),
        price_per_unit=Decimal('45.00'),
        total_amount=Decimal('2250.00'),
        inventory_updated=False,
    )


@pytest.fixture
def payment_cycle(cooperative):
    return PaymentCycleFactory(cooperative=cooperative)


@pytest.fixture
def inventory_pool(cooperative, payment_cycle):
    return InventoryFactory(
        cooperative=cooperative,
        payment_cycle=payment_cycle,
        product_type='MILK',
        grade='A',
        unit='kg',
        quantity_in=Decimal('300.00'),
        quantity_out=Decimal('0.00'),
    )


# =============================================================================
# decrement_inventory_on_sale
# =============================================================================


class TestDecrementInventoryOnSale:
    def test_already_decremented_skips(self, sale):
        sale.inventory_updated = True
        sale.save(update_fields=['inventory_updated'])

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'skipped'

    def test_no_stock_id_skips(self, buyer):
        sale = SaleFactory(
            buyer=buyer,
            cooperative=buyer.cooperative,
            stock=None,
            quantity=Decimal('50.00'),
            inventory_updated=False,
        )

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'skipped'
        assert 'No stock' in result['reason']

    def test_zero_quantity_skips(self, sale):
        sale.quantity = Decimal('0.00')
        sale.save(update_fields=['quantity'])

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'skipped'

    def test_negative_quantity_skips(self, sale):
        sale.quantity = Decimal('-10.00')
        sale.save(update_fields=['quantity'])

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'skipped'

    def test_successful_single_pool(self, sale, inventory_pool, stock):
        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'ok'
        assert result['line_items'] == 1

        sale.refresh_from_db()
        assert sale.inventory_updated is True

        inventory_pool.refresh_from_db()
        assert inventory_pool.quantity_out == Decimal('50.00')

        stock.refresh_from_db()
        assert stock.quantity_available == Decimal('450.00')

        assert SaleInventoryLineItem.objects.filter(sale=sale).count() == 1

    def test_successful_multiple_pools_fifo(self, cooperative, buyer, stock):
        cycle1 = PaymentCycleFactory(cooperative=cooperative)
        cycle2 = PaymentCycleFactory(cooperative=cooperative)

        pool1 = InventoryFactory(
            cooperative=cooperative,
            payment_cycle=cycle1,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('20.00'),
            quantity_out=Decimal('0.00'),
        )
        pool2 = InventoryFactory(
            cooperative=cooperative,
            payment_cycle=cycle2,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('40.00'),
            quantity_out=Decimal('0.00'),
        )

        sale = SaleFactory(
            buyer=buyer,
            cooperative=cooperative,
            stock=stock,
            product_type='MILK',
            grade_letter='A',
            unit='kg',
            quantity=Decimal('50.00'),
            total_amount=Decimal('2250.00'),
            inventory_updated=False,
        )

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'ok'
        assert result['line_items'] == 2

        pool1.refresh_from_db()
        assert pool1.quantity_out == Decimal('20.00')
        assert pool1.is_sold is True

        pool2.refresh_from_db()
        assert pool2.quantity_out == Decimal('30.00')
        assert pool2.is_sold is False

        stock.refresh_from_db()
        assert stock.quantity_available == Decimal('450.00')

        sale.refresh_from_db()
        assert sale.inventory_updated is True
        assert sale.payment_cycle_id == cycle1.id

    def test_insufficient_stock(self, cooperative, buyer, stock, payment_cycle):
        pool = InventoryFactory(
            cooperative=cooperative,
            payment_cycle=payment_cycle,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('10.00'),
            quantity_out=Decimal('0.00'),
        )
        sale = SaleFactory(
            buyer=buyer,
            cooperative=cooperative,
            stock=stock,
            product_type='MILK',
            grade_letter='A',
            unit='kg',
            quantity=Decimal('100.00'),
            total_amount=Decimal('4500.00'),
            inventory_updated=False,
        )

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'error'
        assert result['short'] == 90.0

        sale.refresh_from_db()
        assert sale.inventory_updated is False

    def test_does_not_raise_on_nonexistent_sale(self):
        result = decrement_inventory_on_sale('00000000-0000-0000-0000-000000000000')

        assert result is None

    def test_assigns_payment_cycle_from_pool(self, sale, inventory_pool, stock):
        sale.payment_cycle = None
        sale.save(update_fields=['payment_cycle'])

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'ok'
        sale.refresh_from_db()
        assert sale.payment_cycle_id == inventory_pool.payment_cycle_id

    def test_pool_with_no_available_skipped(self, cooperative, buyer, stock):
        InventoryFactory(
            cooperative=cooperative,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('100.00'),
            quantity_out=Decimal('100.00'),
        )
        sale = SaleFactory(
            buyer=buyer,
            cooperative=cooperative,
            stock=stock,
            product_type='MILK',
            grade_letter='A',
            unit='kg',
            quantity=Decimal('50.00'),
            total_amount=Decimal('2250.00'),
            inventory_updated=False,
        )

        result = decrement_inventory_on_sale(str(sale.id))

        assert result['status'] == 'error'


# =============================================================================
# reverse_inventory_on_cancellation
# =============================================================================


class TestReverseInventoryOnCancellation:
    def test_already_reversed_skips(self, sale):
        sale.inventory_updated = False
        sale.save(update_fields=['inventory_updated'])

        result = reverse_inventory_on_cancellation(str(sale.id))

        assert result['status'] == 'skipped'

    def test_successful_reverse(self, sale, inventory_pool, stock):
        decrement_inventory_on_sale(str(sale.id))

        sale.refresh_from_db()
        inventory_pool.refresh_from_db()
        stock.refresh_from_db()

        old_qty_out = inventory_pool.quantity_out
        old_stock_qty = stock.quantity_available
        line_item_count = SaleInventoryLineItem.objects.filter(sale=sale).count()

        result = reverse_inventory_on_cancellation(str(sale.id))

        assert result is None

        sale.refresh_from_db()
        assert sale.inventory_updated is False
        assert SaleInventoryLineItem.objects.filter(sale=sale).count() == 0

        inventory_pool.refresh_from_db()
        assert inventory_pool.quantity_out == old_qty_out - sale.quantity

        stock.refresh_from_db()
        assert stock.quantity_available == old_stock_qty + sale.quantity

    def test_reverse_restores_pool_is_sold(self, cooperative, buyer, stock):
        cycle = PaymentCycleFactory(cooperative=cooperative)
        pool = InventoryFactory(
            cooperative=cooperative,
            payment_cycle=cycle,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('50.00'),
            quantity_out=Decimal('0.00'),
        )
        sale = SaleFactory(
            buyer=buyer,
            cooperative=cooperative,
            stock=stock,
            product_type='MILK',
            grade_letter='A',
            unit='kg',
            quantity=Decimal('50.00'),
            total_amount=Decimal('2250.00'),
            inventory_updated=False,
        )

        decrement_inventory_on_sale(str(sale.id))
        pool.refresh_from_db()
        assert pool.is_sold is True

        reverse_inventory_on_cancellation(str(sale.id))
        pool.refresh_from_db()
        assert pool.is_sold is True

    def test_does_not_raise_on_nonexistent_sale(self):
        result = reverse_inventory_on_cancellation('00000000-0000-0000-0000-000000000000')

        assert result is None

    def test_reverse_with_no_stock_id(self, cooperative, buyer, payment_cycle):
        pool = InventoryFactory(
            cooperative=cooperative,
            payment_cycle=payment_cycle,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_in=Decimal('100.00'),
            quantity_out=Decimal('0.00'),
        )
        stock = Stock.objects.create(
            cooperative=cooperative,
            product_type='MILK',
            grade='A',
            unit='kg',
            quantity_available=Decimal('500.00'),
        )
        sale = SaleFactory(
            buyer=buyer,
            cooperative=cooperative,
            stock=stock,
            product_type='MILK',
            grade_letter='A',
            unit='kg',
            quantity=Decimal('50.00'),
            total_amount=Decimal('2250.00'),
            inventory_updated=False,
        )

        decrement_inventory_on_sale(str(sale.id))
        sale.refresh_from_db()
        assert sale.inventory_updated is True

        sale.stock = None
        sale.save(update_fields=['stock'])

        result = reverse_inventory_on_cancellation(str(sale.id))

        assert result is None
        sale.refresh_from_db()
        assert sale.inventory_updated is False
        assert SaleInventoryLineItem.objects.filter(sale=sale).count() == 0
