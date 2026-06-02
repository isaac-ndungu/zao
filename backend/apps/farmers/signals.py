from django.contrib.postgres.search import SearchVector
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.cooperatives.models import Cooperative

from .models import Farmer


@receiver(pre_save, sender=Farmer)
def auto_generate_member_number(sender, instance, **kwargs):
    if instance.member_number:
        return

    if not instance.cooperative_id:
        raise ValidationError('cooperative_id is required to generate member number.')

    coop = Cooperative.objects.get(id=instance.cooperative_id)
    year = timezone.now().year
    coop.last_member_sequence += 1
    coop.save(update_fields=['last_member_sequence'])
    instance.member_number = f"{coop.prefix}-{year}-{coop.last_member_sequence:04d}"


@receiver(post_save, sender=Farmer)
def update_search_vector(sender, instance, **kwargs):
    if instance.member_number and (instance.first_name or instance.last_name):
        Farmer.objects.filter(id=instance.id).update(
            search_vector=SearchVector('first_name', 'last_name', 'member_number'),
        )
