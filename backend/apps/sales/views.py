from rest_framework.permissions import IsAuthenticated

from apps.base.permissions import IsManager
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
from .tasks import decrement_inventory_on_sale


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
            return [IsAuthenticated(), IsManager()]
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
    queryset = Sale.objects.all().select_related('buyer', 'grade', 'inventory', 'cooperative')

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
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='sale',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'buyer': instance.buyer.name,
                'grade': instance.grade.grade_letter,
                'quantity': float(instance.quantity),
                'total_amount': float(instance.total_amount),
            },
            cooperative_id=self.request.cooperative_id,
        )
        decrement_inventory_on_sale.delay(str(instance.id))

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='sale',
            resource_id=instance.id,
            action='UPDATE',
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type='sale',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'buyer': instance.buyer.name},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()
