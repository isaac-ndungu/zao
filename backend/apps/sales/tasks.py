import logging

from celery import shared_task
from django.db import transaction

from apps.base.utils import log_audit

logger = logging.getLogger(__name__)


@shared_task(soft_time_limit=30, time_limit=60)
def decrement_inventory_on_sale(sale_id: str):
    from apps.inventory.models import Inventory
    from .models import Sale

    try:
        with transaction.atomic():
            sale = Sale.objects.select_for_update().get(id=sale_id)

            if sale.inventory_updated:
                return {'status': 'skipped', 'reason': 'Already decremented'}

            line_items = list(sale.line_items.select_related('inventory').all())

            if line_items:
                inventory_ids = sorted([li.inventory_id for li in line_items])
                inventories = {
                    str(i.id): i
                    for i in Inventory.objects.select_for_update().filter(id__in=inventory_ids)
                }
                for li in line_items:
                    inv = inventories[str(li.inventory_id)]
                    available = inv.quantity_in - inv.quantity_out
                    if li.quantity > available:
                        logger.critical(
                            "Sale %s: cannot decrement line item %s. Available: %s %s, "
                            "requested: %s %s. Inventory %s requires manual review.",
                            sale_id, li.id, available, inv.unit, li.quantity, inv.unit, inv.id,
                        )
                        log_audit(
                            actor=sale.recorded_by,
                            resource_type='inventory',
                            resource_id=inv.id,
                            action='LOCK',
                            new_value={
                                'error': 'insufficient_balance',
                                'available': float(available),
                                'requested': float(li.quantity),
                                'line_item_id': str(li.id),
                            },
                            cooperative_id=sale.cooperative_id,
                        )
                        return
                    inv.quantity_out += li.quantity
                    if inv.running_balance <= 0:
                        inv.is_sold = True
                    inv.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])

                logger.info(
                    "Inventory decremented for sale %s across %d batch(es)",
                    sale_id, len(line_items),
                )

            elif sale.inventory:
                inventory = Inventory.objects.select_for_update().get(id=sale.inventory_id)
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

            sale.inventory_updated = True
            sale.save(update_fields=['inventory_updated'])

    except Sale.DoesNotExist:
        logger.error("Sale %s not found. Inventory not decremented.", sale_id)


@shared_task(soft_time_limit=30, time_limit=60)
def reverse_inventory_on_cancellation(sale_id: str):
    from apps.inventory.models import Inventory
    from .models import Sale

    try:
        with transaction.atomic():
            sale = Sale.objects.select_for_update().get(id=sale_id)

            if not sale.inventory_updated:
                return {'status': 'skipped', 'reason': 'Already reversed'}

            line_items = list(sale.line_items.select_related('inventory').all())

            if line_items:
                inventory_ids = sorted([li.inventory_id for li in line_items])
                inventories = {
                    str(i.id): i
                    for i in Inventory.objects.select_for_update().filter(id__in=inventory_ids)
                }
                for li in line_items:
                    inv = inventories[str(li.inventory_id)]
                    inv.quantity_out -= li.quantity
                    if inv.quantity_out < 0:
                        inv.quantity_out = 0
                    if inv.running_balance > 0:
                        inv.is_sold = False
                    inv.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])

                logger.info(
                    "Inventory reversed for cancelled sale %s across %d batch(es)",
                    sale_id, len(line_items),
                )

            elif sale.inventory:
                inventory = Inventory.objects.select_for_update().get(id=sale.inventory_id)
                inventory.quantity_out -= sale.quantity
                if inventory.quantity_out < 0:
                    inventory.quantity_out = 0
                if inventory.running_balance > 0:
                    inventory.is_sold = False
                inventory.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])

                logger.info("Inventory %s reversed by %s for cancelled sale %s", inventory.id, sale.quantity, sale_id)

            sale.inventory_updated = False
            sale.save(update_fields=['inventory_updated'])

    except Sale.DoesNotExist:
        logger.error("Sale %s not found. Inventory not reversed.", sale_id)
