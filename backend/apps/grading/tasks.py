import logging
from decimal import Decimal

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def update_inventory_on_grade(grade_id: str):
    from .models import Grade

    try:
        grade = Grade.objects.select_related('delivery__cooperative').get(id=grade_id)
    except Grade.DoesNotExist:
        logger.error('Grade %s not found. Inventory not updated.', grade_id)
        return

    delivery = grade.delivery
    coop = delivery.cooperative
    product = delivery.product_type

    inventory = coop.inventory or {}
    current = inventory.get(product, {})

    if grade.rejection_reason:
        current['rejected_qty_kg'] = float(current.get('rejected_qty_kg', 0)) + float(delivery.quantity_kg or 0)
        current['rejected_volume_litres'] = float(current.get('rejected_volume_litres', 0)) + float(delivery.volume_litres or 0)
    else:
        current['graded_qty_kg'] = float(current.get('graded_qty_kg', 0)) + float(delivery.quantity_kg or 0)
        current['graded_volume_litres'] = float(current.get('graded_volume_litres', 0)) + float(delivery.volume_litres or 0)

    inventory[product] = current
    coop.inventory = inventory
    coop.save(update_fields=['inventory'])

    logger.info(
        'Inventory updated for cooperative %s — %s: %s',
        coop.id, product, current,
    )
