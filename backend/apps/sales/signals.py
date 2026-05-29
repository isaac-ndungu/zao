from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Sale


@receiver(pre_save, sender=Sale)
def compute_sale_total(sender, instance, **kwargs):
    if instance.quantity and instance.price_per_unit:
        instance.total_amount = instance.quantity * instance.price_per_unit
