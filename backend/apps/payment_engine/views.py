from celery.result import AsyncResult
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import IsAccountantOrManager, IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet

from .models import ComputationWarning, PaymentCycle
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
        if self.action == 'run':
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

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        cycle = self.get_object()

        if cycle.status == 'LOCKED':
            return Response(
                {'detail': 'Cannot run computation on a locked cycle.'},
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

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        cycle = self.get_object()
        serializer = CyclePreviewSerializer(
            cycle, context={'request': request},
        )
        return Response(serializer.data)

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

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        cycle = self.get_object()
        serializer = PaymentCycleStatusSerializer(
            cycle, context={'request': request},
        )
        return Response(serializer.data)

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
