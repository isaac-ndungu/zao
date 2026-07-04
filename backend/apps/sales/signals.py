from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Sale
from .tasks import decrement_inventory_on_sale, reverse_inventory_on_cancellation


@receiver(pre_save, sender=Sale)
def populate_sale_fields(sender, instance, **kwargs):
    if instance.quantity and instance.price_per_unit and not instance.total_amount:
        instance.total_amount = instance.quantity * instance.price_per_unit

    if instance.pk:
        try:
            old = Sale.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except Sale.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Sale)
def handle_sale_status_change(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)

    if created and instance.status == 'COMPLETED':
        decrement_inventory_on_sale.delay(str(instance.id))

    elif not created:
        if old_status == 'PENDING' and instance.status == 'COMPLETED':
            decrement_inventory_on_sale.delay(str(instance.id))
        elif old_status == 'COMPLETED' and instance.status == 'CANCELLED':
            reverse_inventory_on_cancellation.delay(str(instance.id))
