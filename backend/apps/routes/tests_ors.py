"""
Tests for the ORS proxy and routing helpers.

The proxy is an async view; we exercise it with ``AsyncClient`` and mock
the underlying ``httpx.Client`` so no real network calls are made.
"""
from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import AsyncClient
from rest_framework import status

from apps.routes.routing import (
    ORSConfigError,
    ORSClient,
    ORSNoRouteError,
    ORSRouteError,
    _cache_key,
    waypoints_from_payload,
)


pytestmark = pytest.mark.django_db


# =============================================================================
# Helpers
# =============================================================================


def _mock_response(json_body, status_code=200):
    """Build a mock httpx.Response-like object."""
    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self.text = json.dumps(json_body)

        def json(self):
            return json_body

    return _Resp()


def _ors_payload(coords=None, distance=1000.0, duration=600.0):
    coords = coords or [[36.1, -1.1], [36.2, -1.2], [36.3, -1.3]]
    return {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'geometry': {'type': 'LineString', 'coordinates': coords},
                'properties': {
                    'summary': {'distance': distance, 'duration': duration},
                },
            }
        ],
    }


# =============================================================================
# Routing helpers
# =============================================================================


class TestWaypointsFromPayload:
    def test_valid_payload(self):
        result = waypoints_from_payload([[36.1, -1.1], [36.2, -1.2]])
        assert result == [(-1.1, 36.1), (-1.2, 36.2)]

    def test_invalid_pair_shape(self):
        with pytest.raises(ORSRouteError):
            waypoints_from_payload([[36.1, -1.1], 'oops'])

    def test_longitude_out_of_range(self):
        with pytest.raises(ORSRouteError):
            waypoints_from_payload([[200.0, 0.0]])

    def test_latitude_out_of_range(self):
        with pytest.raises(ORSRouteError):
            waypoints_from_payload([[0.0, 100.0]])


class TestCacheKey:
    def test_deterministic(self):
        a = _cache_key('driving-car', [(-1.1, 36.1), (-1.2, 36.2)])
        b = _cache_key('driving-car', [(-1.1, 36.1), (-1.2, 36.2)])
        assert a == b

    def test_different_profiles_differ(self):
        a = _cache_key('driving-car', [(-1.1, 36.1)])
        b = _cache_key('cycling-regular', [(-1.1, 36.1)])
        assert a != b


# =============================================================================
# ORSClient
# =============================================================================


class TestORSClient:
    def test_from_settings_missing_key(self, settings):
        settings.ORS_API_KEY = ''
        with pytest.raises(ORSConfigError):
            ORSClient.from_settings()

    def test_from_settings_with_key(self, settings):
        settings.ORS_API_KEY = 'test-key'
        settings.ORS_BASE_URL = 'https://example.com'
        client = ORSClient.from_settings()
        assert client.api_key == 'test-key'
        assert client.base_url == 'https://example.com'

    def test_get_route_validates_profile(self, settings):
        settings.ORS_API_KEY = 'k'
        client = ORSClient.from_settings()
        with pytest.raises(ORSRouteError):
            client.get_route([(0.0, 0.0), (1.0, 1.0)], profile='rocket-ship')

    def test_get_route_validates_min_waypoints(self, settings):
        settings.ORS_API_KEY = 'k'
        client = ORSClient.from_settings()
        with pytest.raises(ORSRouteError):
            client.get_route([(0.0, 0.0)])

    def test_get_route_validates_max_waypoints(self, settings):
        settings.ORS_API_KEY = 'k'
        client = ORSClient.from_settings()
        with pytest.raises(ORSRouteError):
            client.get_route([(0.0, 0.0)] * 51)

    def test_get_route_success(self, settings):
        settings.ORS_API_KEY = 'k'
        client = ORSClient.from_settings()
        with patch('apps.routes.routing.httpx.Client') as MockClient:
            mock_instance = MockClient.return_value.__enter__.return_value
            mock_instance.post.return_value = _mock_response(_ors_payload())
            data = client.get_route([(-1.1, 36.1), (-1.2, 36.2)], use_cache=False)
        assert data['type'] == 'FeatureCollection'
        assert data['distance_m'] == 1000.0
        assert data['duration_s'] == 600.0
        assert len(data['geometry']['coordinates']) == 3

    def test_get_route_no_features(self, settings):
        settings.ORS_API_KEY = 'k'
        client = ORSClient.from_settings()
        with patch('apps.routes.routing.httpx.Client') as MockClient:
            mock_instance = MockClient.return_value.__enter__.return_value
            mock_instance.post.return_value = _mock_response({'type': 'FeatureCollection', 'features': []})
            with pytest.raises(ORSNoRouteError):
                client.get_route([(-1.1, 36.1), (-1.2, 36.2)], use_cache=False)

    def test_get_route_4xx(self, settings):
        settings.ORS_API_KEY = 'bad'
        client = ORSClient.from_settings()
        with patch('apps.routes.routing.httpx.Client') as MockClient:
            mock_instance = MockClient.return_value.__enter__.return_value
            mock_instance.post.return_value = _mock_response({'error': 'invalid'}, status_code=401)
            with pytest.raises(ORSRouteError) as exc:
                client.get_route([(-1.1, 36.1), (-1.2, 36.2)], use_cache=False)
            assert exc.value.status_code == 401

    def test_get_route_cache_hit_skips_request(self, settings):
        settings.ORS_API_KEY = 'k'
        client = ORSClient.from_settings()
        from django.core.cache import cache
        cache.clear()
        # Pre-populate the cache with the *wrapped* response shape.
        cached = {
            'type': 'FeatureCollection',
            'features': _ors_payload(distance=999.0)['features'],
            'distance_m': 999.0,
            'duration_s': 600.0,
            'geometry': {'type': 'LineString', 'coordinates': [[36.1, -1.1], [36.2, -1.2]]},
        }
        cache.set(_cache_key('driving-car', [(-1.1, 36.1), (-1.2, 36.2)]), cached, timeout=60)
        with patch('apps.routes.routing.httpx.Client') as MockClient:
            data = client.get_route([(-1.1, 36.1), (-1.2, 36.2)])
        assert data['distance_m'] == 999.0
        MockClient.assert_not_called()


# =============================================================================
# Async proxy view
# =============================================================================


@pytest.fixture
def async_client():
    return AsyncClient()


@pytest.fixture
def api_user(db):
    from django.contrib.auth import get_user_model
    from apps.base.constants import UserRole
    User = get_user_model()
    return User.objects.create_user(
        'api@test.com', '+25470008888', 'Api', 'User',
        password='testpass123', role=UserRole.MANAGER,
    )


@pytest.fixture
def auth_headers(api_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(api_user)
    return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}


@pytest.fixture
def auth_async_client(api_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = AsyncClient()
    refresh = RefreshToken.for_user(api_user)
    token = f'Bearer {refresh.access_token}'
    # Store on the client; tests pass `headers=` per-request.
    client._auth_header = token
    return client


class TestRouteProxyView:
    def test_unauthenticated_rejected(self, client):
        resp = client.post(
            '/api/routes/route/',
            data=json.dumps({'waypoints': [[36.1, -1.1], [36.2, -1.2]]}),
            content_type='application/json',
        )
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_get_method_not_allowed(self, api_client):
        resp = api_client.get('/api/routes/route/')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_invalid_json_body(self, api_client):
        resp = api_client.post(
            '/api/routes/route/', data='not json', content_type='application/json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_waypoints(self, api_client, settings):
        settings.ORS_API_KEY = 'k'
        resp = api_client.post(
            '/api/routes/route/',
            data=json.dumps({'waypoints': []}),
            content_type='application/json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_ors_key_returns_503(self, api_client, settings):
        settings.ORS_API_KEY = ''
        resp = api_client.post(
            '/api/routes/route/',
            data=json.dumps({'waypoints': [[36.1, -1.1], [36.2, -1.2]]}),
            content_type='application/json',
        )
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_invalid_coords(self, api_client, settings):
        settings.ORS_API_KEY = 'k'
        resp = api_client.post(
            '/api/routes/route/',
            data=json.dumps({'waypoints': [[200, 0], [0, 0]]}),
            content_type='application/json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_success(self, api_client, settings):
        settings.ORS_API_KEY = 'k'
        from django.core.cache import cache
        cache.clear()
        with patch('apps.routes.routing.httpx.Client') as MockClient:
            mock_instance = MockClient.return_value.__enter__.return_value
            mock_instance.post.return_value = _mock_response(_ors_payload())
            resp = api_client.post(
                '/api/routes/route/',
                data=json.dumps({'waypoints': [[36.1, -1.1], [36.2, -1.2], [36.3, -1.3]]}),
                content_type='application/json',
            )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        body = resp.json()
        assert body['type'] == 'FeatureCollection'
        assert body['distance_m'] == 1000.0

    def test_upstream_error_returns_502(self, api_client, settings):
        settings.ORS_API_KEY = 'k'
        from django.core.cache import cache
        cache.clear()
        with patch('apps.routes.routing.httpx.Client') as MockClient:
            mock_instance = MockClient.return_value.__enter__.return_value
            mock_instance.post.return_value = _mock_response({'error': 'oops'}, status_code=500)
            resp = api_client.post(
                '/api/routes/route/',
                data=json.dumps({'waypoints': [[36.1, -1.1], [36.2, -1.2]]}),
                content_type='application/json',
            )
        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
