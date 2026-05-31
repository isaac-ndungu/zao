from django.db import models, transaction
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import IsManager, IsManagerOrGrader
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import Delivery
from .serializers import (
    DeliveryCreateSerializer,
    DeliveryDetailSerializer,
    DeliveryListSerializer,
    DeliverySyncSerializer,
)
from .tasks import send_bulk_delivery_sms, send_delivery_sms


class DeliveryViewSet(CooperativeScopedViewSet):
    queryset = Delivery.objects.all().select_related('farmer', 'grader', 'cooperative')
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'batch_id', 'farmer__first_name', 'farmer__last_name',
        'farmer__member_number', 'local_id',
    ]
    ordering_fields = [
        'date_delivered', 'batch_id', 'product_type', 'status',
    ]
    ordering = ['-date_delivered']

    def get_queryset(self):
        qs = super().get_queryset()
        for param in ('product_type', 'status', 'shift', 'grade'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        farmer_id = self.request.query_params.get('farmer')
        if farmer_id:
            qs = qs.filter(farmer_id=farmer_id)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(date_delivered__date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(date_delivered__date__lte=date_to)
        return qs

    def get_permissions(self):
        if self.action in ('destroy',):
            return [IsAuthenticated(), IsManager()]
        if self.action in ('create', 'update', 'partial_update', 'sync'):
            return [IsAuthenticated(), IsManagerOrGrader()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return DeliveryCreateSerializer
        if self.action in ('list', 'batches'):
            return DeliveryListSerializer
        if self.action == 'sync':
            return DeliverySyncSerializer
        if self.action == 'summary':
            return DeliveryListSerializer
        return DeliveryDetailSerializer

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if getattr(request.user, 'role', None) == 'admin':
                coop_id = serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
            else:
                serializer.validated_data.pop('cooperative_id', None)
                coop_id = request.cooperative_id
            instance = serializer.save(
                cooperative_id=coop_id,
            )
        log_audit(
            actor=request.user,
            resource_type='delivery',
            resource_id=instance.id,
            action='CREATE',
            new_value={'batch_id': instance.batch_id, 'product_type': instance.product_type},
            cooperative_id=request.cooperative_id,
        )
        send_delivery_sms.delay(
            phone_number=instance.farmer.phone_number,
            farmer_name=f'{instance.farmer.first_name} {instance.farmer.last_name}',
            batch_id=instance.batch_id,
            product_type=instance.product_type,
        )
        return Response(
            DeliveryDetailSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='delivery',
            resource_id=instance.id,
            action='UPDATE',
            previous_value={'batch_id': instance.batch_id},
            new_value=serializer.validated_data,
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='delivery',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'batch_id': instance.batch_id},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()

    @action(detail=False, methods=['post'])
    def sync(self, request):
        serializer = DeliverySyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = []
        sms_deliveries = []
        raw_deliveries = request.data.get('deliveries', [])
        with transaction.atomic():
            for raw_data in raw_deliveries:
                create_serializer = DeliveryCreateSerializer(data=raw_data, context={'request': request})
                create_serializer.is_valid(raise_exception=True)
                if getattr(request.user, 'role', None) == 'admin':
                    coop_id = create_serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
                else:
                    create_serializer.validated_data.pop('cooperative_id', None)
                    coop_id = request.cooperative_id
                instance = create_serializer.save(
                    cooperative_id=coop_id,
                )
                results.append({
                    'local_id': raw_data.get('local_id'),
                    'id': str(instance.id),
                    'batch_id': instance.batch_id,
                })
                sms_deliveries.append({
                    'phone_number': instance.farmer.phone_number,
                    'farmer_name': f'{instance.farmer.first_name} {instance.farmer.last_name}',
                    'batch_id': instance.batch_id,
                    'product_type': instance.product_type,
                })

        if sms_deliveries:
            send_bulk_delivery_sms.delay(sms_deliveries)

        return Response({'synced': results}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def map(self, request):
        qs = self.get_queryset().annotate(
            map_latitude=Coalesce('latitude', 'farmer__latitude'),
            map_longitude=Coalesce('longitude', 'farmer__longitude'),
        ).filter(
            map_latitude__isnull=False, map_longitude__isnull=False,
        )
        date = request.query_params.get('date')
        if date:
            qs = qs.filter(date_delivered__date=date)
        grade = request.query_params.get('grade')
        if grade:
            qs = qs.filter(grade=grade)

        results = []
        for delivery in qs:
            results.append({
                'id': delivery.id,
                'farmer_id': delivery.farmer_id,
                'farmer_name': f'{delivery.farmer.first_name} {delivery.farmer.last_name}',
                'grade': delivery.grade,
                'status': delivery.status,
                'latitude': float(delivery.map_latitude),
                'longitude': float(delivery.map_longitude),
            })

        return Response(results)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'by_product_type': qs.values('product_type').annotate(count=models.Count('id')),
            'by_status': qs.values('status').annotate(count=models.Count('id')),
            'pending_grading': qs.filter(status='PENDING').count(),
        })

    @action(detail=False, methods=['get'])
    def batches(self, request):
        qs = self.get_queryset()
        batch_id = request.query_params.get('batch_id')
        if batch_id:
            deliveries = qs.filter(batch_id=batch_id)
            if not deliveries.exists():
                return Response({'detail': 'Batch not found.'}, status=404)
            total_kg = sum(d.quantity_kg or 0 for d in deliveries)
            total_litres = sum(d.volume_litres or 0 for d in deliveries)
            return Response({
                'batch_id': batch_id,
                'delivery_count': deliveries.count(),
                'total_quantity_kg': total_kg,
                'total_volume_litres': total_litres,
                'product_types': list(deliveries.values_list('product_type', flat=True).distinct()),
                'statuses': list(deliveries.values_list('status', flat=True).distinct()),
                'deliveries': DeliveryListSerializer(deliveries, many=True, context={'request': request}).data,
            })

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date_delivered__date__gte=date_from)
        if date_to:
            qs = qs.filter(date_delivered__date__lte=date_to)

        batches_data = (
            qs.values('batch_id')
            .annotate(
                delivery_count=models.Count('id'),
                total_quantity_kg=models.Sum('quantity_kg'),
                total_volume_litres=models.Sum('volume_litres'),
            )
            .order_by('-batch_id')
        )
        return Response({
            'count': len(batches_data),
            'results': list(batches_data),
        })
