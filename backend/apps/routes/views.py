from django.db import transaction
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import IsManager
from apps.base.views import CooperativeScopedViewSet

from .models import CollectionRoute, RouteStop
from .serializers import (
    RouteAssignSerializer,
    RouteDetailSerializer,
    RouteListSerializer,
    RouteWriteSerializer,
)


class RouteViewSet(CooperativeScopedViewSet):
    queryset = CollectionRoute.objects.all().prefetch_related('stops__farmers')

    def get_serializer_class(self):
        if self.action == 'list':
            return RouteListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return RouteWriteSerializer
        if self.action == 'assign_stops':
            return RouteAssignSerializer
        return RouteDetailSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'assign_stops'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(farmer_count=Count('stops__farmers', distinct=True))
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        day_of_week = self.request.query_params.get('day_of_week')
        if day_of_week is not None:
            qs = qs.filter(day_of_week=int(day_of_week))
        return qs

    @action(detail=True, methods=['post'], url_path='assign-stops')
    def assign_stops(self, request, pk=None):
        route = self.get_object()
        serializer = RouteAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stops_data = serializer.validated_data['stops']
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

        return Response(
            RouteDetailSerializer(route, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )
