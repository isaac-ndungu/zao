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
        'manager@route.com', '+25470000999', 'Test', 'User',
        password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=manager)
    return client


@pytest.fixture
def grader_api_client(db, cooperative):
    from rest_framework.test import APIClient
    grader = User.objects.create_user(
        'grader@route.com', '+25470000777', 'Grader', 'User',
        password='testpass123', role=UserRole.GRADER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=grader)
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
        assert resp.json()['id'] == collection_route.id

    def test_create(self, manager_api_client):
        resp = manager_api_client.post('/api/routes/', {
            'name': 'New Route',
            'path': {'type': 'LineString', 'coordinates': [[36.8, -1.3], [36.9, -1.2]]},
            'day_of_week': 'MONDAY',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['name'] == 'New Route'

    def test_create_no_path(self, manager_api_client):
        # Path is now optional at create time; it auto-builds from stops.
        resp = manager_api_client.post('/api/routes/', {'name': 'Empty Path'}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['path'] in ({}, '')

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
            'acct@route.com', '+25470000111', 'Acct', 'User',
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
        assert len(resp.json()['results']) == 0


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
            'acct2@route.com', '+25470000222', 'Acct2', 'User',
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


# =============================================================================
# Map, assign-farmer, unassign-farmer, path auto-build
# =============================================================================


def _make_route_with_stops(cooperative, count=2):
    route = CollectionRoute.objects.create(
        cooperative=cooperative, name='Stops Route', path={},
    )
    stops = []
    for i in range(1, count + 1):
        stops.append(RouteStop.objects.create(
            route=route,
            latitude=Decimal(f'-1.{i}00000'),
            longitude=Decimal(f'36.{i}00000'),
            stop_order=i,
            estimated_minutes=10 * i,
        ))
    return route, stops


class TestRouteMap:
    def test_map_returns_stops_and_farmers(self, api_client, collection_route, farmer):
        stop = RouteStop.objects.create(
            route=collection_route, latitude=0, longitude=0, stop_order=1,
        )
        stop.farmers.add(farmer)
        resp = api_client.get(f'/api/routes/{collection_route.id}/map/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['id'] == collection_route.id
        assert len(data['stops']) == 1
        assert data['stops'][0]['order'] == 1
        assert len(data['stops'][0]['farmers']) == 1
        assert data['stops'][0]['farmers'][0]['id'] == str(farmer.id)

    def test_map_unauthenticated(self, client, collection_route):
        resp = client.get(f'/api/routes/{collection_route.id}/map/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestRouteAssignFarmer:
    def test_assign_farmer_to_stop(self, manager_api_client, farmer, cooperative):
        route, stops = _make_route_with_stops(cooperative, count=2)
        resp = manager_api_client.post(
            f'/api/routes/{route.id}/assign-farmer/',
            {'farmer_id': str(farmer.id), 'stop_id': stops[1].id},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert stops[1].farmers.filter(id=farmer.id).exists()
        assert not stops[0].farmers.filter(id=farmer.id).exists()

    def test_assign_farmer_moves_farmer_between_stops(self, manager_api_client, farmer, cooperative):
        route, stops = _make_route_with_stops(cooperative, count=2)
        stops[0].farmers.add(farmer)
        resp = manager_api_client.post(
            f'/api/routes/{route.id}/assign-farmer/',
            {'farmer_id': str(farmer.id), 'stop_id': stops[1].id},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert stops[1].farmers.filter(id=farmer.id).exists()

    def test_assign_farmer_invalid_stop(self, manager_api_client, farmer, cooperative):
        route, _ = _make_route_with_stops(cooperative, count=1)
        resp = manager_api_client.post(
            f'/api/routes/{route.id}/assign-farmer/',
            {'farmer_id': str(farmer.id), 'stop_id': 99999},
            format='json',
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_farmer_invalid_farmer(self, manager_api_client, cooperative):
        from uuid import uuid4
        route, stops = _make_route_with_stops(cooperative, count=1)
        resp = manager_api_client.post(
            f'/api/routes/{route.id}/assign-farmer/',
            {'farmer_id': str(uuid4()), 'stop_id': stops[0].id},
            format='json',
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_farmer_as_grader_allowed(self, grader_api_client, farmer, cooperative):
        route, stops = _make_route_with_stops(cooperative, count=1)
        resp = grader_api_client.post(
            f'/api/routes/{route.id}/assign-farmer/',
            {'farmer_id': str(farmer.id), 'stop_id': stops[0].id},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK


class TestRouteUnassignFarmer:
    def test_unassign_farmer(self, manager_api_client, farmer, cooperative):
        route, stops = _make_route_with_stops(cooperative, count=1)
        stops[0].farmers.add(farmer)
        resp = manager_api_client.post(
            f'/api/routes/{route.id}/unassign-farmer/',
            {'farmer_id': str(farmer.id)},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert not stops[0].farmers.filter(id=farmer.id).exists()

    def test_unassign_farmer_not_on_route(self, manager_api_client, farmer, cooperative):
        route, _ = _make_route_with_stops(cooperative, count=1)
        resp = manager_api_client.post(
            f'/api/routes/{route.id}/unassign-farmer/',
            {'farmer_id': str(farmer.id)},
            format='json',
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestRoutePathAutoBuild:
    def test_create_with_empty_path_autofills_from_stops(self, manager_api_client, cooperative):
        route = CollectionRoute.objects.create(
            cooperative=cooperative, name='Empty', path={},
        )
        RouteStop.objects.create(route=route, latitude=Decimal('1.0'), longitude=Decimal('36.0'), stop_order=1)
        RouteStop.objects.create(route=route, latitude=Decimal('2.0'), longitude=Decimal('37.0'), stop_order=2)
        # Trigger via serializer
        from apps.routes.views import RouteViewSet
        view = RouteViewSet()
        view._autofill_path(route)
        route.refresh_from_db()
        assert route.path['type'] == 'LineString'
        assert len(route.path['coordinates']) == 2
        assert route.path['coordinates'][0] == [36.0, 1.0]
        assert route.path['coordinates'][1] == [37.0, 2.0]

    def test_create_with_existing_path_unchanged(self, manager_api_client, collection_route):
        existing = collection_route.path
        from apps.routes.views import RouteViewSet
        view = RouteViewSet()
        view._autofill_path(collection_route)
        collection_route.refresh_from_db()
        assert collection_route.path == existing

    def test_assign_stops_autofills_path(self, manager_api_client, collection_route, farmer):
        from apps.farmers.models import Farmer as FModel
        farmer2 = FModel.objects.create(
            first_name='F2', last_name='P',
            id_number='RT002A', phone_number='+25470000903',
            county='Nairobi', cooperative=collection_route.cooperative,
        )
        # Use a fresh route with empty path to verify auto-build.
        empty_route = CollectionRoute.objects.create(
            cooperative=collection_route.cooperative,
            name='Empty For Auto',
            path={},
        )
        resp = manager_api_client.post(
            f'/api/routes/{empty_route.id}/assign-stops/',
            {
                'stops': [
                    {'farmer_ids': [str(farmer.id)], 'latitude': '-1.10', 'longitude': '36.10', 'stop_order': 1},
                    {'farmer_ids': [str(farmer2.id)], 'latitude': '-1.20', 'longitude': '36.20', 'stop_order': 2},
                ],
            },
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        empty_route.refresh_from_db()
        assert empty_route.path['type'] == 'LineString'
        first = empty_route.path['coordinates'][0]
        assert abs(first[0] - 36.1) < 1e-6
        assert abs(first[1] - (-1.1)) < 1e-6
