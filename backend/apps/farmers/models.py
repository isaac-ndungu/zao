import uuid
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone

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
    is_active = models.BooleanField(default=True, db_index=True)
    has_active_loan = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        verbose_name = 'Farmer'
        verbose_name_plural = 'Farmers'
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['cooperative', 'is_active', 'county'], name='idx_farmer_coop_active_county'),
            models.Index(fields=['cooperative', 'is_active', 'sub_county'], name='idx_farm_coop_act_subcounty'),
            models.Index(fields=['cooperative'], condition=models.Q(deleted_at__isnull=True), name='idx_farmer_live_records'),
        ]

    @property
    def primary_membership(self):
        return self.memberships.order_by('joined_at').first()

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        primary = self.primary_membership
        mn = primary.member_number if primary else '---'
        return f'{mn} — {self.first_name} {self.last_name}'


class FarmerCooperativeMembershipManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def all_with_trashed(self):
        return super().get_queryset()

    def trashed_only(self):
        return super().get_queryset().filter(deleted_at__isnull=False)


class FarmerCooperativeMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    objects = FarmerCooperativeMembershipManager()
    farmer = models.ForeignKey(
        Farmer, on_delete=models.CASCADE, related_name='memberships'
    )
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative', on_delete=models.CASCADE, related_name='farmer_memberships'
    )
    member_number = models.CharField(max_length=50, editable=False)
    payment_method = models.CharField(max_length=20, choices=FarmerPaymentMethod.choices, default='M-PESA', db_index=True)
    mpesa_number = models.CharField(max_length=30, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    bank_account = models.CharField(max_length=30, blank=True, default='')
    bank_branch = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    deleted_via_cascade_from = models.UUIDField(null=True, blank=True)

    class Meta:
        verbose_name = 'Farmer Cooperative Membership'
        verbose_name_plural = 'Farmer Cooperative Memberships'
        unique_together = [['farmer', 'cooperative']]
        indexes = [
            models.Index(fields=['cooperative', 'is_active', 'payment_method'], name='idx_mem_coop_active_method'),
            models.Index(fields=['cooperative'], condition=models.Q(left_at__isnull=False), name='idx_mem_left_coop'),
            models.Index(fields=['cooperative'], condition=models.Q(deleted_at__isnull=True), name='idx_membership_live_records'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cooperative', 'member_number'],
                name='unique_member_per_coop'
            ),
        ]

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.restored_at = timezone.now()
        self.deleted_via_cascade_from = None
        self.save(update_fields=['deleted_at', 'restored_at', 'deleted_via_cascade_from'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f'{self.member_number} @ {self.cooperative_id} — {self.farmer.first_name} {self.farmer.last_name}'
