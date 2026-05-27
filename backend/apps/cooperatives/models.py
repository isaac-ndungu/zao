from django.db import models
import uuid


class Cooperative(models.Model):
    PRODUCE_CHOICES = [
        ('DAIRY', 'Dairy'),
        ('COFFEE', 'Coffee'),
        ('HONEY', 'Honey'),
    ]
    PAYMENT_MODEL_CHOICES = [
        ('FIXED_PRICE', 'Fixed Price'),
        ('REVENUE_SHARE', 'Revenue Share'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    produce_type = models.CharField(max_length=20, choices=PRODUCE_CHOICES)
    payment_model = models.CharField(max_length=20, choices=PAYMENT_MODEL_CHOICES)
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

    prefix = models.CharField(max_length=10, blank=True)
    last_member_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'base_cooperative'
        verbose_name = 'Cooperative'
        verbose_name_plural = 'Cooperatives'

    def __str__(self):
        return self.name
