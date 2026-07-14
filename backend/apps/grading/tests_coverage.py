from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.conftest import (
    CooperativeFactory,
    DeliveryFactory,
    GradeFactory,
    PaymentCycleFactory,
)
from apps.deliveries.models import ProductType
from apps.inventory.models import Inventory, Stock
from apps.payment_engine.models import ComputationWarning, PaymentCycle
from apps.grading.models import Grade
from apps.grading.tasks import update_inventory_on_grade

pytestmark = pytest.mark.django_db


@pytest.fixture
def cooperative():
    return CooperativeFactory()


@pytest.fixture
def delivery(cooperative):
    return DeliveryFactory(
        cooperative=cooperative,
        product_type=ProductType.MILK,
        quantity_kg=None,
        volume_litres=Decimal('200.00'),
    )


@pytest.fixture
def payment_cycle(cooperative, delivery):
    return PaymentCycleFactory(
        cooperative=cooperative,
        start_date=delivery.date_delivered.date(),
        end_date=delivery.date_delivered.date(),
    )


@pytest.fixture
def grade(delivery, cooperative):
    return GradeFactory(
        delivery=delivery,
        cooperative=cooperative,
        grade_letter='A',
        is_inventory_updated=False,
    )


# =============================================================================
# update_inventory_on_grade
# =============================================================================


class TestUpdateInventoryOnGrade:
    def test_already_processed_skips(self, grade):
        grade.is_inventory_updated = True
        grade.save(update_fields=['is_inventory_updated'])

        result = update_inventory_on_grade(str(grade.id))

        assert result['status'] == 'skipped'

    def test_no_payment_cycle_returns_error(self, delivery, cooperative):
        grade = GradeFactory(
            delivery=delivery,
            cooperative=cooperative,
            grade_letter='B',
            is_inventory_updated=False,
        )

        result = update_inventory_on_grade(str(grade.id))

        assert result['status'] == 'error'
        assert 'no cycle' in result['reason']
        assert ComputationWarning.objects.filter(
            cooperative=cooperative, severity='ERROR',
        ).exists()

    def test_new_pool_creation(self, grade, payment_cycle):
        result = update_inventory_on_grade(str(grade.id))

        assert result is None

        pool = Inventory.objects.get(
            cooperative=grade.cooperative,
            payment_cycle=payment_cycle,
            product_type=ProductType.MILK,
            grade='A',
        )
        assert pool.quantity_in == Decimal('200.00')
        assert pool.unit == 'litres'
        assert pool.is_sold is False

        grade.refresh_from_db()
        assert grade.is_inventory_updated is True

    def test_existing_pool_increments(self, grade, payment_cycle):
        update_inventory_on_grade(str(grade.id))

        grade.is_inventory_updated = False
        grade.save(update_fields=['is_inventory_updated'])
        update_inventory_on_grade(str(grade.id))

        pool = Inventory.objects.get(
            cooperative=grade.cooperative,
            payment_cycle=payment_cycle,
            product_type=ProductType.MILK,
            grade='A',
        )
        assert pool.quantity_in == Decimal('400.00')

    def test_stock_aggregate_creation(self, grade, payment_cycle):
        result = update_inventory_on_grade(str(grade.id))

        stock = Stock.objects.get(
            cooperative=grade.cooperative,
            product_type=ProductType.MILK,
            grade='A',
        )
        assert stock.quantity_available == Decimal('400.00')
        assert stock.unit == 'litres'

    def test_stock_aggregate_update(self, grade, payment_cycle):
        update_inventory_on_grade(str(grade.id))

        grade.is_inventory_updated = False
        grade.save(update_fields=['is_inventory_updated'])
        update_inventory_on_grade(str(grade.id))

        stock = Stock.objects.get(
            cooperative=grade.cooperative,
            product_type=ProductType.MILK,
            grade='A',
        )
        assert stock.quantity_available == Decimal('600.00')

    def test_does_not_raise_on_nonexistent_grade(self):
        result = update_inventory_on_grade('00000000-0000-0000-0000-000000000000')

        assert result is None

    def test_grade_with_explicit_payment_cycle(self, grade, cooperative):
        explicit_cycle = PaymentCycleFactory(
            cooperative=cooperative,
            start_date=grade.delivery.date_delivered.date(),
            end_date=grade.delivery.date_delivered.date(),
        )
        grade.payment_cycle = explicit_cycle
        grade.save(update_fields=['payment_cycle'])

        result = update_inventory_on_grade(str(grade.id))

        pool = Inventory.objects.get(
            cooperative=cooperative,
            payment_cycle=explicit_cycle,
            product_type=ProductType.MILK,
            grade='A',
        )
        assert pool.quantity_in == Decimal('200.00')

    def test_kg_product_type(self, cooperative):
        delivery = DeliveryFactory(
            cooperative=cooperative,
            product_type=ProductType.COFFEE_CHERRIES,
            quantity_kg=Decimal('150.00'),
            volume_litres=None,
        )
        PaymentCycleFactory(
            cooperative=cooperative,
            start_date=delivery.date_delivered.date(),
            end_date=delivery.date_delivered.date(),
        )
        grade = GradeFactory(
            delivery=delivery,
            cooperative=cooperative,
            grade_letter='B',
            is_inventory_updated=False,
        )

        update_inventory_on_grade(str(grade.id))

        pool = Inventory.objects.get(
            cooperative=cooperative,
            product_type=ProductType.COFFEE_CHERRIES,
            grade='B',
        )
        assert pool.unit == 'kg'
        assert pool.quantity_in == Decimal('150.00')

        stock = Stock.objects.get(
            cooperative=cooperative,
            product_type=ProductType.COFFEE_CHERRIES,
            grade='B',
        )
        assert stock.quantity_available == Decimal('300.00')
        assert stock.unit == 'kg'

    def test_unit_mismatch_raises_valueerror(self, grade, payment_cycle):
        Stock.objects.create(
            cooperative=grade.cooperative,
            product_type=ProductType.MILK,
            grade='A',
            unit='kg',
            quantity_available=Decimal('100.00'),
        )

        with pytest.raises(ValueError, match='Unit mismatch'):
            update_inventory_on_grade(str(grade.id))
