import uuid
from django.core.validators import MinValueValidator
from django.db import models

from apps.base.models import CooperativeScopedModel


class GradeImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='grades/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"GradeImage {self.id}"


class GradeLetter(models.TextChoices):
    A = 'A', 'A'
    B = 'B', 'B'
    C = 'C', 'C'
    PREMIUM = 'PREMIUM', 'Premium'
    STANDARD = 'STANDARD', 'Standard'


class DisputeStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    RESOLVED = 'RESOLVED', 'Resolved'
    REJECTED = 'REJECTED', 'Rejected'


class Grade(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.OneToOneField(
        'deliveries.Delivery', on_delete=models.CASCADE,
        related_name='grade_record',
    )
    payment_cycle = models.ForeignKey(
        'payment_engine.PaymentCycle', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='grades',
    )
    grade_letter = models.CharField(max_length=20, choices=GradeLetter.choices, blank=True)
    price_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    rejection_reason = models.TextField(blank=True)
    is_overridden = models.BooleanField(default=False)
    overridden_by = models.ForeignKey(
        'auth_api.User', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='grade_overrides',
    )
    overridden_at = models.DateTimeField(null=True, blank=True)
    override_reason = models.TextField(blank=True)
    is_inventory_updated = models.BooleanField(default=False)
    images = models.ManyToManyField(GradeImage, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grade'
        verbose_name_plural = 'Grades'
        indexes = [
            models.Index(fields=['cooperative', 'created_at'], name='idx_grade_coop_created'),
        ]

    def __str__(self):
        if self.grade_letter:
            return f'{self.delivery.batch_id} — {self.grade_letter} @ {self.price_per_unit}'
        return f'{self.delivery.batch_id} — REJECTED'


class GradePrice(models.Model):
    GRADE_CHOICES = GradeLetter.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grade_letter = models.CharField(max_length=20, choices=GRADE_CHOICES)
    price_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Grade Price'
        verbose_name_plural = 'Grade Prices'
        ordering = ['-effective_from']
        unique_together = [['grade_letter', 'effective_from']]

    def __str__(self):
        return f'{self.grade_letter} @ {self.price_per_unit} (from {self.effective_from})'


class FarmerGradeDispute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, related_name='disputes',
    )
    raised_by = models.ForeignKey(
        'auth_api.User', on_delete=models.CASCADE, related_name='grade_disputes',
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=DisputeStatus.choices, default=DisputeStatus.PENDING, db_index=True,
    )
    resolved_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_disputes',
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Grade Dispute'
        verbose_name_plural = 'Grade Disputes'
        ordering = ['-created_at']

    def __str__(self):
        return f'Dispute on {self.grade} — {self.status}'
