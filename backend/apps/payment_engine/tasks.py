import logging
from decimal import Decimal

from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from .models import FarmerPayment, PaymentCycle

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def run_payment_engine(self, cycle_id: str):
    try:
        cycle = PaymentCycle.objects.select_related('cooperative').get(id=cycle_id)
    except PaymentCycle.DoesNotExist:
        logger.error("Payment cycle %s not found", cycle_id)
        return {'error': 'Cycle not found'}

    if cycle.status == 'LOCKED':
        logger.warning("Cycle %s is locked, skipping", cycle_id)
        return {'error': 'Cycle is locked'}

    cycle.status = 'COMPUTING'
    cycle.save(update_fields=['status'])

    cycle.farmer_payments.all().delete()

    cooperative = cycle.cooperative

    try:
        if cooperative.payment_model == 'FIXED_PRICE':
            from .engine import compute_fixed_price
            farmer_data = compute_fixed_price(cycle)
        elif cooperative.payment_model == 'REVENUE_SHARE':
            from .engine import compute_revenue_share
            farmer_data = compute_revenue_share(cycle)
        else:
            raise ValueError(f"Unknown payment model: {cooperative.payment_model}")

        if not farmer_data:
            logger.warning("Cycle %s: no farmer payments generated", cycle_id)
            cycle.status = 'COMPUTED'
            cycle.totals = {}
            cycle.computed_at = timezone.now()
            cycle.save(update_fields=['status', 'totals', 'computed_at'])
            return {'status': 'COMPUTED', 'cycle_id': cycle_id, 'farmer_count': 0}

        active_count = len(farmer_data)

        for data in farmer_data:
            from .engine import apply_deductions
            fp = FarmerPayment.objects.create(
                cooperative=cycle.cooperative,
                cycle=cycle,
                farmer=data['farmer'],
                total_quantity=data['total_quantity'],
                grade_breakdown=data['grade_breakdown'],
                gross_amount=data['gross_amount'],
            )

            deductions, net = apply_deductions(fp, cooperative, active_count)
            fp.deductions = deductions
            fp.net_amount = net
            fp.computation_log = {
                'method': cooperative.payment_model,
                'total_quantity': float(fp.total_quantity),
                'gross_amount': float(fp.gross_amount),
                'deductions_applied': deductions,
                'net_amount': float(net),
            }
            fp.save(update_fields=['deductions', 'net_amount', 'computation_log'])

        totals = FarmerPayment.objects.filter(cycle=cycle).aggregate(
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_quantity=Sum('total_quantity'),
        )
        cycle.totals = {
            'total_quantity': float(totals['total_quantity'] or 0),
            'total_gross': float(totals['total_gross'] or 0),
            'total_net': float(totals['total_net'] or 0),
            'farmer_count': active_count,
        }
        cycle.status = 'COMPUTED'
        cycle.computed_at = timezone.now()
        cycle.save(update_fields=['totals', 'status', 'computed_at'])

        logger.info("Payment engine completed for cycle %s: %d farmers, NET %s",
                     cycle_id, active_count, cycle.totals['total_net'])
        return {
            'status': 'COMPUTED',
            'cycle_id': cycle_id,
            'farmer_count': active_count,
        }

    except Exception:
        cycle.status = 'DRAFT'
        cycle.computed_at = None
        cycle.save(update_fields=['status', 'computed_at'])
        logger.exception("Payment engine failed for cycle %s, reset to DRAFT", cycle_id)
        raise
