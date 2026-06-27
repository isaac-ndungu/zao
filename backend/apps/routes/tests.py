from decimal import Decimal

import pytest
from rest_framework import status

from apps.base.constants import UserRole
from apps.routes.models import CollectionRoute, DayOfWeekChoices, RouteStop

pytestmark = pytest.mark.django_db


# =============================================================================
# CollectionRoute Model Tests
# =============================================================================

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


# =============================================================================
# Route API Endpoint Tests
# =============================================================================

from django.contrib.auth import get_user_model
User = get_user_model()


@pytest.fixture
def manager_api_client(db, cooperative):
    from rest_framework.test import APIClient
    manager = User.objects.create_user(
        'Test', 'User', email='manager@route.com', phone_number='+25470000999',
        password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=manager)
    return client


@pytest.fixture
def collection_route(db, cooperative):
    return CollectionRoute.objects.create(
        cooperative=cooperative,
        name='Test Route',
        path={'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]},
        day_of_week=DayOfWeekChoices.MONDAY,
    )


class TestRouteAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/routes/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, collection_route):
        resp = api_client.get('/api/routes/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, collection_route):
        resp = api_client.get(f'/api/routes/{collection_route.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(collection_route.id)

    def test_create(self, manager_api_client):
        resp = manager_api_client.post('/api/routes/', {
            'name': 'New Route',
            'path': {'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]},
            'day_of_week': 'MONDAY',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['name'] == 'New Route'

    def test_create_no_path(self, manager_api_client):
        resp = manager_api_client.post('/api/routes/', {'name': 'Bad Route'}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_wrong_path_type(self, manager_api_client):
        resp = manager_api_client.post('/api/routes/', {
            'name': 'Bad',
            'path': {'type': 'Point', 'coordinates': [36.8, -1.3]},
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_single_coordinate(self, manager_api_client):
        resp = manager_api_client.post('/api/routes/', {
            'name': 'Bad',
            'path': {'type': 'LineString', 'coordinates': [[36.8, -1.3]]},
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_invalid_day(self, manager_api_client):
        resp = manager_api_client.post('/api/routes/', {
            'name': 'Bad',
            'path': {'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]},
            'day_of_week': 'FUNDAY',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_unauthenticated(self, client):
        resp = client.post('/api/routes/', {
            'name': 'Test',
            'path': {'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]},
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_permission_accountant_denied(self, cooperative):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct@route.com', phone_number='+25470000111',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post('/api/routes/', {
            'name': 'Test',
            'path': {'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]},
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, manager_api_client, collection_route):
        resp = manager_api_client.patch(f'/api/routes/{collection_route.id}/',
                                        {'name': 'Updated Route'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['name'] == 'Updated Route'

    def test_delete(self, manager_api_client, collection_route):
        resp = manager_api_client.delete(f'/api/routes/{collection_route.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_is_active(self, api_client, collection_route):
        resp = api_client.get('/api/routes/?is_active=true')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_day_of_week(self, api_client, collection_route):
        resp = api_client.get('/api/routes/?day_of_week=MONDAY')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_invalid_day(self, api_client):
        resp = api_client.get('/api/routes/?day_of_week=INVALID')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 0


class TestRouteAssignStops:
    def test_assign_stops(self, manager_api_client, collection_route, farmer):
        resp = manager_api_client.post(f'/api/routes/{collection_route.id}/assign-stops/', {
            'stops': [{
                'farmer_ids': [str(farmer.id)],
                'latitude': '-1.283333',
                'longitude': '36.816667',
                'stop_order': 1,
                'estimated_minutes': 10,
            }],
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()['stops']) == 1

    def test_assign_multiple_stops(self, manager_api_client, collection_route, farmer):
        from apps.farmers.models import Farmer as FModel
        farmer2 = FModel.objects.create(
            first_name='F2', last_name='F2',
            id_number='RT002', phone_number='+25470000902',
            county='Nairobi', cooperative=collection_route.cooperative,
        )
        resp = manager_api_client.post(f'/api/routes/{collection_route.id}/assign-stops/', {
            'stops': [
                {'farmer_ids': [str(farmer.id)], 'latitude': '-1.28', 'longitude': '36.81', 'stop_order': 1},
                {'farmer_ids': [str(farmer2.id)], 'latitude': '-1.29', 'longitude': '36.82', 'stop_order': 2},
            ],
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()['stops']) == 2

    def test_assign_stops_invalid_order(self, manager_api_client, collection_route):
        resp = manager_api_client.post(f'/api/routes/{collection_route.id}/assign-stops/', {
            'stops': [
                {'farmer_ids': [], 'latitude': '-1.28', 'longitude': '36.81', 'stop_order': 2},
                {'farmer_ids': [], 'latitude': '-1.29', 'longitude': '36.82', 'stop_order': 1},
            ],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_stops_invalid_farmer(self, manager_api_client, collection_route):
        from uuid import uuid4
        resp = manager_api_client.post(f'/api/routes/{collection_route.id}/assign-stops/', {
            'stops': [{
                'farmer_ids': [str(uuid4())],
                'latitude': '-1.28',
                'longitude': '36.81',
                'stop_order': 1,
            }],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_stops_unauthenticated(self, client, collection_route):
        resp = client.post(f'/api/routes/{collection_route.id}/assign-stops/', {
            'stops': [],
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_assign_stops_permission_accountant_denied(self, cooperative, collection_route):
        from rest_framework.test import APIClient
        accountant = User.objects.create_user(
            email='acct2@route.com', phone_number='+25470000222',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        resp = client.post(f'/api/routes/{collection_route.id}/assign-stops/', {
            'stops': [{
                'farmer_ids': [],
                'latitude': '-1.28',
                'longitude': '36.81',
                'stop_order': 1,
            }],
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN
