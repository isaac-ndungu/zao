from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Farmer


@receiver(pre_save, sender=Farmer)
def auto_generate_member_number(sender, instance, **kwargs):
    if instance.member_number:
        return

    coop = instance.cooperative
    year = timezone.now().year
    coop.last_member_sequence += 1
    coop.save(update_fields=['last_member_sequence'])
    instance.member_number = f"{coop.prefix}-{year}-{coop.last_member_sequence:04d}"
