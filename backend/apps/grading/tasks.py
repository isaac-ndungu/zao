import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction

from apps.deliveries.models import ProductType
from apps.inventory.models import Inventory, Stock
from apps.payment_engine.models import ComputationWarning, PaymentCycle

from .models import Grade

logger = logging.getLogger(__name__)


def _get_delivery_qty(delivery):
    if delivery.product_type == ProductType.MILK:
        return delivery.volume_litres or Decimal('0')
    return delivery.quantity_kg or Decimal('0')


def _get_delivery_unit(delivery):
    return 'litres' if delivery.product_type == ProductType.MILK else 'kg'


@shared_task(soft_time_limit=30, time_limit=60)
def update_inventory_on_grade(grade_id: str):

    try:
        with transaction.atomic():
            grade = Grade.objects.select_for_update().get(id=grade_id)
            if grade.is_inventory_updated:
                return {'status': 'skipped', 'reason': 'Already processed'}

            delivery = grade.delivery
            coop = delivery.cooperative
            product = delivery.product_type
            unit = _get_delivery_unit(delivery)
            qty = _get_delivery_qty(delivery)
            grade_letter = grade.grade_letter or ''

            # Resolve the payment cycle: prefer grade.payment_cycle, else by delivery date.
            cycle = grade.payment_cycle
            if cycle is None:
                cycle = PaymentCycle.objects.filter(
                    cooperative=coop,
                    start_date__lte=delivery.date_delivered.date(),
                    end_date__gte=delivery.date_delivered.date(),
                ).first()
            if cycle is None:
                msg = (
                    f'No PaymentCycle for delivery date {delivery.date_delivered.date()} '
                    f'(coop {coop.id}); grade {grade_id} skipped.'
                )
                logger.error(msg)
                ComputationWarning.objects.create(
                    cooperative=coop, severity='ERROR', message=msg,
                )
                return {'status': 'error', 'reason': 'no cycle for delivery date'}

            # Find-or-create the cycle-pool (the bulk pool for this coop/cycle/product/grade).
            batch_id = f'CYC-{str(cycle.id).split("-")[0]}-{product}-{grade_letter or "NA"}'[:30]
            pool, created = Inventory.objects.get_or_create(
                cooperative=coop,
                payment_cycle=cycle,
                product_type=product,
                grade=grade_letter,
                defaults={
                    'batch_id': batch_id,
                    'unit': unit,
                    'quantity_in': qty,
                    'quantity_out': Decimal('0'),
                    'is_sold': False,
                },
            )
            if not created:
                # Unit consistency (Q4): the pool's unit is immutable.
                if pool.unit != unit:
                    msg = (
                        f'Unit mismatch on inventory pool {pool.batch_id}: '
                        f'pool={pool.unit!r} delivery={unit!r}.'
                    )
                    logger.error(msg)
                    ComputationWarning.objects.create(
                        cooperative=coop, severity='ERROR', message=msg,
                    )
                    raise ValueError(msg)
                pool.quantity_in = (pool.quantity_in or Decimal('0')) + qty

            pool.is_sold = (pool.quantity_in - (pool.quantity_out or Decimal('0'))) <= 0
            pool.save(update_fields=['quantity_in', 'is_sold', 'updated_at'])

            # Find-or-create Stock (the fast aggregate).
            stock, _ = Stock.objects.get_or_create(
                cooperative=coop,
                product_type=product,
                grade=grade_letter,
                defaults={'unit': unit, 'quantity_available': qty},
            )
            if stock.unit != unit:
                msg = (
                    f'Unit mismatch on stock {coop}/{product}/{grade_letter}: '
                    f'{stock.unit!r} vs {unit!r}.'
                )
                logger.error(msg)
                ComputationWarning.objects.create(
                    cooperative=coop, severity='ERROR', message=msg,
                )
                raise ValueError(msg)
            stock.quantity_available = (stock.quantity_available or Decimal('0')) + qty
            stock.save(update_fields=['quantity_available', 'last_updated'])

            grade.is_inventory_updated = True
            grade.save(update_fields=['is_inventory_updated'])

        logger.info(
            'Cycle-pool + stock updated: coop=%s cycle=%s pool=%s grade=%s +%s %s',
            coop.id, cycle.id, pool.batch_id, grade_letter or 'NA', qty, unit,
        )
    except Grade.DoesNotExist:
        logger.error('Grade %s not found. Inventory not updated.', grade_id)
