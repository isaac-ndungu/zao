import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class Inventory(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_id = models.CharField(max_length=30, db_index=True)
    product_type = models.CharField(max_length=20)
    grade = models.CharField(max_length=20, blank=True)
    unit = models.CharField(max_length=10)
    quantity_in = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_out = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventory'
        ordering = ['-created_at']

    @property
    def running_balance(self):
        return self.quantity_in - self.quantity_out

    def __str__(self):
        return f'{self.batch_id} — {self.grade or "No grade"} ({self.unit})'
