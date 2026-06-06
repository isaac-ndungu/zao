import uuid
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from apps.auth_api.models import User
from apps.base.models import CooperativeScopedModel, LocationMixin


class FarmerPaymentMethod(models.TextChoices):
    M_PESA = 'M-PESA', 'M-Pesa'
    BANK = 'BANK', 'Bank Transfer'
    CASH = 'CASH', 'Cash'


class Farmer(LocationMixin, CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='farmer_profile'
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    id_number = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=30, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    has_active_loan = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        verbose_name = 'Farmer'
        verbose_name_plural = 'Farmers'
        indexes = [
            GinIndex(fields=['search_vector']),
        ]

    @property
    def primary_membership(self):
        return self.memberships.order_by('joined_at').first()

    def __str__(self):
        primary = self.primary_membership
        mn = primary.member_number if primary else '---'
        return f'{mn} — {self.first_name} {self.last_name}'


class FarmerCooperativeMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        Farmer, on_delete=models.CASCADE, related_name='memberships'
    )
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative', on_delete=models.CASCADE, related_name='farmer_memberships'
    )
    member_number = models.CharField(max_length=50, editable=False)
    payment_method = models.CharField(max_length=20, choices=FarmerPaymentMethod.choices, default='M-PESA')
    mpesa_number = models.CharField(max_length=30, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    bank_account = models.CharField(max_length=30, blank=True, default='')
    bank_branch = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Farmer Cooperative Membership'
        verbose_name_plural = 'Farmer Cooperative Memberships'
        unique_together = [['farmer', 'cooperative']]
        constraints = [
            models.UniqueConstraint(
                fields=['cooperative', 'member_number'],
                name='unique_member_per_coop'
            ),
        ]

    def __str__(self):
        return f'{self.member_number} @ {self.cooperative_id} — {self.farmer.first_name} {self.farmer.last_name}'
