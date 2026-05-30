from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import IsAccountant, IsAccountantOrManager, IsFarmer
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import Loan
from .serializers import (
    LoanApproveSerializer,
    LoanCreateSerializer,
    LoanDetailSerializer,
    LoanListSerializer,
)


class LoanViewSet(CooperativeScopedViewSet):
    queryset = Loan.objects.all().select_related(
        'farmer', 'approved_by', 'cooperative',
    ).prefetch_related('repayments')

    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        if self.action == 'create':
            return LoanCreateSerializer
        return LoanDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsFarmer() | IsAccountantOrManager()]
        if self.action == 'approve':
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action == 'disburse':
            return [IsAuthenticated(), IsAccountant()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'FARMER':
            if hasattr(user, 'farmer_profile'):
                qs = qs.filter(farmer=user.farmer_profile)
            else:
                qs = qs.none()
        farmer_id = self.request.query_params.get('farmer')
        if farmer_id:
            qs = qs.filter(farmer_id=farmer_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        status_val = 'PENDING'
        if user.role in ('MANAGER', 'ACCOUNTANT'):
            status_val = 'ACTIVE'
        instance = serializer.save(
            cooperative_id=self.request.cooperative_id,
            status=status_val,
        )
        log_audit(
            actor=user,
            resource_type='loan',
            resource_id=instance.id,
            action='CREATE',
            new_value={
                'farmer': str(instance.farmer_id),
                'principal': float(instance.amount_principal),
                'status': instance.status,
            },
            cooperative_id=self.request.cooperative_id,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type='loan',
            resource_id=instance.id,
            action='UPDATE',
            cooperative_id=self.request.cooperative_id,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        loan = self.get_object()
        serializer = LoanApproveSerializer(
            data=request.data, context={'view': self, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        from django.utils import timezone
        loan.status = 'ACTIVE'
        loan.approved_by = request.user
        loan.approved_at = timezone.now()
        loan.save(update_fields=['status', 'approved_by', 'approved_at'])
        log_audit(
            actor=request.user,
            resource_type='loan',
            resource_id=loan.id,
            action='APPROVE',
            cooperative_id=self.request.cooperative_id,
        )
        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        loan = self.get_object()
        if loan.status != 'ACTIVE':
            return Response(
                {'detail': 'Only ACTIVE loans can be disbursed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if loan.disbursed_at:
            return Response(
                {'detail': 'Loan has already been disbursed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        loan.disbursed_at = timezone.now()
        loan.save(update_fields=['disbursed_at'])
        log_audit(
            actor=request.user,
            resource_type='loan',
            resource_id=loan.id,
            action='DISBURSE',
            cooperative_id=self.request.cooperative_id,
        )
        serializer = self.get_serializer(loan)
        return Response(serializer.data)
