import logging
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal

import redis as redis_module
from celery import shared_task
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from apps.deductions.models import Deduction, FarmInputCredit
from apps.farmers.models import Farmer
from apps.loans.models import Loan, LoanRepayment

from .engine import FarmerPaymentResult, _compute_deductions
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

    if cycle.status == 'DISBURSED':
        logger.warning("Cycle %s is already disbursed, skipping", cycle_id)
        return {'error': 'Cycle is already disbursed'}

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

        Deduction.objects.filter(cycle=cycle, deduction_type='LOAN_REPAYMENT').delete()
        Deduction.objects.filter(cycle=cycle, deduction_type='INPUT_CREDIT').delete()

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
            cycle.total_input_credits = 0
            cycle.has_warnings = cycle.warnings.exists()
            cycle.computed_at = timezone.now()
            cycle.save(update_fields=[
                'status', 'totals', 'total_levy', 'total_cooperative_fee',
                'total_loan_repayments', 'total_input_credits',
                'has_warnings', 'computed_at',
            ])
            _release_cycle_lock(cycle_id)
            return {'status': 'COMPUTED', 'cycle_id': cycle_id, 'farmer_count': 0}

        # Handle zero-delivery farmers: active members with no deliveries this cycle
        all_active_ids = set(Farmer.objects.filter(
            cooperative=cycle.cooperative, is_active=True,
        ).values_list('id', flat=True))

        present_ids = {d.farmer.id for d in farmer_data}
        missing_ids = all_active_ids - present_ids

        if missing_ids:
            missing_farmers = Farmer.objects.in_bulk(missing_ids)
            for fid, farmer in missing_farmers.items():
                farmer_data.append(FarmerPaymentResult(
                    farmer=farmer,
                    total_quantity=0.0,
                    grade_breakdown={},
                    gross_amount=0.0,
                ))

        active_count = len(farmer_data)

        # Batch carry-forward and input credit queries — avoid N+1 in the loop
        farmer_ids = [d.farmer.id for d in farmer_data]
        all_carried = FarmerPayment.objects.filter(
            farmer_id__in=farmer_ids,
            carry_forward_reason='BELOW_MINIMUM_THRESHOLD',
            payment_status='PENDING',
        ).exclude(cycle=cycle)
        carry_forward_entries = defaultdict(list)
        for cf in all_carried:
            carry_forward_entries[cf.farmer_id].append(cf)

        undeducted_credits = FarmInputCredit.objects.filter(
            farmer_id__in=farmer_ids,
            deducted_in_cycle__isnull=True,
        )
        credits_by_farmer = defaultdict(list)
        for credit in undeducted_credits:
            credits_by_farmer[credit.farmer_id].append(credit)

        # Batch withholding tax — 2 queries total instead of 2 per farmer
        from apps.disbursement.utils import compute_withholding_taxes
        taxes = compute_withholding_taxes(farmer_ids, cycle)

        total_levy = 0.0
        total_cooperative_fee = 0.0
        total_loan_repayments = 0.0
        total_input_credits = 0.0

        # Chunked processing — flush to DB every FLUSH_INTERVAL farmers
        # to keep peak memory proportional to chunk size, not farmer count
        FLUSH_INTERVAL = 500
        farmer_payments = []
        all_loan_deds = []
        all_loan_repayments = []
        updated_loans = []
        all_input_deds = []
        credits_to_update = []
        carry_forward_updates = []
        all_levy_deds = []

        def _flush_chunk():
            for prev in carry_forward_updates:
                prev.save(update_fields=['carry_forward_reason'])
            FarmerPayment.objects.bulk_create(farmer_payments)
            if all_loan_deds:
                Deduction.objects.bulk_create(all_loan_deds)
                LoanRepayment.objects.bulk_create(all_loan_repayments)
                for update in updated_loans:
                    Loan.objects.filter(id=update.loan_id).update(
                        installments_paid=update.installments_paid, status=update.status,
                    )
            if all_input_deds:
                Deduction.objects.bulk_create(all_input_deds)
                for credit, amount_deducted in credits_to_update:
                    credit.total_deducted += Decimal(str(amount_deducted))
                    if credit.total_deducted >= credit.amount:
                        credit.status = 'COMPLETED'
                        credit.deducted_in_cycle = cycle
                        credit.installment_amount = credit.installment_amount or credit.amount
                    credit.save(update_fields=['total_deducted', 'status', 'deducted_in_cycle'])
            if all_levy_deds:
                Deduction.objects.bulk_create(all_levy_deds)

        # Delete existing LEVY deductions once before the chunk loop
        Deduction.objects.filter(cycle=cycle, deduction_type='LEVY').delete()

        for idx, data in enumerate(farmer_data, 1):
            farmer = data.farmer
            gross = data.gross_amount

            # Carry forward any amount skipped in previous cycles
            carried_forward_amount = Decimal('0')
            for prev in carry_forward_entries.get(farmer.id, []):
                carried_forward_amount += prev.carried_forward_amount
                prev.carry_forward_reason = 'RESOLVED'
                carry_forward_updates.append(prev)

            carry_forward_reason = ''
            if carried_forward_amount > 0:
                gross += float(carried_forward_amount)
                carry_forward_reason = 'FROM_PREVIOUS_CYCLE'

            fp = FarmerPayment(
                cooperative=cycle.cooperative,
                cycle=cycle,
                farmer=farmer,
                total_quantity=data.total_quantity,
                grade_breakdown=data.grade_breakdown,
                gross_amount=round(gross, 2),
                carried_forward_amount=carried_forward_amount,
                carry_forward_reason=carry_forward_reason,
            )

            deductions, net, pending = _compute_deductions(
                fp, cooperative, active_count, cycle,
                credits_by_farmer.get(farmer.id, []),
            )
            fp.deductions = asdict(deductions)
            fp.net_amount = net

            tax, is_subject = taxes.get(farmer.id, (0.0, False))
            fp.withholding_tax_amount = tax
            fp.is_subject_to_withholding_tax = is_subject

            fp.computation_log = {
                'method': cooperative.payment_model,
                'total_quantity': float(fp.total_quantity),
                'gross_amount': float(fp.gross_amount),
                'deductions_applied': asdict(deductions),
                'net_amount': float(net),
                'withholding_tax': tax,
            }
            farmer_payments.append(fp)

            if pending.loan_repayment_ded:
                all_loan_deds.append(pending.loan_repayment_ded)
                all_loan_repayments.append(pending.loan_repayment_record)
                updated_loans.append(pending.updated_loan)
            all_input_deds.extend(pending.input_credit_deds)
            credits_to_update.extend(pending.updated_credits)

            total_levy += deductions.levy
            total_cooperative_fee += deductions.monthly_fee
            total_loan_repayments += deductions.loan_repayment
            total_input_credits += deductions.input_credit

            # Accumulate levy deduction (original gross, before carry-forward)
            levy_amount = round(data.gross_amount * (float(cooperative.levy_percentage) / 100), 2)
            if levy_amount > 0:
                all_levy_deds.append(Deduction(
                    cooperative=cycle.cooperative,
                    farmer=farmer,
                    cycle=cycle,
                    deduction_type='LEVY',
                    amount=levy_amount,
                    notes='Auto-generated levy deduction',
                ))

            # Flush to DB periodically to keep peak memory bounded
            if idx % FLUSH_INTERVAL == 0:
                _flush_chunk()
                farmer_payments = []
                all_loan_deds = []
                all_loan_repayments = []
                updated_loans = []
                all_input_deds = []
                credits_to_update = []
                carry_forward_updates = []
                all_levy_deds = []

        # Final flush for remaining farmers
        _flush_chunk()

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
        cycle.total_input_credits = round(total_input_credits, 2)
        cycle.has_warnings = cycle.warnings.exists()
        cycle.status = 'COMPUTED'
        cycle.computed_at = timezone.now()
        cycle.save(update_fields=[
            'totals', 'total_levy', 'total_cooperative_fee',
            'total_loan_repayments', 'total_input_credits',
            'has_warnings', 'status', 'computed_at',
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

