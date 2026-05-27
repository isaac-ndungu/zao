import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class Delivery(CooperativeScopedModel):
    PRODUCT_CHOICES = [
        ('MILK', 'Milk'),
        ('COFFEE_CHERRIES', 'Coffee Cherries'),
        ('HONEY', 'Honey'),
        ('OTHER', 'Other'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('GRADED', 'Graded'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]
    SHIFT_CHOICES = [('AM', 'Morning'), ('PM', 'Evening')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.CASCADE,
        related_name='deliveries',
    )
    grader = models.ForeignKey(
        'auth_api.User', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='graded_deliveries',
    )

    product_type = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    batch_id = models.CharField(max_length=30, unique=True, editable=False)

    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    volume_litres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    grade = models.CharField(max_length=20, blank=True)
    quality_metrics = models.JSONField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    date_delivered = models.DateTimeField(auto_now_add=True)
    shift = models.CharField(max_length=2, choices=SHIFT_CHOICES, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_synced = models.BooleanField(default=True)
    local_id = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Delivery'
        verbose_name_plural = 'Deliveries'
        ordering = ['-date_delivered']

    def __str__(self):
        return f'{self.batch_id} — {self.farmer} ({self.product_type})'
