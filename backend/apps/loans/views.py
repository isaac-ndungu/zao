from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated, OR
from rest_framework.response import Response

from apps.base.constants import UserRole
from apps.base.permissions import IsAccountant, IsAccountantOrManager, IsFarmer, IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet
from apps.base.export_mixins import CsvExportMixin
from apps.notifications.models import Notification

from .models import Loan, LoanGuarantor
from apps.base.idempotency import idempotent
from .serializers import (
    AddGuarantorSerializer,
    LoanApproveSerializer,
    LoanCreateSerializer,
    LoanDetailSerializer,
    LoanGuarantorSerializer,
    LoanListSerializer,
    LoanMarkCompletedSerializer,
    LoanMarkDefaultedSerializer,
)


class LoanViewSet(CsvExportMixin, CooperativeScopedViewSet):
    csv_filename = 'loans.csv'
    queryset = Loan.objects.all().select_related(
        'farmer', 'approved_by', 'cooperative',
    ).prefetch_related('repayments')
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'farmer__first_name', 'farmer__last_name',
        'farmer__member_number', 'notes',
    ]
    ordering_fields = [
        'created_at', 'amount_principal', 'status',
        'installments_paid', 'number_of_installments',
    ]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return LoanCreateSerializer
        return LoanDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), OR(IsFarmer(), IsAccountantOrManager())]
        if self.action == 'approve':
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action == 'disburse':
            return [IsAuthenticated(), IsAccountant()]
        if self.action == 'mark_completed':
            return [IsAuthenticated(), IsAccountant()]
        if self.action == 'mark_defaulted':
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action in ('add_guarantor', 'remove_guarantor'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == UserRole.FARMER:
            if hasattr(user, 'farmer_profile'):
                qs = qs.filter(farmer=user.farmer_profile)
            else:
                qs = qs.none()
        farmer_id = self.request.query_params.get('farmer')
        if farmer_id:
            qs = qs.filter(farmer_id=farmer_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status__iexact=status_param)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(
            cooperative_id=self.request.cooperative_id,
            status='PENDING',
        )
        log_audit(
            actor=self.request.user,
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

    @idempotent()
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
        try:
            Notification.objects.create(
                cooperative=loan.cooperative,
                recipient=loan.farmer,
                channel='IN_APP',
                notification_type='LOAN_APPROVAL',
                content=f'Your loan of KES {loan.amount_principal} has been approved.',
                status='PENDING',
            )
        except Exception:
            pass
        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @idempotent()
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
        try:
            Notification.objects.create(
                cooperative=loan.cooperative,
                recipient=loan.farmer,
                channel='IN_APP',
                notification_type='LOAN_DISBURSEMENT',
                content=f'Your loan of KES {loan.amount_principal} has been disbursed.',
                status='PENDING',
            )
        except Exception:
            pass
        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @idempotent()
    @action(detail=True, methods=['post'])
    def add_guarantor(self, request, pk=None):
        loan = self.get_object()
        serializer = AddGuarantorSerializer(
            data=request.data, context={'view': self, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        guarantor = serializer.validated_data['guarantor_id']
        LoanGuarantor.objects.create(
            loan=loan,
            guarantor=guarantor,
            cooperative=loan.cooperative,
        )
        log_audit(
            actor=request.user,
            resource_type='loan_guarantor',
            resource_id=loan.id,
            action='CREATE',
            new_value={
                'guarantor_id': str(guarantor.id),
                'guarantor_name': f'{guarantor.first_name} {guarantor.last_name}',
            },
            cooperative_id=self.request.cooperative_id,
        )
        return Response(
            LoanGuarantorSerializer(loan.guarantors.all(), many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @idempotent()
    @action(detail=True, methods=['post'])
    def remove_guarantor(self, request, pk=None):
        loan = self.get_object()
        if loan.status != 'PENDING':
            return Response(
                {'detail': 'Guarantors can only be removed from PENDING loans.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        guarantor_id = request.data.get('guarantor_id')
        if not guarantor_id:
            return Response(
                {'detail': 'guarantor_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = LoanGuarantor.objects.filter(
            loan=loan, guarantor_id=guarantor_id,
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Guarantor not found on this loan.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        log_audit(
            actor=request.user,
            resource_type='loan_guarantor',
            resource_id=loan.id,
            action='DELETE',
            new_value={'removed_guarantor_id': str(guarantor_id)},
            cooperative_id=self.request.cooperative_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @idempotent()
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        loan = self.get_object()
        serializer = LoanMarkCompletedSerializer(
            data=request.data, context={'view': self, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        loan.status = 'COMPLETED'
        loan.save(update_fields=['status'])
        log_audit(
            actor=request.user,
            resource_type='loan',
            resource_id=loan.id,
            action='MARK_COMPLETED',
            cooperative_id=self.request.cooperative_id,
        )
        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @idempotent()
    @action(detail=True, methods=['post'])
    def mark_defaulted(self, request, pk=None):
        loan = self.get_object()
        serializer = LoanMarkDefaultedSerializer(
            data=request.data, context={'view': self, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data['reason']
        reason = reason.strip()[:500]
        loan.status = 'DEFAULTED'
        loan.notes = (loan.notes + '\n' if loan.notes else '') + f'Defaulted: {reason}'
        loan.save(update_fields=['status', 'notes'])
        log_audit(
            actor=request.user,
            resource_type='loan',
            resource_id=loan.id,
            action='MARK_DEFAULTED',
            new_value={'reason': reason},
            cooperative_id=self.request.cooperative_id,
        )
        for lg in loan.guarantors.filter(status='ACTIVE').select_related('guarantor'):
            Notification.objects.create(
                cooperative=loan.cooperative,
                recipient=lg.guarantor,
                channel='IN_APP',
                notification_type='LOAN_DEFAULTED',
                content=(
                    f'The loan (KES {loan.amount_principal}) for '
                    f'{loan.farmer.first_name} {loan.farmer.last_name} '
                    f'which you guaranteed has been defaulted. Reason: {reason}'
                ),
                status='SENT',
            )
            log_audit(
                actor=request.user,
                resource_type='guarantor_notification',
                resource_id=lg.id,
                action='NOTIFY',
                new_value={
                    'guarantor_id': str(lg.guarantor_id),
                    'reason': reason,
                },
                cooperative_id=loan.cooperative_id,
            )
        serializer = self.get_serializer(loan)
        return Response(serializer.data)
