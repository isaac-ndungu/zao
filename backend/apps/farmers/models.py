import uuid
from django.db import models

from apps.auth_api.models import User
from apps.base.models import CooperativeScopedModel


class Farmer(CooperativeScopedModel):
    PAYMENT_METHOD_CHOICES = [
        ('M-PESA', 'M-Pesa'),
        ('BANK', 'Bank Transfer'),
        ('CASH', 'Cash'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='farmer_profile'
    )
    member_number = models.CharField(max_length=50, unique=True, editable=False)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20, unique=True)
    mpesa_number = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=30, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Farmer'
        verbose_name_plural = 'Farmers'

    def __str__(self):
        return f'{self.member_number} — {self.first_name} {self.last_name}'
