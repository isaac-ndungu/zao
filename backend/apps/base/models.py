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
    produce_type = models.CharField(max_length=20, choices=PRODUCE_CHOICES)
    payment_model = models.CharField(max_length=20, choices=PAYMENT_MODEL_CHOICES)
    levy_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_shortcode = models.CharField(max_length=20, blank=True)
    float_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cooperative'
        verbose_name_plural = 'Cooperatives'

    def __str__(self):
        return self.name


class CooperativeScopedModel(models.Model):
    cooperative = models.ForeignKey(
        Cooperative,
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
    )

    class Meta:
        abstract = True
