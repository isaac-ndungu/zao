import logging

from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from .models import ComputationWarning, FarmerPayment, PaymentCycle

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
    cycle.celery_task_id = self.request.id or ''

    cycle.save(update_fields=['status', 'celery_task_id'])

    cycle.farmer_payments.all().delete()
    cycle.warnings.all().delete()

    from apps.deductions.models import Deduction
    Deduction.objects.filter(cycle=cycle, deduction_type='LOAN_REPAYMENT').delete()

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
            cycle.total_levy = 0
            cycle.total_cooperative_fee = 0
            cycle.total_loan_repayments = 0
            cycle.has_warnings = cycle.warnings.exists()
            cycle.computed_at = timezone.now()
            cycle.save(update_fields=[
                'status', 'totals', 'total_levy', 'total_cooperative_fee',
                'total_loan_repayments', 'has_warnings', 'computed_at',
            ])
            return {'status': 'COMPUTED', 'cycle_id': cycle_id, 'farmer_count': 0}

        active_count = len(farmer_data)

        total_levy = 0.0
        total_cooperative_fee = 0.0
        total_loan_repayments = 0.0

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

            deductions, net = apply_deductions(fp, cooperative, active_count, cycle)
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

            total_levy += deductions['levy']
            total_cooperative_fee += deductions['monthly_fee']
            total_loan_repayments += deductions['loan_repayment']

        _create_levy_deductions(cycle, farmer_data)

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
        cycle.total_levy = round(total_levy, 2)
        cycle.total_cooperative_fee = round(total_cooperative_fee, 2)
        cycle.total_loan_repayments = round(total_loan_repayments, 2)
        cycle.has_warnings = cycle.warnings.exists()
        cycle.status = 'COMPUTED'
        cycle.computed_at = timezone.now()
        cycle.save(update_fields=[
            'totals', 'total_levy', 'total_cooperative_fee',
            'total_loan_repayments', 'has_warnings', 'status', 'computed_at',
        ])

        logger.info(
            "Payment engine completed for cycle %s: %d farmers, "
            "GROSS %s, LEVY %s, NET %s",
            cycle_id, active_count,
            cycle.totals['total_gross'],
            cycle.total_levy,
            cycle.totals['total_net'],
        )
        return {
            'status': 'COMPUTED',
            'cycle_id': cycle_id,
            'farmer_count': active_count,
            'has_warnings': cycle.has_warnings,
        }

    except Exception:
        cycle.status = 'DRAFT'
        cycle.computed_at = None
        cycle.save(update_fields=['status', 'computed_at'])
        logger.exception("Payment engine failed for cycle %s, reset to DRAFT", cycle_id)
        raise


def _create_levy_deductions(cycle, farmer_data):
    from apps.deductions.models import Deduction
    Deduction.objects.filter(cycle=cycle, deduction_type='LEVY').delete()
    levies = []
    for data in farmer_data:
        farmer = data['farmer']
        gross = data['gross_amount']
        levy_amount = round(gross * (float(cycle.cooperative.levy_percentage) / 100), 2)
        if levy_amount > 0:
            levies.append(Deduction(
                cooperative=cycle.cooperative,
                farmer=farmer,
                cycle=cycle,
                deduction_type='LEVY',
                amount=levy_amount,
                notes='Auto-generated levy deduction',
            ))
    Deduction.objects.bulk_create(levies)
