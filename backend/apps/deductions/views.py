from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.base.permissions import IsAccountantOrManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import Deduction
from .serializers import (
    DeductionCreateSerializer,
    DeductionDetailSerializer,
    DeductionListSerializer,
)


class DeductionViewSet(CooperativeScopedViewSet):
    queryset = Deduction.objects.all().select_related(
        'farmer', 'cycle', 'created_by', 'cooperative',
    )

    def get_serializer_class(self):
        if self.action == 'list':
            return DeductionListSerializer
        if self.action in ('create',):
            return DeductionCreateSerializer
        return DeductionDetailSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        farmer = self.request.query_params.get('farmer')
        if farmer:
            qs = qs.filter(farmer_id=farmer)
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
