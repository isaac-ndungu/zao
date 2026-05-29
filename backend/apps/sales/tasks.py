import logging

from celery import shared_task

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
    inventory.quantity_out += sale.quantity
    if inventory.running_balance <= 0:
        inventory.is_sold = True
    inventory.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])
    logger.info("Inventory %s decremented by %s for sale %s", inventory.id, sale.quantity, sale_id)
