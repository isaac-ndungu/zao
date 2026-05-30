import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class Deduction(CooperativeScopedModel):
    DEDUCTION_TYPES = [
        ('LEVY', 'Levy'),
        ('LOAN_REPAYMENT', 'Loan Repayment'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.CASCADE,
        related_name='deductions',
    )
    cycle = models.ForeignKey(
        'payment_engine.PaymentCycle', on_delete=models.CASCADE,
        related_name='deductions',
    )
    deduction_type = models.CharField(
        max_length=20, choices=DEDUCTION_TYPES, db_index=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Deduction'
        verbose_name_plural = 'Deductions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.deduction_type} {self.amount} — {self.farmer} ({self.cycle.name})'
