import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction

from apps.base.utils import log_audit
from apps.inventory.models import Inventory, Stock

from .models import Sale, SaleInventoryLineItem

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, soft_time_limit=30, time_limit=60)
def decrement_inventory_on_sale(self, sale_id: str):
    """FIFO-allocate a sale's quantity across the cooperative's cycle-pools,
    decrement each pool and the Stock aggregate, and record the allocation as
    SaleInventoryLineItem rows. Phase 3 server-side allocation."""

    try:
        with transaction.atomic():
            sale = Sale.objects.select_for_update().get(id=sale_id)
            if sale.inventory_updated:
                return {'status': 'skipped', 'reason': 'Already decremented'}
            if not sale.stock_id:
                return {'status': 'skipped', 'reason': 'No stock FK (legacy sale?)'}

            stock = Stock.objects.select_for_update().get(id=sale.stock_id)
            qty_remaining = sale.quantity
            if qty_remaining <= 0:
                return {'status': 'skipped', 'reason': 'Zero quantity'}

            # FIFO over cycle-pools for (cooperative, product_type, grade), oldest first.
            pools = list(Inventory.objects.select_for_update().filter(
                cooperative_id=sale.cooperative_id,
                payment_cycle__isnull=False,
                product_type=sale.product_type,
                grade=sale.grade_letter,
            ).order_by('created_at'))

            line_items = []
            payment_cycle_assigned = False
            for pool in pools:
                if qty_remaining <= 0:
                    break
                available = (pool.quantity_in or Decimal('0')) - (pool.quantity_out or Decimal('0'))
                if available <= 0:
                    continue
                take = min(available, qty_remaining)
                pool.quantity_out = (pool.quantity_out or Decimal('0')) + take
                pool.is_sold = (pool.quantity_in - pool.quantity_out) <= 0
                pool.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])
                qty_remaining -= take
                line_items.append(SaleInventoryLineItem(
                    sale=sale, inventory=pool, quantity=take,
                ))
                if not payment_cycle_assigned and pool.payment_cycle_id:
                    sale.payment_cycle_id = pool.payment_cycle_id
                    payment_cycle_assigned = True

            if qty_remaining > 0:
                logger.critical(
                    "Sale %s: insufficient stock. Short by %s %s. Stock %s had %s available across %d pool(s).",
                    sale_id, qty_remaining, sale.unit, stock.id,
                    stock.quantity_available, len(pools),
                )
                return {'status': 'error', 'reason': 'insufficient stock',
                        'short': float(qty_remaining)}

            SaleInventoryLineItem.objects.bulk_create(line_items)
            stock.quantity_available = (stock.quantity_available or Decimal('0')) - sale.quantity
            stock.save(update_fields=['quantity_available', 'last_updated'])
            sale.inventory_updated = True
            sale.save(update_fields=['inventory_updated', 'payment_cycle'])

            logger.info(
                "Sale %s allocated FIFO: %s %s across %d pool(s); stock %s now %s.",
                sale_id, sale.quantity, sale.unit, len(line_items),
                stock.id, stock.quantity_available,
            )
            return {'status': 'ok', 'line_items': len(line_items)}
    except Sale.DoesNotExist:
        logger.error("Sale %s not found. Inventory not decremented.", sale_id)


@shared_task(soft_time_limit=30, time_limit=60)
def reverse_inventory_on_cancellation(sale_id: str):
    """Reverse the FIFO allocation for a cancelled sale: restore each
    cycle-pool's quantity_out, restore the Stock aggregate, and delete the
    SaleInventoryLineItem rows."""

    try:
        with transaction.atomic():
            sale = Sale.objects.select_for_update().get(id=sale_id)
            if not sale.inventory_updated:
                return {'status': 'skipped', 'reason': 'Already reversed'}

            line_items = list(sale.line_items.select_related('inventory').all())
            for li in line_items:
                inv = Inventory.objects.select_for_update().get(id=li.inventory_id)
                inv.quantity_out = max(
                    (inv.quantity_out or Decimal('0')) - li.quantity,
                    Decimal('0'),
                )
                inv.is_sold = (inv.quantity_in - inv.quantity_out) > 0
                inv.save(update_fields=['quantity_out', 'is_sold', 'updated_at'])

            if sale.stock_id:
                stock = Stock.objects.select_for_update().get(id=sale.stock_id)
                stock.quantity_available = (
                    (stock.quantity_available or Decimal('0')) + sale.quantity
                )
                stock.save(update_fields=['quantity_available', 'last_updated'])

            sale.line_items.all().delete()
            sale.inventory_updated = False
            sale.save(update_fields=['inventory_updated'])
            logger.info(
                "Sale %s reversed: %d pool(s) restored; stock %s now %s.",
                sale_id, len(line_items),
                stock.id if sale.stock_id else 'N/A',
                stock.quantity_available if sale.stock_id else 'N/A',
            )
    except Sale.DoesNotExist:
        logger.error("Sale %s not found. Inventory not reversed.", sale_id)
