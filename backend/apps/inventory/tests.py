from decimal import Decimal

import pytest

from apps.inventory.models import Inventory


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
