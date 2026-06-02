import uuid
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.base.models import CooperativeScopedModel, LocationMixin


class ProductType(models.TextChoices):
    MILK = 'MILK', 'Milk'
    COFFEE_CHERRIES = 'COFFEE_CHERRIES', 'Coffee Cherries'
    HONEY = 'HONEY', 'Honey'
    OTHER = 'OTHER', 'Other'


class DeliveryStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    GRADED = 'GRADED', 'Graded'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    REJECTED = 'REJECTED', 'Rejected'
    PAID = 'PAID', 'Paid'


class Shift(models.TextChoices):
    AM = 'AM', 'Morning'
    PM = 'PM', 'Evening'


class Delivery(LocationMixin, CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.CASCADE,
        related_name='deliveries',
        db_index=True,
    )
    grader = models.ForeignKey(
        'auth_api.User', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='graded_deliveries',
    )

    product_type = models.CharField(max_length=20, choices=ProductType.choices, db_index=True)
    batch_id = models.CharField(max_length=30, unique=True, editable=False, db_index=True)

    quantity_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    volume_litres = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )

    status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING, db_index=True)
    grade = models.CharField(max_length=20, blank=True)
    quality_metrics = models.JSONField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    date_delivered = models.DateTimeField(default=timezone.now, db_index=True)
    shift = models.CharField(max_length=2, choices=Shift.choices, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_synced = models.BooleanField(default=True)
    local_id = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Delivery'
        verbose_name_plural = 'Deliveries'
        ordering = ['-date_delivered']
        constraints = [
            models.UniqueConstraint(
                fields=['cooperative', 'local_id'],
                name='unique_delivery_local_id',
                condition=models.Q(local_id__gt=''),
            ),
        ]

    def __str__(self):
        return f'{self.batch_id} — {self.farmer} ({self.product_type})'
