from decimal import Decimal

from django.db import models
from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Inventory
from .serializers import (
    InventoryDetailSerializer,
    InventoryListSerializer,
)


class InventoryViewSet(ReadOnlyModelViewSet):
    queryset = Inventory.objects.all().select_related('cooperative')
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['batch_id', 'grade', 'product_type']
    ordering_fields = ['batch_id', 'product_type', 'grade', 'created_at']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get_serializer_class(self):
        if self.action == 'list':
            return InventoryListSerializer
        return InventoryDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == 'admin':
            qs = self.queryset
        else:
            qs = self.queryset.filter(
                cooperative_id=self.request.cooperative_id
            )
        for param in ('product_type', 'grade'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        batch_id = self.request.query_params.get('batch_id')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        return qs

    def get_permissions(self):
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset()
        return Response({
            'total_records': qs.count(),
            'total_quantity_in': float(qs.aggregate(s=Sum('quantity_in'))['s'] or 0),
            'total_quantity_out': float(qs.aggregate(s=Sum('quantity_out'))['s'] or 0),
            'by_product_type': list(
                qs.values('product_type')
                .annotate(
                    records=models.Count('id'),
                    qty_in=Sum('quantity_in'),
                    qty_out=Sum('quantity_out'),
                )
            ),
            'by_grade': list(
                qs.values('grade')
                .annotate(
                    records=models.Count('id'),
                    qty_in=Sum('quantity_in'),
                    qty_out=Sum('quantity_out'),
                )
            ),
        })

    @action(detail=False, methods=['get', 'post'])
    def alerts(self, request):
        if request.method == 'POST':
            threshold = Decimal(str(request.data.get('threshold', 100)))
            product_type = request.data.get('product_type')
        else:
            threshold = Decimal(str(request.query_params.get('threshold', 100)))
            product_type = request.query_params.get('product_type')

        qs = self.get_queryset()
        if product_type:
            qs = qs.filter(product_type=product_type)

        results = []
        for item in qs.iterator():
            balance = item.running_balance
            if balance < threshold:
                results.append({
                    'id': str(item.id),
                    'batch_id': item.batch_id,
                    'product_type': item.product_type,
                    'grade': item.grade,
                    'unit': item.unit,
                    'quantity_in': float(item.quantity_in),
                    'quantity_out': float(item.quantity_out),
                    'running_balance': float(balance),
                })

        return Response({
            'threshold': float(threshold),
            'product_type': product_type,
            'count': len(results),
            'results': results,
        })
