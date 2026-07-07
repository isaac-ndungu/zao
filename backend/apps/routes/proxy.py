"""
Sync DRF view that proxies OpenRouteService route requests.

Returns a raw GeoJSON ``FeatureCollection`` so the leaflet-routing-machine
custom router on the frontend can consume it without translation.

Note: kept synchronous because DRF's APIView dispatch is sync. The
underlying ``httpx.Client`` call is what actually hits the network, and
DRF's throttle + auth are already optimised for sync.
"""
from __future__ import annotations

import json
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .routing import (
    ORSConfigError,
    ORSClient,
    ORSNoRouteError,
    ORSRouteError,
    waypoints_from_payload,
)

logger = logging.getLogger(__name__)


class RouteOrsThrottle(UserRateThrottle):
    scope = 'route_ors'


class RouteProxyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [RouteOrsThrottle]

    def _problem(self, status_code, title, detail):
        return Response(
            {
                'type': 'about:blank',
                'title': title,
                'status': status_code,
                'detail': detail,
            },
            status=status_code,
        )

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return self._problem(400, 'Bad Request', 'Body must be valid JSON.')

        raw_waypoints = payload.get('waypoints') or []
        profile = (payload.get('profile') or 'driving-car').strip()
        if not isinstance(raw_waypoints, list) or not raw_waypoints:
            return self._problem(400, 'Bad Request', '`waypoints` must be a non-empty list.')

        try:
            waypoints = waypoints_from_payload(raw_waypoints)
        except ORSRouteError as exc:
            return self._problem(exc.status_code, 'Bad Request', exc.detail)

        try:
            client = ORSClient.from_settings()
        except ORSConfigError as exc:
            return self._problem(503, 'Service Unavailable', str(exc))

        try:
            data = client.get_route(waypoints, profile=profile)
        except ORSConfigError as exc:
            return self._problem(503, 'Service Unavailable', str(exc))
        except ORSNoRouteError as exc:
            return self._problem(502, 'Bad Gateway', str(exc))
        except ORSRouteError as exc:
            # Any upstream routing error surfaces as 502 Bad Gateway;
            # ORS auth/quota issues (4xx) become 502 too, not propagated.
            return self._problem(502, 'Bad Gateway', exc.detail)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception('Unexpected ORS proxy error')
            return self._problem(502, 'Bad Gateway', str(exc))

        return Response(data, status=200)
