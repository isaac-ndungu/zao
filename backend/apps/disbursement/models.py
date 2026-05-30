import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class DisbursementBatch(CooperativeScopedModel):
    BATCH_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('PARTIALLY_COMPLETED', 'Partially Completed'),
        ('FAILED', 'Failed'),
    ]
    COMMAND_ID_CHOICES = [
        ('BusinessPayment', 'Business Payment'),
        ('SalaryPayment', 'Salary Payment'),
        ('PromotionPayment', 'Promotion Payment'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_cycle = models.ForeignKey(
        'payment_engine.PaymentCycle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='disbursement_batches',
    )
    status = models.CharField(
        max_length=20, choices=BATCH_STATUS_CHOICES, default='PENDING', db_index=True,
    )
    command_id = models.CharField(
        max_length=20, choices=COMMAND_ID_CHOICES, default='SalaryPayment',
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

    def __str__(self):
        return f'Batch {self.id} — {self.get_status_display()}'


class DisbursementTransaction(CooperativeScopedModel):
    PAYMENT_METHOD_CHOICES = [
        ('M_PESA', 'M-Pesa'),
        ('BANK', 'Bank Transfer'),
        ('CASH', 'Cash'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('QUEUED', 'Queued'),
        ('SENT', 'Sent'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

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
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    recipient_identifier = models.CharField(max_length=100)
    recipient_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True,
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

    def __str__(self):
        return f'{self.farmer} — {self.amount} ({self.get_status_display()})'
