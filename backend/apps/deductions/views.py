from rest_framework import filters
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.base.constants import UserRole
from apps.base.permissions import IsAccountantOrManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet
from apps.base.export_mixins import CsvExportMixin

from .models import Deduction, FarmInputCredit
from .serializers import (
    DeductionCreateSerializer,
    DeductionDetailSerializer,
    DeductionListSerializer,
    FarmInputCreditCreateSerializer,
    FarmInputCreditDetailSerializer,
    FarmInputCreditListSerializer,
)


class DeductionViewSet(CsvExportMixin, CooperativeScopedViewSet):
    csv_filename = 'deductions.csv'
    queryset = Deduction.objects.all().select_related(
        'farmer', 'cycle', 'created_by', 'cooperative',
    )
    lookup_value_regex = '[0-9a-f-]{36}'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['farmer__first_name', 'farmer__last_name', 'farmer__member_number', 'deduction_type']

    def get_serializer_class(self):
        if self.action == 'list':
            return DeductionListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return DeductionCreateSerializer
        return DeductionDetailSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and getattr(user, 'role', None) == UserRole.FARMER:
            qs = qs.filter(farmer__user=user)
        farmer_id = self.request.query_params.get('farmer')
        if farmer_id:
            qs = qs.filter(farmer_id=farmer_id)
        deduction_type = self.request.query_params.get('type')
        if deduction_type:
            qs = qs.filter(deduction_type=deduction_type)
        cycle = self.request.query_params.get('cycle')
        if cycle:
            qs = qs.filter(cycle_id=cycle)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(
            cooperative_id=self.request.cooperative_id,
            created_by=self.request.user,
            deduction_type='LOAN_REPAYMENT',
        )
        log_audit(
            actor=self.request.user,
            resource_type='deduction',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'farmer': str(instance.farmer_id),
                'cycle': str(instance.cycle_id),
                'amount': float(instance.amount),
                'type': instance.deduction_type,
            },
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='deduction',
            resource_id=instance.id,
            action='UPDATE',
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        if instance.cycle.status != 'DRAFT':
            raise ValidationError(
                'Only deductions in DRAFT cycles can be deleted.'
            )
        log_audit(
            actor=self.request.user,
            resource_type='deduction',
            resource_id=instance.id,
            action='DELETE',
            previous_value={
                'farmer': str(instance.farmer_id),
                'amount': float(instance.amount),
                'type': instance.deduction_type,
            },
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()


class FarmInputCreditViewSet(CooperativeScopedViewSet):
    queryset = FarmInputCredit.objects.all().select_related(
        'farmer', 'cooperative',
    )

    def get_serializer_class(self):
        if self.action == 'list':
            return FarmInputCreditListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return FarmInputCreditCreateSerializer
        return FarmInputCreditDetailSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        farmer = self.request.query_params.get('farmer')
        if farmer:
            qs = qs.filter(farmer_id=farmer)
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(
            cooperative_id=self.request.cooperative_id,
        )
        log_audit(
            actor=self.request.user,
            resource_type='farm_input_credit',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'farmer': str(instance.farmer_id),
                'item': instance.item_description,
                'amount': float(instance.amount),
            },
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        if instance.status == 'COMPLETED':
            raise ValidationError(
                'Cannot delete an input credit that has already been fully deducted.'
            )
        log_audit(
            actor=self.request.user,
            resource_type='farm_input_credit',
            resource_id=instance.id,
            action='DELETE',
            previous_value={
                'farmer': str(instance.farmer_id),
                'amount': float(instance.amount),
                'item': instance.item_description,
            },
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()
