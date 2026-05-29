import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


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
    computation_log = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Farmer Payment'
        verbose_name_plural = 'Farmer Payments'
        ordering = ['-created_at']
        unique_together = [['cycle', 'farmer']]

    def __str__(self):
        return f'{self.farmer} — {self.cycle.name}'
