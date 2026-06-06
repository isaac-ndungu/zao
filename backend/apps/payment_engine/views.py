from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import IsAccountantOrManager, IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import ComputationWarning, FarmerPayment, PaymentCycle
from .serializers import (
    ComputationWarningSerializer,
    CyclePreviewSerializer,
    PaymentCycleSerializer,
    PaymentCycleStatusSerializer,
)
from .tasks import run_payment_engine


class PaymentCycleViewSet(CooperativeScopedViewSet):
    queryset = PaymentCycle.objects.all().select_related('cooperative', 'locked_by')

    def get_serializer_class(self):
        if self.action == 'preview':
            return CyclePreviewSerializer
        if self.action in ('status', 'task_status'):
            return PaymentCycleStatusSerializer
        return PaymentCycleSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action in ('lock', 'unlock'):
            return [IsAuthenticated(), IsManager()]
        if self.action in ('run', 'hold', 'release'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action == 'export':
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        if getattr(self.request.user, 'role', None) == 'admin':
            cooperative_id = serializer.validated_data.pop('cooperative_id', None) or self.request.cooperative_id
        else:
            serializer.validated_data.pop('cooperative_id', None)
            cooperative_id = self.request.cooperative_id

        instance = serializer.save(cooperative_id=cooperative_id)
        log_audit(
            actor=self.request.user,
            resource_type='payment_cycle',
            resource_id=instance.id,
            action='CREATE',
            new_value={'name': instance.name, 'status': instance.status},
            cooperative_id=cooperative_id,
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
        if instance.status != 'DRAFT':
            raise ValidationError(
                'Only DRAFT cycles can be deleted. '
                'Computed or locked cycles are permanent financial records.'
            )
        log_audit(
            actor=self.request.user,
            resource_type='payment_cycle',
            resource_id=instance.id,
            action='DELETE',
            previous_value={'name': instance.name, 'status': instance.status},
            cooperative_id=self.request.cooperative_id,
        )
        instance.delete()

    @extend_schema(summary="Run payment computation", description="Triggers Celery task to compute farmer payments for this cycle.")
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        cycle = self.get_object()

        if cycle.status in ('LOCKED', 'DISBURSED', 'COMPUTING'):
            return Response(
                {'detail': f'Cannot run computation on a {cycle.status.lower()} cycle.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = run_payment_engine.delay(str(cycle.id))
        PaymentCycle.objects.filter(id=cycle.id).update(celery_task_id=task.id)

        log_audit(
            actor=request.user,
            resource_type='payment_cycle',
            resource_id=cycle.id,
            action='RUN',
            new_value={'task_id': task.id, 'status': cycle.status},
            cooperative_id=self.request.cooperative_id,
        )
        return Response({'task_id': task.id, 'status': 'started'})

    @extend_schema(summary="Preview cycle payments", description="Returns detailed preview of farmer payments before locking.")
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        cycle = self.get_object()
        serializer = CyclePreviewSerializer(
            cycle, context={'request': request},
        )
        return Response(serializer.data)

    @extend_schema(summary="Lock payment cycle", description="Locks a COMPUTED cycle, preventing further changes.")
    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        cycle = self.get_object()

        if cycle.status != 'COMPUTED':
            return Response(
                {'detail': 'Only COMPUTED cycles can be locked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cycle.status = 'LOCKED'
        cycle.locked_by = request.user
        cycle.locked_at = timezone.now()
        cycle.save(update_fields=['status', 'locked_by', 'locked_at'])
        log_audit(
            actor=request.user,
            resource_type='payment_cycle',
            resource_id=cycle.id,
            action='LOCK',
            cooperative_id=self.request.cooperative_id,
        )
        return Response(PaymentCycleSerializer(cycle).data)

    @extend_schema(summary="Unlock payment cycle", description="Returns a LOCKED cycle back to COMPUTED status.")
    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        cycle = self.get_object()

        if cycle.status != 'LOCKED':
            return Response(
                {'detail': 'Only LOCKED cycles can be unlocked.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cycle.status = 'COMPUTED'
        cycle.locked_by = None
        cycle.locked_at = None
        cycle.save(update_fields=['status', 'locked_by', 'locked_at'])
        log_audit(
            actor=request.user,
            resource_type='payment_cycle',
            resource_id=cycle.id,
            action='UNLOCK',
            cooperative_id=self.request.cooperative_id,
        )
        return Response(PaymentCycleSerializer(cycle).data)

    @extend_schema(summary="Cycle status", description="Returns current status, totals, warnings, and celery task info.")
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        cycle = self.get_object()
        serializer = PaymentCycleStatusSerializer(
            cycle, context={'request': request},
        )
        return Response(serializer.data)

    @extend_schema(summary="Hold farmer payment", description="Place a hold on a specific farmer payment within this cycle.")
    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        cycle = self.get_object()

        if cycle.status not in ('COMPUTED', 'LOCKED'):
            return Response(
                {'detail': 'Only COMPUTED or LOCKED cycles can be modified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        farmer_payment_id = request.data.get('farmer_payment_id')
        reason = request.data.get('hold_reason', '')

        if not farmer_payment_id:
            return Response(
                {'detail': 'farmer_payment_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            fp = FarmerPayment.objects.get(
                id=farmer_payment_id, cycle=cycle,
            )
        except FarmerPayment.DoesNotExist:
            return Response(
                {'detail': 'FarmerPayment not found in this cycle.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        fp.is_on_hold = True
        fp.hold_reason = reason
        fp.save(update_fields=['is_on_hold', 'hold_reason'])

        log_audit(
            actor=request.user,
            resource_type='farmer_payment',
            resource_id=fp.id,
            action='HOLD',
            new_value={'reason': reason, 'cycle': str(cycle.id)},
            cooperative_id=self.request.cooperative_id,
        )

        return Response({'status': 'held', 'farmer_payment_id': str(fp.id)})

    @extend_schema(summary="Release held payment", description="Release a previously held farmer payment.")
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        cycle = self.get_object()

        if cycle.status not in ('COMPUTED', 'LOCKED'):
            return Response(
                {'detail': 'Only COMPUTED or LOCKED cycles can be modified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        farmer_payment_id = request.data.get('farmer_payment_id')

        if not farmer_payment_id:
            return Response(
                {'detail': 'farmer_payment_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            fp = FarmerPayment.objects.get(
                id=farmer_payment_id, cycle=cycle,
            )
        except FarmerPayment.DoesNotExist:
            return Response(
                {'detail': 'FarmerPayment not found in this cycle.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        fp.is_on_hold = False
        fp.hold_reason = ''
        fp.save(update_fields=['is_on_hold', 'hold_reason'])

        log_audit(
            actor=request.user,
            resource_type='farmer_payment',
            resource_id=fp.id,
            action='RELEASE',
            cooperative_id=self.request.cooperative_id,
        )

        return Response({'status': 'released', 'farmer_payment_id': str(fp.id)})

    @extend_schema(summary="Task status", description="Returns the Celery task status for the running computation.")
    @action(detail=True, methods=['get'], url_path='task-status')
    def task_status(self, request, pk=None):
        cycle = self.get_object()

        result = {
            'task_id': cycle.celery_task_id,
            'celery_state': None,
            'cycle_status': cycle.status,
            'result': None,
            'warnings': [],
        }

        if cycle.celery_task_id:
            task = AsyncResult(cycle.celery_task_id)
            result['celery_state'] = task.state
            if task.successful():
                result['result'] = task.result

        warnings_qs = ComputationWarning.objects.filter(cycle=cycle)
        result['warnings'] = ComputationWarningSerializer(
            warnings_qs, many=True,
        ).data

        return Response(result)

    @extend_schema(summary="Export cycle as CSV", description="Downloads farmer payments as a CSV file.")
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        import csv
        cycle = self.get_object()
        farmer_payments = FarmerPayment.objects.filter(
            cycle=cycle,
        ).select_related('farmer').order_by('farmer__id')

        from apps.farmers.models import FarmerCooperativeMembership
        farmer_ids = [fp.farmer_id for fp in farmer_payments]
        memberships = {
            m.farmer_id: m
            for m in FarmerCooperativeMembership.objects.filter(
                farmer_id__in=farmer_ids,
                cooperative=cycle.cooperative,
            )
        }

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="cycle_{cycle.name}_payments.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            'member_number', 'farmer_name', 'total_quantity_kg',
            'gross_amount', 'total_deductions', 'withholding_tax_amount',
            'net_amount', 'payment_method', 'payment_status',
        ])

        for fp in farmer_payments:
            membership = memberships.get(fp.farmer_id)
            writer.writerow([
                membership.member_number if membership else '',
                f'{fp.farmer.first_name} {fp.farmer.last_name}',
                fp.total_quantity,
                fp.gross_amount,
                fp.deductions,
                fp.withholding_tax_amount,
                fp.net_amount,
                membership.payment_method if membership else 'M-PESA',
                fp.payment_status,
            ])

        return response
