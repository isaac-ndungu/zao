from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.base.permissions import IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import Buyer, Sale
from .serializers import (
    BuyerSerializer,
    SaleCreateSerializer,
    SaleDetailSerializer,
    SaleListSerializer,
)


class BuyerViewSet(CooperativeScopedViewSet):
    queryset = Buyer.objects.all().select_related('cooperative')
    serializer_class = BuyerSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'contact_person', 'phone_number', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(cooperative_id=self.request.cooperative_id)
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

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status__iexact=status)
        buyer = self.request.query_params.get('buyer')
        if buyer:
            qs = qs.filter(buyer_id=buyer)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(sale_date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(sale_date__lte=date_to)
        product_type = self.request.query_params.get('product_type')
        if product_type:
            qs = qs.filter(product_type__iexact=product_type)
        return qs

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
