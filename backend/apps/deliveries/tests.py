from decimal import Decimal

import pytest
from django.utils import timezone

from apps.deliveries.models import Delivery, DeliveryStatus, ProductType, Shift


class TestDeliveryModel:
    def test_create(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='BAT001',
            quantity_kg=Decimal('100.00'),
        )
        assert delivery.pk is not None
        assert delivery.status == DeliveryStatus.PENDING

    def test_str(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='BAT002',
        )
        assert 'BAT002' in str(delivery)
        assert ProductType.MILK in str(delivery)

    def test_default_status_pending(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.COFFEE_CHERRIES,
            batch_id='BAT003',
        )
        assert delivery.status == DeliveryStatus.PENDING

    def test_batch_id_unique(self, farmer):
        Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='UNIQUE',
        )
        with pytest.raises(Exception):
            Delivery.objects.create(
                farmer=farmer,
                cooperative=farmer.cooperative,
                product_type=ProductType.MILK,
                batch_id='UNIQUE',
            )

    def test_quantity_kg_can_be_null(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.HONEY,
            batch_id='BAT005',
        )
        assert delivery.quantity_kg is None

    def test_volume_litres(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='BAT006',
            volume_litres=Decimal('50.00'),
        )
        assert delivery.volume_litres == Decimal('50.00')

    def test_shift_choices(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='BAT007',
            shift=Shift.AM,
        )
        assert delivery.shift == Shift.AM

    def test_soft_delete(self, delivery):
        delivery.soft_delete()
        assert delivery.deleted_at is not None

    def test_status_transitions(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='BAT008',
        )
        delivery.status = DeliveryStatus.ACCEPTED
        delivery.save()
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.ACCEPTED

    def test_cooperative_scoped(self, farmer):
        delivery = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.OTHER,
            batch_id='BAT009',
        )
        assert delivery.cooperative == farmer.cooperative

    def test_ordering(self, farmer):
        d1 = Delivery.objects.create(
            farmer=farmer, cooperative=farmer.cooperative,
            product_type=ProductType.MILK, batch_id='ORD1',
        )
        d2 = Delivery.objects.create(
            farmer=farmer, cooperative=farmer.cooperative,
            product_type=ProductType.MILK, batch_id='ORD2',
        )
        deliveries = list(Delivery.objects.all())
        assert deliveries[0] == d2
        assert deliveries[1] == d1
