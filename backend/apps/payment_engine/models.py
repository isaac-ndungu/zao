from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.db import models

from apps.base.models import CooperativeScopedModel
from apps.cooperatives.models import PaymentModel


class Severity(models.TextChoices):
    WARNING = 'WARNING', 'Warning'
    ERROR = 'ERROR', 'Error'


class CycleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    COMPUTING = 'COMPUTING', 'Computing'
    COMPUTED = 'COMPUTED', 'Computed'
    LOCKED = 'LOCKED', 'Locked'
    DISBURSED = 'DISBURSED', 'Disbursed'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PAID = 'PAID', 'Paid'
    FAILED = 'FAILED', 'Failed'


class ComputationWarning(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(
        'PaymentCycle', on_delete=models.CASCADE,
        related_name='warnings',
    )
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT, db_index=True,
    )
    totals = models.JSONField(default=dict, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True, default='', db_index=True)

    total_levy = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cooperative_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_loan_repayments = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_input_credits = models.DecimalField(max_digits=12, decimal_places=2, default=0)

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

    def clean(self):
        if not self.totals:
            return
        required = {'total_quantity', 'total_gross', 'total_net', 'farmer_count'}
        missing = required - set(self.totals.keys())
        if missing:
            raise ValidationError({'totals': f'Missing required keys: {", ".join(sorted(missing))}.'})


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
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True,
    )
    computation_log = models.JSONField(default=dict, blank=True)
    is_on_hold = models.BooleanField(default=False)
    hold_reason = models.TextField(blank=True)
    withholding_tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_subject_to_withholding_tax = models.BooleanField(default=False)
    carried_forward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    carry_forward_reason = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Farmer Payment'
        verbose_name_plural = 'Farmer Payments'
        ordering = ['-created_at']
        unique_together = [['cycle', 'farmer']]

    def __str__(self):
        return f'{self.farmer} — {self.cycle.name}'

    def clean(self):
        self._validate_grade_breakdown()
        self._validate_deductions()
        self._validate_computation_log()

    def _validate_grade_breakdown(self):
        if not self.grade_breakdown:
            return
        if not isinstance(self.grade_breakdown, dict):
            raise ValidationError({'grade_breakdown': 'Must be a dict.'})
        pm = None
        if self.cycle_id and self.cycle:
            pm = self.cycle.cooperative.payment_model
        if pm == PaymentModel.FIXED_PRICE:
            self._validate_grade_breakdown_fixed_price()
        elif pm == PaymentModel.REVENUE_SHARE:
            self._validate_grade_breakdown_revenue_share()

    def _validate_grade_breakdown_fixed_price(self):
        for grade, data in self.grade_breakdown.items():
            if not isinstance(data, dict) or 'kg' not in data or 'amount' not in data:
                raise ValidationError(
                    {'grade_breakdown': f'Grade "{grade}" must be a dict with kg and amount.'}
                )

    def _validate_grade_breakdown_revenue_share(self):
        for grade, qty in self.grade_breakdown.items():
            if not isinstance(qty, (int, float, Decimal)):
                raise ValidationError(
                    {'grade_breakdown': f'Grade "{grade}" must be a numeric quantity.'}
                )

    def _validate_deductions(self):
        if not self.deductions:
            return
        if not isinstance(self.deductions, dict):
            raise ValidationError({'deductions': 'Must be a dict.'})
        required = {'levy', 'monthly_fee', 'loan_repayment', 'input_credit'}
        missing = required - set(self.deductions.keys())
        if missing:
            raise ValidationError(
                {'deductions': f'Missing required keys: {", ".join(sorted(missing))}.'}
            )

    def _validate_computation_log(self):
        if not self.computation_log:
            return
        if not isinstance(self.computation_log, dict):
            raise ValidationError({'computation_log': 'Must be a dict.'})
        required = {
            'method', 'total_quantity', 'gross_amount',
            'deductions_applied', 'net_amount', 'withholding_tax',
        }
        missing = required - set(self.computation_log.keys())
        if missing:
            raise ValidationError(
                {'computation_log': f'Missing required keys: {", ".join(sorted(missing))}.'}
            )
