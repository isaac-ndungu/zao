from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.cooperatives.models import Cooperative
from apps.cooperatives.serializers import (
    CooperativeListSerializer,
    CooperativeDetailSerializer,
)


class CooperativeViewSet(viewsets.ModelViewSet):
    queryset = Cooperative.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return CooperativeListSerializer
        return CooperativeDetailSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        total = queryset.count()
        active = queryset.filter(is_active=True).count()
        by_produce_type = queryset.values('produce_type').annotate(
            count=Count('id')
        )
        by_county = queryset.values('county').annotate(
            count=Count('id')
        )
        return Response({
            'total': total,
            'active': active,
            'by_produce_type': by_produce_type,
            'by_county': by_county,
        })
