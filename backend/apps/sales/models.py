from datetime import date
import uuid

from django.db import models

from apps.base.models import CooperativeScopedModel


class SaleStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class SaleUnit(models.TextChoices):
    KG = 'kg', 'Kilograms'
    LITRES = 'litres', 'Litres'


class Buyer(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    kra_pin = models.CharField(max_length=20, blank=True)
    physical_address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Buyer'
        verbose_name_plural = 'Buyers'
        ordering = ['name']

    def __str__(self):
        return self.name


class SaleInventoryLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(
        'Sale', on_delete=models.CASCADE,
        related_name='line_items',
    )
    inventory = models.ForeignKey(
        'inventory.Inventory', on_delete=models.PROTECT,
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        unique_together = [['sale', 'inventory']]
        verbose_name = 'Sale Inventory Line Item'
        verbose_name_plural = 'Sale Inventory Line Items'

    def __str__(self):
        return f'{self.quantity} from {self.inventory.batch_id}'


class Sale(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        Buyer, on_delete=models.PROTECT,
        related_name='sales',
    )
    inventory = models.ForeignKey(
        'inventory.Inventory', on_delete=models.PROTECT,
        related_name='sales',
        null=True, blank=True,
    )
    payment_cycle = models.ForeignKey(
        'payment_engine.PaymentCycle', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales',
    )
    recorded_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='recorded_sales',
    )

    product_type = models.CharField(max_length=20)
    grade_letter = models.CharField(max_length=20, blank=True)
    unit = models.CharField(max_length=10, choices=SaleUnit.choices)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    status = models.CharField(max_length=20, choices=SaleStatus.choices, default=SaleStatus.PENDING, db_index=True)
    inventory_updated = models.BooleanField(default=False)
    sale_date = models.DateField(default=date.today, db_index=True)
    invoice_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-sale_date', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['cooperative', 'invoice_number'],
                name='unique_sale_invoice_number',
                condition=models.Q(invoice_number__gt=''),
            ),
        ]

    @property
    def all_inventory(self):
        line_items = self.line_items.select_related('inventory').all()
        if line_items.exists():
            return [(li.inventory, li.quantity) for li in line_items]
        if self.inventory:
            return [(self.inventory, self.quantity)]
        return []

    def __str__(self):
        return f'{self.invoice_number or "Sale"} — {self.buyer.name} ({self.sale_date})'
