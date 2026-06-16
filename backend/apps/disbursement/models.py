import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class BatchStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    PARTIALLY_COMPLETED = 'PARTIALLY_COMPLETED', 'Partially Completed'
    FAILED = 'FAILED', 'Failed'


class CommandId(models.TextChoices):
    BUSINESS_PAYMENT = 'BusinessPayment', 'Business Payment'
    SALARY_PAYMENT = 'SalaryPayment', 'Salary Payment'
    PROMOTION_PAYMENT = 'PromotionPayment', 'Promotion Payment'


class DisbursementPaymentMethod(models.TextChoices):
    M_PESA = 'M_PESA', 'M-Pesa'
    BANK = 'BANK', 'Bank Transfer'
    CASH = 'CASH', 'Cash'


class TransactionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    QUEUED = 'QUEUED', 'Queued'
    SENT = 'SENT', 'Sent'
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class DisbursementBatch(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_cycle = models.ForeignKey(
        'payment_engine.PaymentCycle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='disbursement_batches',
    )
    status = models.CharField(
        max_length=20, choices=BatchStatus.choices, default=BatchStatus.PENDING, db_index=True,
    )
    command_id = models.CharField(
        max_length=20, choices=CommandId.choices, default=CommandId.SALARY_PAYMENT,
    )
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_transactions = models.PositiveIntegerField(default=0)
    successful_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    approved_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_disbursements',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_disbursements',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Disbursement Batch'
        verbose_name_plural = 'Disbursement Batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cooperative', 'created_at', 'status'], name='idx_dsb_coop_date_status'),
        ]

    def __str__(self):
        return f'Batch {self.id} — {self.get_status_display()}'


class DisbursementTransaction(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        DisbursementBatch, on_delete=models.CASCADE,
        related_name='transactions',
    )
    farmer_payment = models.ForeignKey(
        'payment_engine.FarmerPayment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='disbursement_transactions',
    )
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.CASCADE,
        related_name='disbursement_transactions',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=DisbursementPaymentMethod.choices)
    recipient_identifier = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING, db_index=True,
    )
    transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    conversation_id = models.CharField(max_length=100, blank=True, db_index=True)
    originator_conversation_id = models.CharField(max_length=100, blank=True)
    result_code = models.CharField(max_length=20, blank=True)
    result_desc = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    withholding_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Disbursement Transaction'
        verbose_name_plural = 'Disbursement Transactions'
        ordering = ['-created_at']
        unique_together = [['conversation_id', 'transaction_id']]
        indexes = [
            models.Index(fields=['cooperative', 'batch', 'status'], name='idx_dsb_txn_coop_batch_st'),
        ]

    def __str__(self):
        return f'{self.farmer} — {self.amount} ({self.get_status_display()})'
