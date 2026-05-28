import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _determine_unit(product_type: str, quantity_kg, volume_litres):
    if product_type == 'MILK':
        return 'litres', volume_litres or 0
    return 'kg', quantity_kg or 0


@shared_task
def update_inventory_on_grade(grade_id: str):
    from apps.inventory.models import Inventory

    from .models import Grade

    try:
        grade = Grade.objects.select_related('delivery__cooperative').get(id=grade_id)
    except Grade.DoesNotExist:
        logger.error('Grade %s not found. Inventory not updated.', grade_id)
        return

    delivery = grade.delivery
    coop = delivery.cooperative
    product = delivery.product_type

    unit, qty = _determine_unit(product, delivery.quantity_kg, delivery.volume_litres)

    Inventory.objects.update_or_create(
        batch_id=delivery.batch_id,
        cooperative=coop,
        defaults={
            'product_type': product,
            'grade': grade.grade_letter,
            'unit': unit,
            'quantity_in': qty,
            'quantity_out': 0,
        },
    )

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
