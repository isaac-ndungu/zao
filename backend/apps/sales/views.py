from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.base.permissions import IsAccountantOrManager, IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import Buyer, PaymentCycle, Sale
from .serializers import (
    BuyerSerializer,
    PaymentCycleSerializer,
    SaleCreateSerializer,
    SaleDetailSerializer,
    SaleListSerializer,
)


class BuyerViewSet(CooperativeScopedViewSet):
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='buyer',
            resource_id=instance.id,
            action='CREATE',
            new_value={'name': instance.name},
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='buyer',
            resource_id=instance.id,
            action='UPDATE',
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='buyer',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'name': instance.name},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()


class PaymentCycleViewSet(CooperativeScopedViewSet):
    queryset = PaymentCycle.objects.all()
    serializer_class = PaymentCycleSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='payment_cycle',
            resource_id=instance.id,
            action='CREATE',
            new_value={'name': instance.name},
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='payment_cycle',
            resource_id=instance.id,
            action='UPDATE',
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='payment_cycle',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'name': instance.name},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()


class SaleViewSet(CooperativeScopedViewSet):
    queryset = Sale.objects.all().select_related('buyer', 'inventory', 'cooperative')
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'buyer__name', 'product_type', 'grade_letter',
        'invoice_number', 'inventory__batch_id',
    ]
    ordering_fields = [
        'sale_date', 'total_amount', 'quantity',
        'product_type', 'status',
    ]
    ordering = ['-sale_date']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            return SaleListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return SaleCreateSerializer
        return SaleDetailSerializer

    def perform_create(self, serializer):
        if getattr(self.request.user, 'role', None) == 'admin':
            cooperative_id = serializer.validated_data.pop('cooperative_id', None) or self.request.cooperative_id
        else:
            serializer.validated_data.pop('cooperative_id', None)
            cooperative_id = self.request.cooperative_id

        instance = serializer.save(
            cooperative_id=cooperative_id,
            recorded_by=self.request.user,
        )
        log_audit(
            actor=self.request.user,
            resource_type='sale',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'buyer': instance.buyer.name,
                'product_type': instance.product_type,
                'grade_letter': instance.grade_letter,
                'quantity': float(instance.quantity),
                'total_amount': float(instance.total_amount),
                'status': instance.status,
            },
            cooperative_id=cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='sale',
            resource_id=instance.id,
            action='UPDATE',
            new_value={
                'status': instance.status,
                'quantity': float(instance.quantity),
                'total_amount': float(instance.total_amount),
            },
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='sale',
            resource_id=instance.id,
            action='DELETE',
            previous_value={
                'buyer': instance.buyer.name,
                'invoice_number': instance.invoice_number,
            },
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()
