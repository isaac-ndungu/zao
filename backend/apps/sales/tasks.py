import logging

from celery import shared_task

from apps.base.utils import log_audit

logger = logging.getLogger(__name__)


@shared_task
def decrement_inventory_on_sale(sale_id: str):
    from apps.inventory.models import Inventory
    from .models import Sale

    try:
        sale = Sale.objects.select_related('inventory').get(id=sale_id)
    except Sale.DoesNotExist:
        logger.error("Sale %s not found. Inventory not decremented.", sale_id)
        return

    inventory = sale.inventory
    available = inventory.quantity_in - inventory.quantity_out

    if sale.quantity > available:
        logger.critical(
            "Sale %s: cannot decrement. Available: %s %s, requested: %s %s. "
            "Inventory %s requires manual review.",
            sale_id, available, inventory.unit, sale.quantity, inventory.unit, inventory.id,
        )
        log_audit(
            actor=sale.recorded_by,
            resource_type='inventory',
            resource_id=inventory.id,
            action='LOCK',
            new_value={
                'error': 'insufficient_balance',
                'available': float(available),
                'requested': float(sale.quantity),
            },
            cooperative_id=sale.cooperative_id,
        )
        return

    inventory.quantity_out += sale.quantity
    if inventory.running_balance <= 0:
        inventory.is_sold = True
    inventory.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])
    logger.info("Inventory %s decremented by %s for sale %s", inventory.id, sale.quantity, sale_id)


@shared_task
def reverse_inventory_on_cancellation(sale_id: str):
    from apps.inventory.models import Inventory
    from .models import Sale

    try:
        sale = Sale.objects.select_related('inventory').get(id=sale_id)
    except Sale.DoesNotExist:
        logger.error("Sale %s not found. Inventory not reversed.", sale_id)
        return

    inventory = sale.inventory
    inventory.quantity_out -= sale.quantity
    if inventory.quantity_out < 0:
        inventory.quantity_out = 0

    if inventory.running_balance > 0:
        inventory.is_sold = False
    inventory.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])
    logger.info("Inventory %s reversed by %s for cancelled sale %s", inventory.id, sale.quantity, sale_id)
