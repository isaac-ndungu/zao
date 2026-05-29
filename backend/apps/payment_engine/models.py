import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class ComputationWarning(models.Model):
    SEVERITY_CHOICES = [
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(
        'PaymentCycle', on_delete=models.CASCADE,
        related_name='warnings',
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='WARNING')
    message = models.TextField()
    delivery_id = models.UUIDField(null=True, blank=True)
    farmer_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Computation Warning'
        verbose_name_plural = 'Computation Warnings'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.severity}] {self.message[:60]}'


class PaymentCycle(CooperativeScopedModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('COMPUTING', 'Computing'),
        ('COMPUTED', 'Computed'),
        ('LOCKED', 'Locked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True,
    )
    totals = models.JSONField(default=dict, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    total_levy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cooperative_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_loan_repayments = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    has_warnings = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='locked_payment_cycles',
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    computed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Cycle'
        verbose_name_plural = 'Payment Cycles'
        ordering = ['-end_date']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'


class FarmerPayment(CooperativeScopedModel):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(
        PaymentCycle, on_delete=models.CASCADE,
        related_name='farmer_payments',
    )
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.CASCADE,
        related_name='payments',
    )
    total_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grade_breakdown = models.JSONField(default=dict, blank=True)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.JSONField(default=dict, blank=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING', db_index=True,
    )
    computation_log = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Farmer Payment'
        verbose_name_plural = 'Farmer Payments'
        ordering = ['-created_at']
        unique_together = [['cycle', 'farmer']]

    def __str__(self):
        return f'{self.farmer} — {self.cycle.name}'
