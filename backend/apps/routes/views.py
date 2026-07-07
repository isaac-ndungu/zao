from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.idempotency import idempotent
from apps.base.permissions import IsManager, IsManagerOrGrader
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet
from apps.farmers.models import Farmer

from .models import CollectionRoute, DayOfWeekChoices, RouteStop
from .serializers import (
    RouteAssignFarmerSerializer,
    RouteAssignSerializer,
    RouteDetailSerializer,
    RouteListSerializer,
    RouteMapSerializer,
    RouteUnassignFarmerSerializer,
    RouteWriteSerializer,
    build_path_from_stops,
)


class RouteViewSet(CooperativeScopedViewSet):
    queryset = CollectionRoute.objects.all().prefetch_related('stops__farmers')

    @idempotent()
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return RouteListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return RouteWriteSerializer
        if self.action == 'assign_stops':
            return RouteAssignSerializer
        if self.action == 'map':
            return RouteMapSerializer
        if self.action == 'assign_farmer':
            return RouteAssignFarmerSerializer
        if self.action == 'unassign_farmer':
            return RouteUnassignFarmerSerializer
        return RouteDetailSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'assign_stops'):
            return [IsAuthenticated(), IsManager()]
        if self.action in ('assign_farmer', 'unassign_farmer'):
            return [IsAuthenticated(), IsManagerOrGrader()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(farmer_count=Count('stops__farmers', distinct=True))
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        day_of_week = self.request.query_params.get('day_of_week')
        if day_of_week is not None:
            try:
                qs = qs.filter(day_of_week=DayOfWeekChoices.from_string(day_of_week))
            except ValueError:
                qs = qs.none()
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(cooperative_id=self.request.cooperative_id)
        self._autofill_path(instance)
        instance.refresh_from_db()
        log_audit(
            actor=self.request.user,
            resource_type='collection_route',
            resource_id=instance.id,
            action='CREATE',
            new_value={'name': instance.name},
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        self._autofill_path(instance)
        log_audit(
            actor=self.request.user,
            resource_type='collection_route',
            resource_id=instance.id,
            action='UPDATE',
            new_value=serializer.validated_data,
            cooperative_id=self.request.cooperative_id,
        )

    def _autofill_path(self, route: CollectionRoute) -> None:
        """If `path` is empty/missing, build a LineString from current stops."""
        if route.path and isinstance(route.path, dict) and route.path.get('coordinates'):
            return
        new_path = build_path_from_stops(route.stops.all())
        if new_path:
            route.path = new_path
            route.save(update_fields=['path'])

    @extend_schema(
        summary='Route map data',
        description='Returns a route with ordered stops and their assigned farmers, ready for map display.',
        responses={200: RouteMapSerializer},
    )
    @action(detail=True, methods=['get'])
    def map(self, request, pk=None):
        route = self.get_object()
        return Response(RouteMapSerializer(route).data)

    @idempotent()
    @action(detail=True, methods=['post'], url_path='assign-stops')
    def assign_stops(self, request, pk=None):
        route = self.get_object()
        serializer = RouteAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stops_data = serializer.validated_data['stops']
        all_farmer_ids = {fid for sd in stops_data for fid in sd['farmer_ids']}
        if all_farmer_ids:
            existing = set(Farmer.objects.filter(id__in=all_farmer_ids).values_list('id', flat=True))
            missing = all_farmer_ids - existing
            if missing:
                return Response(
                    {'detail': f'Farmers not found: {len(missing)} invalid ID(s).',
                     'invalid_farmer_ids': [str(m) for m in missing]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            route.stops.all().delete()
            stop_instances = []
            for stop_data in stops_data:
                farmer_ids = stop_data.pop('farmer_ids')
                stop = RouteStop.objects.create(
                    route=route,
                    latitude=stop_data['latitude'],
                    longitude=stop_data['longitude'],
                    stop_order=stop_data['stop_order'],
                    estimated_minutes=stop_data.get('estimated_minutes'),
                )
                if farmer_ids:
                    stop.farmers.set(farmer_ids)
                stop_instances.append(stop)
            self._autofill_path(route)

        route.refresh_from_db()
        return Response(
            RouteDetailSerializer(route, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary='Assign a farmer to a stop',
        request=RouteAssignFarmerSerializer,
        responses={200: RouteDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='assign-farmer')
    def assign_farmer(self, request, pk=None):
        route = self.get_object()
        serializer = RouteAssignFarmerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            stop = route.stops.get(id=serializer.validated_data['stop_id'])
        except RouteStop.DoesNotExist:
            return Response(
                {'detail': 'Stop not found on this route.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            farmer = Farmer.objects.get(id=serializer.validated_data['farmer_id'])
        except Farmer.DoesNotExist:
            return Response(
                {'detail': 'Farmer not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        stop.farmers.add(farmer)
        log_audit(
            actor=request.user,
            resource_type='collection_route',
            resource_id=route.id,
            action='UPDATE',
            new_value={
                'assigned_farmer': str(farmer.id),
                'stop_id': stop.id,
            },
            cooperative_id=request.cooperative_id,
        )
        return Response(
            RouteMapSerializer(route).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary='Remove a farmer from any stop on this route',
        request=RouteUnassignFarmerSerializer,
        responses={200: OpenApiResponse(description='Farmer unassigned')},
    )
    @action(detail=True, methods=['post'], url_path='unassign-farmer')
    def unassign_farmer(self, request, pk=None):
        route = self.get_object()
        serializer = RouteUnassignFarmerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        farmer_id = serializer.validated_data['farmer_id']
        stops = route.stops.filter(farmers__id=farmer_id)
        if not stops.exists():
            return Response(
                {'detail': 'Farmer is not assigned to any stop on this route.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        count = 0
        for stop in stops:
            removed = stop.farmers.remove(farmer_id)
            if removed:
                count += 1
        log_audit(
            actor=request.user,
            resource_type='collection_route',
            resource_id=route.id,
            action='UPDATE',
            previous_value={'unassigned_farmer': str(farmer_id), 'stops_affected': count},
            cooperative_id=request.cooperative_id,
        )
        return Response(
            {'detail': f'Farmer removed from {count} stop(s).', 'stops_affected': count},
            status=status.HTTP_200_OK,
        )
