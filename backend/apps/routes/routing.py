"""
OpenRouteService proxy: caches + forwards route requests so the
``ORS_API_KEY`` never reaches the browser, and so the response shape is
stable for both raw GeoJSON consumers and the leaflet-routing-machine
custom router on the frontend.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Iterable

import httpx
from django.conf import settings
from django.core.cache import cache
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ORSConfigError(Exception):
    """Raised when ORS_API_KEY is missing."""


class ORSRouteError(Exception):
    """Raised when ORS returns a non-success status (other than 429)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f'ORS error {status_code}: {detail}')


class ORSNoRouteError(Exception):
    """Raised when ORS returns 200 but no usable geometry."""


VALID_PROFILES = frozenset({
    'driving-car',
    'driving-hgv',
    'cycling-regular',
    'foot-walking',
})


def _normalize_waypoint(lat: float, lng: float) -> tuple[float, float]:
    """Round to 6 decimals to maximise cache hits for nearby waypoints."""
    return (round(float(lat), 6), round(float(lng), 6))


def _cache_key(profile: str, waypoints: list[tuple[float, float]]) -> str:
    payload = json.dumps(
        {'profile': profile, 'waypoints': waypoints},
        sort_keys=True, separators=(',', ':'),
    )
    return f'ors:route:{hashlib.sha256(payload.encode()).hexdigest()}'


@dataclass(frozen=True)
class ORSClient:
    base_url: str
    api_key: str
    timeout: float = 10.0

    @classmethod
    def from_settings(cls) -> 'ORSClient':
        api_key = getattr(settings, 'ORS_API_KEY', '') or ''
        base_url = getattr(settings, 'ORS_BASE_URL', 'https://api.openrouteservice.org')
        if not api_key:
            raise ORSConfigError('ORS_API_KEY is not configured.')
        return cls(base_url=base_url.rstrip('/'), api_key=api_key)

    def _request(self, profile: str, waypoints: list[tuple[float, float]]) -> dict:
        body = {
            'coordinates': [[lng, lat] for lat, lng in waypoints],
            'preference': 'fastest',
            'instructions': False,
            'geometry': True,
        }
        url = f'{self.base_url}/v2/directions/{profile}/geojson'
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/geo+json,application/json',
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=body, headers=headers)
        if resp.status_code == 429:
            raise ORSRouteError(429, 'rate limited')
        if resp.status_code >= 500:
            raise ORSRouteError(resp.status_code, resp.text[:200])
        if resp.status_code >= 400:
            raise ORSRouteError(resp.status_code, resp.text[:200])
        data = resp.json()
        features = data.get('features') or []
        if not features:
            raise ORSNoRouteError('ORS returned no features.')
        geometry = features[0].get('geometry') or {}
        coords = geometry.get('coordinates') or []
        if not coords:
            raise ORSNoRouteError('ORS geometry has no coordinates.')
        return {
            'type': 'FeatureCollection',
            'features': features,
            'distance_m': (features[0].get('properties') or {}).get('summary', {}).get('distance'),
            'duration_s': (features[0].get('properties') or {}).get('summary', {}).get('duration'),
            'geometry': geometry,
        }

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, ORSRouteError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        reraise=True,
    )
    def _request_with_retry(self, profile: str, waypoints: list[tuple[float, float]]) -> dict:
        return self._request(profile, waypoints)

    def get_route(
        self,
        waypoints: list[tuple[float, float]],
        profile: str = 'driving-car',
        use_cache: bool = True,
    ) -> dict:
        if profile not in VALID_PROFILES:
            raise ORSRouteError(400, f'Unsupported profile: {profile}')
        if len(waypoints) < 2:
            raise ORSRouteError(400, 'At least 2 waypoints are required.')
        if len(waypoints) > 50:
            raise ORSRouteError(400, 'At most 50 waypoints are allowed.')

        normalised = [_normalize_waypoint(lat, lng) for lat, lng in waypoints]
        key = _cache_key(profile, normalised)

        if use_cache:
            cached = cache.get(key)
            if cached is not None:
                return cached

        try:
            data = self._request_with_retry(profile, normalised)
        except RetryError as exc:
            logger.warning('ORS proxy exhausted retries: %s', exc)
            raise ORSRouteError(502, 'Upstream routing service unavailable.') from exc

        if use_cache:
            ttl = int(getattr(settings, 'ORS_CACHE_TTL', 86400))
            cache.set(key, data, timeout=ttl)
        return data


def waypoints_from_payload(payload: Iterable) -> list[tuple[float, float]]:
    """Parse a list of [lng, lat] pairs from request payload."""
    parsed: list[tuple[float, float]] = []
    for pair in payload:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ORSRouteError(400, 'Each waypoint must be a [lng, lat] pair.')
        lng, lat = pair
        if not (-180.0 <= float(lng) <= 180.0):
            raise ORSRouteError(400, f'Longitude out of range: {lng}')
        if not (-90.0 <= float(lat) <= 90.0):
            raise ORSRouteError(400, f'Latitude out of range: {lat}')
        parsed.append((float(lat), float(lng)))
    return parsed
