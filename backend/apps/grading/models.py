import uuid
from django.core.validators import MinValueValidator
from django.db import models

from apps.base.models import CooperativeScopedModel


class Grade(CooperativeScopedModel):
    GRADE_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('PREMIUM', 'Premium'),
        ('STANDARD', 'Standard'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.OneToOneField(
        'deliveries.Delivery', on_delete=models.CASCADE,
        related_name='grade_record',
    )
    grade_letter = models.CharField(max_length=20, choices=GRADE_CHOICES)
    price_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2,
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grade'
        verbose_name_plural = 'Grades'

    def __str__(self):
        return f'{self.delivery.batch_id} — {self.grade_letter} @ {self.price_per_unit}'


class GradePrice(models.Model):
    GRADE_CHOICES = Grade.GRADE_CHOICES

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
