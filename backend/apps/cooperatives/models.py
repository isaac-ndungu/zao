from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
from apps.deliveries.models import Delivery
from apps.deductions.models import Deduction, FarmInputCredit
from apps.disbursement.models import DisbursementBatch, DisbursementTransaction
from apps.farmers.models import Farmer, FarmerCooperativeMembership
from apps.grading.models import Grade
from apps.inventory.models import Inventory
from apps.loans.models import Loan, LoanGuarantor
from apps.notifications.models import Notification
from apps.routes.models import CollectionRoute
from apps.sales.models import Sale, Buyer
import uuid


class CooperativeQuerySet(models.QuerySet):
    def delete(self):
        self.update(deleted_at=timezone.now())


class CooperativeManager(models.Manager):
    def get_queryset(self):
        return CooperativeQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)

    def all_with_trashed(self):
        return CooperativeQuerySet(self.model, using=self._db)

    def trashed_only(self):
        return CooperativeQuerySet(self.model, using=self._db).filter(deleted_at__isnull=False)


class ProduceType(models.TextChoices):
    DAIRY = 'DAIRY', 'Dairy'
    COFFEE = 'COFFEE', 'Coffee'
    HONEY = 'HONEY', 'Honey'


class PaymentModel(models.TextChoices):
    FIXED_PRICE = 'FIXED_PRICE', 'Fixed Price'
    REVENUE_SHARE = 'REVENUE_SHARE', 'Revenue Share'


class Cooperative(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    produce_type = models.CharField(max_length=20, choices=ProduceType.choices)
    payment_model = models.CharField(max_length=20, choices=PaymentModel.choices)
    levy_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_shortcode = models.CharField(max_length=20, blank=True)
    till_number = models.CharField(max_length=12, blank=True)
    float_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    kra_pin = models.CharField(max_length=20, blank=True)
    year_established = models.PositiveSmallIntegerField(null=True, blank=True)
    member_count = models.PositiveIntegerField(default=0)

    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    physical_address = models.TextField(blank=True)

    settlement_bank_name = models.CharField(max_length=100, blank=True)
    settlement_bank_account = models.CharField(max_length=30, blank=True)
    settlement_bank_branch = models.CharField(max_length=100, blank=True)

    payment_day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)

    parent_union = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='members',
    )

    prefix = models.CharField(max_length=10, blank=True, null=True, unique=True)
    last_member_sequence = models.PositiveIntegerField(default=0)
    last_delivery_date = models.DateField(null=True, blank=True)
    last_delivery_sequence = models.IntegerField(default=0)
    inventory = models.JSONField(default=dict, blank=True)
    logo = models.ImageField(upload_to='cooperative_logos/', blank=True)
    minimum_payout_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_share_by_produce_type = models.BooleanField(default=False)
    prorate_new_members = models.BooleanField(default=False)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    deleted_via_cascade_from = models.UUIDField(null=True, blank=True)

    objects = CooperativeManager()

    def delete(self, using=None, keep_parents=False):
        from apps.payment_engine.models import PaymentCycle, FarmerPayment
        User = get_user_model()
        now = timezone.now()
        self.deleted_at = now
        self.save(update_fields=['deleted_at'])
        cascade_models = [
            (Farmer, 'cooperative'),
            (FarmerCooperativeMembership, 'cooperative'),
            (User, 'cooperative'),
            (Delivery, 'cooperative'),
            (PaymentCycle, 'cooperative'),
            (FarmerPayment, 'cooperative'),
            (Loan, 'cooperative'),
            (LoanGuarantor, 'cooperative'),
            (Grade, 'cooperative'),
            (DisbursementBatch, 'cooperative'),
            (DisbursementTransaction, 'cooperative'),
            (Deduction, 'cooperative'),
            (FarmInputCredit, 'cooperative'),
            (Sale, 'cooperative'),
            (Buyer, 'cooperative'),
            (Inventory, 'cooperative'),
            (CollectionRoute, 'cooperative'),
            (Notification, 'cooperative'),
        ]
        for model_cls, field in cascade_models:
            if hasattr(model_cls, 'deleted_at'):
                model_cls.objects.filter(**{field: self}).update(
                    deleted_at=now,
                    deleted_via_cascade_from=self.pk,
                )

    def restore(self):
        from apps.payment_engine.models import PaymentCycle, FarmerPayment
        User = get_user_model()
        now = timezone.now()
        self.deleted_at = None
        self.restored_at = now
        self.deleted_via_cascade_from = None
        self.save(update_fields=['deleted_at', 'restored_at', 'deleted_via_cascade_from'])
        cascade_models = [
            (Farmer, 'cooperative'),
            (FarmerCooperativeMembership, 'cooperative'),
            (User, 'cooperative'),
            (Delivery, 'cooperative'),
            (PaymentCycle, 'cooperative'),
            (FarmerPayment, 'cooperative'),
            (Loan, 'cooperative'),
            (LoanGuarantor, 'cooperative'),
            (Grade, 'cooperative'),
            (DisbursementBatch, 'cooperative'),
            (DisbursementTransaction, 'cooperative'),
            (Deduction, 'cooperative'),
            (FarmInputCredit, 'cooperative'),
            (Sale, 'cooperative'),
            (Buyer, 'cooperative'),
            (Inventory, 'cooperative'),
            (CollectionRoute, 'cooperative'),
            (Notification, 'cooperative'),
        ]
        for model_cls, field in cascade_models:
            if hasattr(model_cls, 'deleted_at'):
                mgr = model_cls.objects
                all_qs = mgr.all_with_trashed() if hasattr(mgr, 'all_with_trashed') else mgr
                all_qs.filter(**{field: self, 'deleted_via_cascade_from': self.pk}).update(
                    deleted_at=None,
                    restored_at=now,
                    deleted_via_cascade_from=None,
                )

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        db_table = 'base_cooperative'
        verbose_name = 'Cooperative'
        verbose_name_plural = 'Cooperatives'

    def __str__(self):
        return self.name
