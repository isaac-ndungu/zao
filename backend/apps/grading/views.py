from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.constants import UserRole
from apps.base.permissions import IsAdminOrManager, IsFarmer, IsGrader, IsManager, IsManagerOrGrader
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet
from apps.base.export_mixins import CsvExportMixin

from .models import Grade, GradeImage, GradePrice, FarmerGradeDispute
from .serializers import (
    GradeCreateSerializer,
    GradeDetailSerializer,
    GradeDisputeResolveSerializer,
    GradeDisputeSerializer,
    GradeImageSerializer,
    GradeListSerializer,
    GradeOverrideSerializer,
    GradePriceSerializer,
)
from .tasks import update_inventory_on_grade


from apps.base.idempotency import idempotent
def update_delivery_from_grade(grade):
    delivery = grade.delivery
    updates = {}
    if grade.rejection_reason:
        updates['status'] = 'REJECTED'
        updates['rejection_reason'] = grade.rejection_reason
    else:
        updates['status'] = 'GRADED'
        updates['rejection_reason'] = ''
    updates['grade'] = grade.grade_letter
    changed = any(
        getattr(delivery, field) != value
        for field, value in updates.items()
    )
    if changed:
        for field, value in updates.items():
            setattr(delivery, field, value)
        delivery.save(update_fields=list(updates.keys()))
    return delivery


def _reverse_cycle_pool_and_stock(delivery, grade_letter):
    """Decrement the cycle-pool and Stock for a grade's contribution.
    Used before re-running the grading task (update/override) or on destroy.
    Pass the OLD grade_letter for update/override (the grade has been saved with
    the new values by the time this is called)."""
    from decimal import Decimal
    from apps.inventory.models import Inventory, Stock
    from apps.payment_engine.models import PaymentCycle

    coop = delivery.cooperative
    product = delivery.product_type
    grade_letter = grade_letter or ''
    qty = delivery.volume_litres if product == 'MILK' else delivery.quantity_kg
    qty = qty or Decimal('0')

    cycle = PaymentCycle.objects.filter(
        cooperative=coop,
        start_date__lte=delivery.date_delivered.date(),
        end_date__gte=delivery.date_delivered.date(),
    ).first()

    if cycle:
        pool = Inventory.objects.filter(
            cooperative=coop, payment_cycle=cycle,
            product_type=product, grade=grade_letter,
        ).first()
        if pool is not None:
            pool.quantity_in = (pool.quantity_in or Decimal('0')) - qty
            if pool.quantity_in <= 0:
                pool.delete()
            else:
                pool.is_sold = (pool.quantity_in - (pool.quantity_out or Decimal('0'))) <= 0
                pool.save(update_fields=['quantity_in', 'is_sold', 'updated_at'])

    stock = Stock.objects.filter(
        cooperative=coop, product_type=product, grade=grade_letter,
    ).first()
    if stock is not None:
        stock.quantity_available = (stock.quantity_available or Decimal('0')) - qty
        if stock.quantity_available < 0:
            stock.quantity_available = Decimal('0')
        stock.save(update_fields=['quantity_available', 'last_updated'])


class GradeViewSet(CsvExportMixin, CooperativeScopedViewSet):
    csv_filename = 'grades.csv'
    queryset = Grade.objects.all().select_related(
        'delivery__farmer', 'delivery__cooperative', 'overridden_by',
    )
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'delivery__batch_id', 'grade_letter',
        'delivery__farmer__first_name', 'delivery__farmer__last_name',
        'delivery__farmer__member_number',
    ]
    ordering_fields = ['created_at', 'grade_letter', 'price_per_unit']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == UserRole.FARMER:
            qs = qs.filter(delivery__farmer__user=user)
        for param in ('grade_letter', 'created_at__date'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        delivery_id = self.request.query_params.get('delivery')
        if delivery_id:
            qs = qs.filter(delivery_id=delivery_id)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_permissions(self):
        if self.action in ('create',):
            return [IsAuthenticated(), IsGrader()]
        if self.action in ('override',):
            return [IsAuthenticated(), IsManager()]
        if self.action in ('prices',):
            return [IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsManagerOrGrader()]
        if self.action == 'images':
            if self.request.method == 'POST':
                return [IsAuthenticated(), IsGrader()]
            return [IsAuthenticated()]
        if self.action == 'delete_image':
            return [IsAuthenticated()]
        if self.action == 'dispute':
            return [IsAuthenticated(), IsFarmer()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return GradeCreateSerializer
        if self.action == 'override':
            return GradeOverrideSerializer
        if self.action == 'list':
            return GradeListSerializer
        if self.action in ('prices',):
            return GradePriceSerializer
        if self.action in ('images', 'delete_image'):
            return GradeImageSerializer
        if self.action == 'dispute':
            return GradeDisputeSerializer
        return GradeDetailSerializer

    @idempotent()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if getattr(request.user, 'role', None) == 'admin':
            coop_id = serializer.validated_data.pop('cooperative_id', None) or request.cooperative_id
        else:
            serializer.validated_data.pop('cooperative_id', None)
            coop_id = request.cooperative_id
        instance = serializer.save(cooperative_id=coop_id)

        update_delivery_from_grade(instance)

        log_audit(
            actor=request.user,
            resource_type='grade',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'batch_id': instance.delivery.batch_id,
                'grade_letter': instance.grade_letter,
                'price_per_unit': str(instance.price_per_unit),
            },
            cooperative_id=request.cooperative_id,
        )
        update_inventory_on_grade.delay(str(instance.id))
        return Response(
            GradeDetailSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        old_grade_letter = instance.grade_letter
        delivery = instance.delivery

        serializer.validated_data.pop('delivery', None)
        instance = serializer.save()
        update_delivery_from_grade(instance)

        _reverse_cycle_pool_and_stock(delivery, old_grade_letter or '')

        instance.is_inventory_updated = False
        instance.save(update_fields=['is_inventory_updated'])
        update_inventory_on_grade.delay(str(instance.id))
        log_audit(
            actor=self.request.user,
            resource_type='grade',
            resource_id=instance.id,
            action='UPDATE',
            previous_value={'grade_letter': instance.grade_letter},
            new_value=serializer.validated_data,
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        delivery = instance.delivery
        _reverse_cycle_pool_and_stock(delivery, instance.grade_letter or '')

        log_audit(
            actor=self.request.user,
            resource_type='grade',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'grade_letter': instance.grade_letter},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()

    @idempotent()
    @extend_schema(summary="Override grade", description="Manager override of a grade. POST to set, PATCH to update.")
    @action(detail=True, methods=['post', 'patch'])
    def override(self, request, pk=None):
        grade = self.get_object()
        serializer = GradeOverrideSerializer(
            grade, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)

        was_rejected = bool(grade.rejection_reason)
        old_grade_letter = grade.grade_letter
        delivery = grade.delivery

        previous = {
            'grade_letter': grade.grade_letter,
            'price_per_unit': str(grade.price_per_unit),
            'is_overridden': grade.is_overridden,
        }

        grade.is_overridden = True
        grade.overridden_by = request.user
        grade.overridden_at = timezone.now()
        grade.override_reason = serializer.validated_data.get('override_reason', '')
        grade.grade_letter = serializer.validated_data.get(
            'grade_letter', grade.grade_letter
        )
        grade.price_per_unit = serializer.validated_data.get(
            'price_per_unit', grade.price_per_unit
        )
        grade.rejection_reason = serializer.validated_data.get(
            'rejection_reason', grade.rejection_reason
        )

        _reverse_cycle_pool_and_stock(delivery, old_grade_letter or '')

        grade.is_inventory_updated = False
        grade.save()

        update_delivery_from_grade(grade)

        log_audit(
            actor=request.user,
            resource_type='grade',
            resource_id=grade.id,
            action='OVERRIDE',
            previous_value=previous,
            new_value={
                'grade_letter': grade.grade_letter,
                'price_per_unit': str(grade.price_per_unit),
                'override_reason': grade.override_reason,
            },
            cooperative_id=request.cooperative_id,
        )
        update_inventory_on_grade.delay(str(grade.id))
        return Response(GradeDetailSerializer(grade).data)

    @extend_schema(summary="List/Create grade prices", description="GET to list price tiers, POST to create a new one.")
    @action(detail=False, methods=['get', 'post'])
    def prices(self, request):
        if request.method == 'GET':
            qs = GradePrice.objects.all().order_by('-effective_from')
            page = self.paginate_queryset(qs)
            if page is not None:
                serializer = GradePriceSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = GradePriceSerializer(qs, many=True)
            return Response(serializer.data)

        if request.method == 'POST':
            if request.user.role != UserRole.ADMIN:
                return Response(
                    {'detail': 'Only admins can create prices.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer = GradePriceSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @idempotent()
    @action(detail=True, methods=['post'])
    def dispute(self, request, pk=None):
        grade = self.get_object()
        farmer = getattr(request.user, 'farmer_profile', None)
        if not farmer or grade.delivery.farmer_id != farmer.id:
            raise PermissionDenied('You can only dispute your own grades.')
        serializer = GradeDisputeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute = serializer.save(
            grade=grade,
            raised_by=request.user,
        )
        log_audit(
            actor=request.user,
            resource_type='grade_dispute',
            resource_id=dispute.id,
            action='CREATE',
            new_value={
                'grade': str(grade.id),
                'reason': dispute.reason,
            },
            cooperative_id=request.cooperative_id,
        )
        return Response(
            GradeDisputeSerializer(dispute).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Manage grade images", description="GET/POST to list/add images, DELETE to remove.")
    @action(detail=True, methods=['get', 'post'], url_path='images')
    def images(self, request, pk=None):
        grade = self.get_object()
        if request.method == 'GET':
            serializer = GradeImageSerializer(
                grade.images.all(), many=True, context={'request': request},
            )
            return Response(serializer.data)

        serializer = GradeImageSerializer(
            data=request.data, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        grade_image = serializer.save(uploaded_by=request.user)
        grade.images.add(grade_image)
        return Response(
            GradeImageSerializer(grade_image, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Manage grade images", description="GET/POST to list/add images, DELETE to remove.")
    @action(detail=True, methods=['delete'], url_path='images/(?P<image_id>[^/.]+)')
    def delete_image(self, request, pk=None, image_id=None):
        grade = self.get_object()
        grade_image = get_object_or_404(GradeImage, id=image_id)

        if grade_image not in grade.images.all():
            return Response(
                {'detail': 'Image not found on this grade.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if grade_image.uploaded_by != request.user and request.user.role != UserRole.MANAGER:
            return Response(
                {'detail': 'Only the uploader or a manager can delete images.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        grade.images.remove(grade_image)
        grade_image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GradeDisputeViewSet(CooperativeScopedViewSet):
    queryset = FarmerGradeDispute.objects.all().select_related(
        'grade', 'raised_by', 'resolved_by',
    )

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if user.is_authenticated and getattr(user, 'role', None) == 'admin':
            return qs
        return qs.filter(grade__cooperative_id=self.request.cooperative_id)

    def get_permissions(self):
        if self.action == 'resolve':
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(raised_by=self.request.user)

    def get_serializer_class(self):
        if self.action == 'resolve':
            return GradeDisputeResolveSerializer
        return GradeDisputeSerializer

    @idempotent()
    @extend_schema(summary="Resolve grade dispute", description="Resolve or reject a FarmerGradeDispute.")
    @action(detail=True, methods=['post', 'patch'])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        if dispute.status != 'PENDING':
            return Response(
                {'detail': 'Only PENDING disputes can be resolved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = GradeDisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute.status = serializer.validated_data['resolution']
        dispute.resolved_by = request.user
        dispute.resolution_notes = serializer.validated_data.get('notes', '')
        dispute.resolved_at = timezone.now()
        dispute.save(update_fields=['status', 'resolved_by', 'resolution_notes', 'resolved_at'])
        log_audit(
            actor=request.user,
            resource_type='grade_dispute',
            resource_id=dispute.id,
            action='RESOLVE',
            new_value={
                'status': dispute.status,
                'resolution_notes': dispute.resolution_notes,
            },
            cooperative_id=request.cooperative_id,
        )
        return Response(GradeDisputeSerializer(dispute).data)


class GradePriceViewSet(viewsets.ModelViewSet):
    queryset = GradePrice.objects.all().order_by('-effective_from')
    serializer_class = GradePriceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdminOrManager()]
        return [IsAuthenticated()]
