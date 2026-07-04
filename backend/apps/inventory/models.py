import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class Inventory(CooperativeScopedModel):
    """A bulk pool of graded stock for a (cooperative, payment_cycle, product_type, grade).
    Physically represents the mixed storage (e.g. the Grade A milk tank for cycle 12)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_id = models.CharField(max_length=30, db_index=True)
    product_type = models.CharField(max_length=20)
    grade = models.CharField(max_length=20, blank=True)
    unit = models.CharField(max_length=10)
    quantity_in = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_out = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_sold = models.BooleanField(default=False)
    payment_cycle = models.ForeignKey(
        'payment_engine.PaymentCycle', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='inventory_pools',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventory (cycle pool)'
        verbose_name_plural = 'Inventory (cycle pools)'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['cooperative', 'payment_cycle', 'product_type', 'grade'],
                name='unique_inventory_cycle_pool',
            ),
        ]

    @property
    def running_balance(self):
        return self.quantity_in - self.quantity_out

    def __str__(self):
        return f'{self.batch_id} — {self.grade or "No grade"} ({self.unit})'


class Stock(CooperativeScopedModel):
    """The 'proper inventory' — current total sellable stock per (cooperative, product, grade).
    Updated atomically alongside Inventory in the grading and sale tasks."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_type = models.CharField(max_length=20, db_index=True)
    grade = models.CharField(max_length=20, db_index=True)
    unit = models.CharField(max_length=10)
    quantity_available = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=100)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock'
        verbose_name_plural = 'Stock'
        constraints = [
            models.UniqueConstraint(
                fields=['cooperative', 'product_type', 'grade'],
                name='unique_stock_coop_product_grade',
            ),
        ]

    def __str__(self):
        g = self.grade or 'No grade'
        return f'{self.cooperative} {self.product_type} {g}: {self.quantity_available} {self.unit}'
