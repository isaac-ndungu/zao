from datetime import date
import uuid

from django.db import models

from apps.base.models import CooperativeScopedModel


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


class PaymentCycle(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Cycle'
        verbose_name_plural = 'Payment Cycles'
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Sale(CooperativeScopedModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    UNIT_CHOICES = [('kg', 'Kilograms'), ('litres', 'Litres')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        Buyer, on_delete=models.PROTECT,
        related_name='sales',
    )
    inventory = models.ForeignKey(
        'inventory.Inventory', on_delete=models.PROTECT,
        related_name='sales',
    )
    payment_cycle = models.ForeignKey(
        PaymentCycle, on_delete=models.SET_NULL,
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
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
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

    def __str__(self):
        return f'{self.invoice_number or "Sale"} — {self.buyer.name} ({self.sale_date})'
