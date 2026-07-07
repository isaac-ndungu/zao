from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.deliveries.models import Delivery, DeliveryStatus, ProductType, Shift
from apps.routes.models import CollectionRoute, RouteStop


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


class TestDeliveryAutoFillLocation:
    def test_picks_route_stop_coordinates(self, farmer):
        route = CollectionRoute.objects.create(
            cooperative=farmer.cooperative,
            name='Morning',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route,
            latitude=Decimal('1.234567'),
            longitude=Decimal('36.789012'),
            stop_order=1,
        )
        d = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='LOC1',
            route_stop=stop,
        )
        assert d.latitude == Decimal('1.234567')
        assert d.longitude == Decimal('36.789012')

    def test_falls_back_to_farmer_coordinates(self, farmer):
        farmer.latitude = Decimal('-1.300000')
        farmer.longitude = Decimal('36.800000')
        farmer.save(update_fields=['latitude', 'longitude'])
        d = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='LOC2',
        )
        assert d.latitude == Decimal('-1.300000')
        assert d.longitude == Decimal('36.800000')

    def test_explicit_coordinates_win(self, farmer):
        farmer.latitude = Decimal('-1.300000')
        farmer.longitude = Decimal('36.800000')
        farmer.save(update_fields=['latitude', 'longitude'])
        d = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='LOC3',
            latitude=Decimal('2.5'),
            longitude=Decimal('37.5'),
        )
        assert d.latitude == Decimal('2.5')
        assert d.longitude == Decimal('37.5')

    def test_route_stop_takes_priority_over_farmer(self, farmer):
        farmer.latitude = Decimal('-1.300000')
        farmer.longitude = Decimal('36.800000')
        farmer.save(update_fields=['latitude', 'longitude'])
        route = CollectionRoute.objects.create(
            cooperative=farmer.cooperative,
            name='Priority',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route,
            latitude=Decimal('0.000001'),
            longitude=Decimal('0.000002'),
            stop_order=1,
        )
        d = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='LOC4',
            route_stop=stop,
        )
        assert d.latitude == Decimal('0.000001')
        assert d.longitude == Decimal('0.000002')

    def test_no_source_leaves_blank(self, farmer):
        d = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='LOC5',
        )
        assert d.latitude is None
        assert d.longitude is None


class TestDeliveryViewSetRouteStopFilter:
    def test_filter_by_route_stop(self, api_client, farmer):
        route = CollectionRoute.objects.create(
            cooperative=farmer.cooperative,
            name='FilterRoute',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route,
            latitude=Decimal('0'),
            longitude=Decimal('0'),
            stop_order=1,
        )
        d_with = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='FILT1',
            route_stop=stop,
        )
        Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='FILT2',
        )
        resp = api_client.get(f'/api/deliveries/?route_stop={stop.id}')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ids = [r['id'] for r in data.get('results', data)]
        assert str(d_with.id) in ids
        assert len([i for i in ids if 'FILT1' in str(i) or i == str(d_with.id)]) >= 1

    def test_filter_by_route(self, api_client, farmer):
        route = CollectionRoute.objects.create(
            cooperative=farmer.cooperative,
            name='RouteFilter',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route,
            latitude=Decimal('0'),
            longitude=Decimal('0'),
            stop_order=1,
        )
        d = Delivery.objects.create(
            farmer=farmer,
            cooperative=farmer.cooperative,
            product_type=ProductType.MILK,
            batch_id='FILT3',
            route_stop=stop,
        )
        resp = api_client.get(f'/api/deliveries/?route={route.id}')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ids = [r['id'] for r in data.get('results', data)]
        assert str(d.id) in ids
