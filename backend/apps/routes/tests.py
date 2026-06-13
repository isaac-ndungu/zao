from decimal import Decimal

import pytest

from apps.routes.models import CollectionRoute, DayOfWeekChoices, RouteStop


class TestCollectionRoute:
    def test_create(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Route A',
            path={'type': 'LineString', 'coordinates': [[36.8, -1.3]]},
            day_of_week=DayOfWeekChoices.MONDAY,
        )
        assert route.pk is not None
        assert route.is_active

    def test_str(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Morning Route',
            path={},
        )
        assert str(route) == 'Morning Route'

    def test_estimated_distance(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Long Route',
            path={},
            estimated_distance_km=Decimal('15.50'),
        )
        assert route.estimated_distance_km == Decimal('15.50')

    def test_soft_delete(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Temp Route',
            path={},
        )
        route.soft_delete()
        assert route.deleted_at is not None


class TestRouteStop:
    def test_create(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Route with stops',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route,
            latitude=Decimal('-1.283333'),
            longitude=Decimal('36.816667'),
            stop_order=1,
            estimated_minutes=10,
        )
        assert stop.pk is not None

    def test_str(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Test Route',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route,
            latitude=Decimal('-1.300000'),
            longitude=Decimal('36.800000'),
            stop_order=1,
        )
        assert 'Test Route' in str(stop)
        assert 'Stop 1' in str(stop)

    def test_ordering(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Ordered Route',
            path={},
        )
        s1 = RouteStop.objects.create(route=route, latitude=0, longitude=0, stop_order=2)
        s2 = RouteStop.objects.create(route=route, latitude=0, longitude=0, stop_order=1)
        stops = list(RouteStop.objects.all())
        assert stops[0] == s2
        assert stops[1] == s1

    def test_unique_stop_order(self, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Unique Stops',
            path={},
        )
        RouteStop.objects.create(route=route, latitude=0, longitude=0, stop_order=1)
        with pytest.raises(Exception):
            RouteStop.objects.create(route=route, latitude=0, longitude=0, stop_order=1)

    def test_m2m_farmers(self, cooperative, farmer):
        route = CollectionRoute.objects.create(
            cooperative=cooperative,
            name='Route with farmers',
            path={},
        )
        stop = RouteStop.objects.create(
            route=route, latitude=0, longitude=0, stop_order=1,
        )
        stop.farmers.add(farmer)
        assert stop.farmers.count() == 1

    def test_day_of_week_from_string(self):
        assert DayOfWeekChoices.from_string('monday') == DayOfWeekChoices.MONDAY
        assert DayOfWeekChoices.from_string('FRIDAY') == DayOfWeekChoices.FRIDAY
