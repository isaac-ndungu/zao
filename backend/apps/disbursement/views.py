import csv
import io
import logging

from drf_spectacular.utils import extend_schema
from django.db.models import Case, IntegerField, When
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.base.permissions import IsAccountantOrManager, IsManager
from apps.base.utils import log_audit
from apps.base.views import CooperativeScopedViewSet
from apps.payment_engine.models import FarmerPayment

from .models import DisbursementBatch, DisbursementTransaction
from .serializers import (
    ConfirmManualSerializer,
    DisbursementBatchCreateSerializer,
    DisbursementBatchDetailSerializer,
    DisbursementBatchListSerializer,
    DisbursementTransactionSerializer,
)
from .tasks import process_batch_disbursements, update_batch_summary

logger = logging.getLogger(__name__)


class DisbursementViewSet(CooperativeScopedViewSet):
    queryset = DisbursementBatch.objects.all().select_related(
        'payment_cycle', 'cooperative', 'approved_by', 'created_by',
    ).prefetch_related('transactions')

    def get_serializer_class(self):
        if self.action == 'initiate':
            return DisbursementBatchCreateSerializer
        if self.action in ('retrieve',):
            return DisbursementBatchDetailSerializer
        if self.action in ('transactions',):
            return DisbursementTransactionSerializer
        return DisbursementBatchListSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action in ('initiate', 'live', 'retry_failed', 'csv', 'confirm_manual'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        if self.action == 'approve':
            return [IsAuthenticated(), IsManager()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(
            cooperative_id=self.request.cooperative_id,
            created_by=self.request.user,
        )
        log_audit(
            actor=self.request.user,
            resource_type='disbursement_batch',
            resource_id=instance.id,
            action='CREATE',
            new_value={'status': instance.status},
            cooperative_id=self.request.cooperative_id,
        )

    def perform_destroy(self, instance):
        if instance.status not in ('PENDING', 'FAILED'):
            raise serializers.ValidationError(
                'Only PENDING or FAILED batches can be deleted.'
            )
        instance.delete()

    @extend_schema(summary="Initiate disbursement", description="Create a disbursement batch from a LOCKED payment cycle.")
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        serializer = DisbursementBatchCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()

        log_audit(
            actor=request.user,
            resource_type='disbursement_batch',
            resource_id=batch.id,
            action='INITIATE',
            new_value={
                'cycle': str(batch.payment_cycle_id),
                'total_amount': float(batch.total_amount),
                'total_transactions': batch.total_transactions,
            },
            cooperative_id=self.request.cooperative_id,
        )

        return Response(
            DisbursementBatchDetailSerializer(batch, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Approve disbursement", description="Manager approval of a disbursement batch.")
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        batch = self.get_object()

        if batch.status != 'PENDING':
            return Response(
                {'detail': 'Only PENDING batches can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch.status = 'PENDING'
        batch.approved_by = request.user
        batch.approved_at = timezone.now()
        batch.save(update_fields=['status', 'approved_by', 'approved_at'])

        log_audit(
            actor=request.user,
            resource_type='disbursement_batch',
            resource_id=batch.id,
            action='APPROVE',
            cooperative_id=self.request.cooperative_id,
        )

        return Response(DisbursementBatchDetailSerializer(batch).data)

    @extend_schema(summary="Send to M-Pesa", description="Trigger actual M-Pesa B2C disbursement via Daraja API.")
    @action(detail=True, methods=['post'])
    def live(self, request, pk=None):
        batch = self.get_object()

        if batch.status != 'PENDING':
            return Response(
                {'detail': 'Only approved PENDING batches can go live.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = process_batch_disbursements.delay(str(batch.id))
        DisbursementBatch.objects.filter(id=batch.id).update(celery_task_id=task.id)

        log_audit(
            actor=request.user,
            resource_type='disbursement_batch',
            resource_id=batch.id,
            action='LIVE',
            new_value={'task_id': task.id},
            cooperative_id=self.request.cooperative_id,
        )

        return Response({'task_id': task.id, 'status': 'processing'})

    @extend_schema(summary="Retry failed transactions", description="Retry all FAILED transactions in a batch.")
    @action(detail=True, methods=['post'])
    def retry_failed(self, request, pk=None):
        batch = self.get_object()

        failed = batch.transactions.filter(status='FAILED')
        count = failed.count()

        if count == 0:
            return Response(
                {'detail': 'No failed transactions to retry.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        failed.update(
            status='PENDING',
            failure_reason='',
            result_code='',
            result_desc='',
            retry_count=0,
            failed_at=None,
        )

        log_audit(
            actor=request.user,
            resource_type='disbursement_batch',
            resource_id=batch.id,
            action='RETRY',
            new_value={'retry_count': count},
            cooperative_id=self.request.cooperative_id,
        )

        return Response({'retried': count, 'status': 'PENDING'})

    @extend_schema(summary="Export batch as CSV", description="Download disbursement transactions as CSV.")
    @action(detail=True, methods=['get'])
    def csv(self, request, pk=None):
        batch = self.get_object()

        bank_txns = batch.transactions.filter(
            payment_method='BANK', status='PENDING',
        ).select_related('farmer').order_by(
            Case(
                When(payment_method='M_PESA', then=0),
                When(payment_method='BANK', then=1),
                When(payment_method='CASH', then=2),
                output_field=IntegerField(),
            ),
            'farmer__member_number', 'id',
        )

        if not bank_txns.exists():
            return Response(
                {'detail': 'No pending bank transactions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['AccountNumber', 'BeneficiaryName', 'Amount', 'Narration'])

        for txn in bank_txns:
            writer.writerow([
                txn.recipient_identifier,
                txn.recipient_name,
                float(txn.amount),
                f'Coop payment {batch.id!s:.8}',
            ])

        response = HttpResponse(
            output.getvalue(), content_type='text/csv',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="disbursement_{batch.id!s:.8}.csv"'
        )

        log_audit(
            actor=request.user,
            resource_type='disbursement_batch',
            resource_id=batch.id,
            action='CSV_EXPORT',
            new_value={'transaction_count': bank_txns.count()},
            cooperative_id=self.request.cooperative_id,
        )

        return response

    @extend_schema(summary="Confirm manual payment", description="Mark a cash/bank transaction as completed outside M-Pesa.")
    @action(detail=True, methods=['post'])
    def confirm_manual(self, request, pk=None):
        serializer = ConfirmManualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        batch = self.get_object()
        txn_ids = serializer.validated_data['transaction_ids']
        notes = serializer.validated_data.get('notes', '')

        txns = batch.transactions.filter(
            id__in=txn_ids,
            payment_method__in=['BANK', 'CASH'],
        )

        if not txns.exists():
            return Response(
                {'detail': 'No matching BANK/CASH transactions found.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        updated = []
        for txn in txns:
            txn.status = 'SUCCESS'
            txn.completed_at = now
            txn.result_desc = f'Manual confirmation by {request.user.email}'
            if notes:
                txn.failure_reason = notes
            txn.save(update_fields=['status', 'completed_at', 'result_desc', 'failure_reason'])

            if txn.farmer_payment_id:
                FarmerPayment.objects.filter(id=txn.farmer_payment_id).update(
                    payment_status='PAID',
                )
            updated.append(str(txn.id))

        update_batch_summary.delay(str(batch.id))

        log_audit(
            actor=request.user,
            resource_type='disbursement_batch',
            resource_id=batch.id,
            action='CONFIRM_MANUAL',
            new_value={
                'confirmed_count': len(updated),
                'transaction_ids': updated,
            },
            cooperative_id=self.request.cooperative_id,
        )

        return Response({'confirmed': len(updated), 'status': 'SUCCESS'})

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        batch = self.get_object()
        txns = batch.transactions.all().select_related('farmer').order_by('created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            txns = txns.filter(status=status_filter.upper())

        method_filter = request.query_params.get('payment_method')
        if method_filter:
            txns = txns.filter(payment_method=method_filter.upper())

        page = self.paginate_queryset(txns)
        if page is not None:
            serializer = DisbursementTransactionSerializer(
                page, many=True, context={'request': request},
            )
            return self.get_paginated_response(serializer.data)

        serializer = DisbursementTransactionSerializer(
            txns, many=True, context={'request': request},
        )
        return Response(serializer.data)
