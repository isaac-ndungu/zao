from decimal import Decimal

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


@receiver(pre_save, sender=Delivery)
def autofill_location(sender, instance, **kwargs):
    """
    If latitude/longitude are blank, prefer the assigned route_stop, then
    the farmer's saved pickup location. Explicit values always win.
    """
    if instance.latitude is not None and instance.longitude is not None:
        return

    lat, lng = None, None

    if instance.route_stop_id:
        rs = instance.route_stop
        if rs is not None and rs.latitude is not None and rs.longitude is not None:
            lat, lng = rs.latitude, rs.longitude

    if (lat is None or lng is None) and instance.farmer_id:
        farmer = instance.farmer
        if farmer is not None and farmer.latitude is not None and farmer.longitude is not None:
            lat, lng = farmer.latitude, farmer.longitude

    if lat is not None and instance.latitude is None:
        instance.latitude = lat if isinstance(lat, Decimal) else Decimal(str(lat))
    if lng is not None and instance.longitude is None:
        instance.longitude = lng if isinstance(lng, Decimal) else Decimal(str(lng))
