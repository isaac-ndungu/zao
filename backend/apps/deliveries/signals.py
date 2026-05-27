from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.cooperatives.models import Cooperative

from .models import Delivery


@receiver(pre_save, sender=Delivery)
def auto_generate_batch_id(sender, instance, **kwargs):
    if instance.batch_id:
        return

    today = timezone.localdate()

    with transaction.atomic():
        coop = Cooperative.objects.select_for_update().get(id=instance.cooperative_id)
        if coop.last_delivery_date == today:
            coop.last_delivery_sequence += 1
        else:
            coop.last_delivery_date = today
            coop.last_delivery_sequence = 1
        coop.save(update_fields=['last_delivery_date', 'last_delivery_sequence'])
        instance.batch_id = f"PRODUCE-{today:%Y%m%d}-{coop.last_delivery_sequence:03d}"
