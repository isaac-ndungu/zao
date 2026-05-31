import logging
from decimal import Decimal

import redis as redis_module
from celery import shared_task
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import ComputationWarning, FarmerPayment, PaymentCycle

logger = logging.getLogger(__name__)

LOCK_TTL = 1800  # 30 minutes — generous for large cycles


def _acquire_cycle_lock(cycle_id: str, task_id: str) -> bool:
    """Try to acquire a distributed lock for this cycle.

    Returns True if the lock was acquired (caller should proceed),
    False if another worker is already computing this cycle.
    """
    try:
        client = redis_module.from_url(settings.CELERY_BROKER_URL)
        lock_key = f'payment_engine:lock:{cycle_id}'
        # SETNX — only succeeds if key does not exist
        acquired = client.setnx(lock_key, task_id)
        if acquired:
            client.expire(lock_key, LOCK_TTL)
        client.close()
        return bool(acquired)
    except Exception:
        logger.exception("Failed to acquire Redis lock for cycle %s, proceeding without lock", cycle_id)
        return True


def _release_cycle_lock(cycle_id: str):
    try:
        client = redis_module.from_url(settings.CELERY_BROKER_URL)
        client.delete(f'payment_engine:lock:{cycle_id}')
        client.close()
    except Exception:
        logger.exception("Failed to release Redis lock for cycle %s", cycle_id)


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

    # Distributed lock guard — prevent concurrent computation on the same cycle
    if not _acquire_cycle_lock(cycle_id, self.request.id or ''):
        logger.warning(
            "Cycle %s is already being computed by another worker, skipping",
            cycle_id,
        )
        return {'status': 'SKIPPED', 'cycle_id': cycle_id, 'reason': 'Already computing'}

    try:
        cycle.status = 'COMPUTING'
        cycle.celery_task_id = self.request.id or ''
        cycle.save(update_fields=['status', 'celery_task_id'])

        cycle.farmer_payments.all().delete()
        cycle.warnings.all().delete()

        from apps.deductions.models import Deduction
        Deduction.objects.filter(cycle=cycle, deduction_type='LOAN_REPAYMENT').delete()

        cooperative = cycle.cooperative

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
            _release_cycle_lock(cycle_id)
            return {'status': 'COMPUTED', 'cycle_id': cycle_id, 'farmer_count': 0}

        active_count = len(farmer_data)

        total_levy = 0.0
        total_cooperative_fee = 0.0
        total_loan_repayments = 0.0

        for data in farmer_data:
            from .engine import apply_deductions
            farmer = data['farmer']
            gross = data['gross_amount']

            # Carry forward any amount skipped in previous cycles
            prev_carried = FarmerPayment.objects.filter(
                farmer=farmer,
                carry_forward_reason='BELOW_MINIMUM_THRESHOLD',
                payment_status='PENDING',
            ).exclude(cycle=cycle)

            carried_forward_amount = Decimal('0')
            for prev in prev_carried:
                carried_forward_amount += prev.carried_forward_amount
                prev.carry_forward_reason = 'RESOLVED'
                prev.save(update_fields=['carry_forward_reason'])

            carry_forward_reason = ''
            if carried_forward_amount > 0:
                gross += float(carried_forward_amount)
                carry_forward_reason = 'FROM_PREVIOUS_CYCLE'

            fp = FarmerPayment.objects.create(
                cooperative=cycle.cooperative,
                cycle=cycle,
                farmer=farmer,
                total_quantity=data['total_quantity'],
                grade_breakdown=data['grade_breakdown'],
                gross_amount=round(gross, 2),
                carried_forward_amount=carried_forward_amount,
                carry_forward_reason=carry_forward_reason,
            )

            deductions, net = apply_deductions(fp, cooperative, active_count, cycle)
            fp.deductions = deductions
            fp.net_amount = net

            from apps.disbursement.utils import compute_withholding_tax
            tax, is_subject = compute_withholding_tax(
                str(data['farmer'].id), str(cycle.id),
            )
            fp.withholding_tax_amount = tax
            fp.is_subject_to_withholding_tax = is_subject

            fp.computation_log = {
                'method': cooperative.payment_model,
                'total_quantity': float(fp.total_quantity),
                'gross_amount': float(fp.gross_amount),
                'deductions_applied': deductions,
                'net_amount': float(net),
                'withholding_tax': tax,
            }
            fp.save(update_fields=[
                'deductions', 'net_amount', 'withholding_tax_amount',
                'is_subject_to_withholding_tax', 'computation_log',
            ])

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

        _release_cycle_lock(cycle_id)
        return {
            'status': 'COMPUTED',
            'cycle_id': cycle_id,
            'farmer_count': active_count,
            'has_warnings': cycle.has_warnings,
        }

    except Exception:
        _release_cycle_lock(cycle_id)
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
