import logging
from collections import defaultdict
from decimal import Decimal

from django.db import models
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from apps.deliveries.models import Delivery
from apps.farmers.models import Farmer
from apps.grading.models import GradePrice
from apps.sales.models import Sale

from .models import ComputationWarning

logger = logging.getLogger(__name__)


def get_delivery_quantity(delivery):
    return float(delivery.quantity_kg or delivery.volume_litres or 0)


def compute_fixed_price(cycle):
    # Query 1: create warnings for GRADED deliveries without a grade record
    ungraded = Delivery.objects.filter(
        cooperative_id=cycle.cooperative_id,
        date_delivered__date__gte=cycle.start_date,
        date_delivered__date__lte=cycle.end_date,
        status__in=['GRADED', 'ACCEPTED'],
        grade_record__isnull=True,
    ).select_related('farmer')
    for d in ungraded:
        logger.warning(
            "Delivery %s (farmer %s) has status GRADED but no grade record — skipping",
            d.id, d.farmer,
        )
        ComputationWarning.objects.create(
            cycle=cycle, severity='WARNING',
            message=(
                f"Delivery {d.batch_id} for {d.farmer.first_name} "
                f"{d.farmer.last_name} is GRADED but has no Grade record."
            ),
            delivery_id=d.id, farmer_id=d.farmer_id,
        )

    # Step 1: fetch active GradePrice records — one per grade_letter, newest before cycle end
    all_prices = GradePrice.objects.filter(
        effective_from__lte=cycle.end_date,
    ).order_by('grade_letter', '-effective_from')
    price_map = {}
    for gp in all_prices:
        if gp.grade_letter not in price_map:
            price_map[gp.grade_letter] = float(gp.price_per_unit)

    # Query 2: aggregate delivery quantities by (farmer_id, grade_letter)
    agg = (
        Delivery.objects.filter(
            cooperative_id=cycle.cooperative_id,
            date_delivered__date__gte=cycle.start_date,
            date_delivered__date__lte=cycle.end_date,
            status__in=['GRADED', 'ACCEPTED'],
            grade_record__isnull=False,
            grade_record__grade_letter__isnull=False,
        )
        .values('farmer_id', 'grade_record__grade_letter')
        .annotate(
            total_kg=Coalesce(Sum('quantity_kg'), Value(Decimal('0')))
            + Coalesce(Sum('volume_litres'), Value(Decimal('0'))),
        )
    )

    # Query 3: fetch all referenced farmers in one batch
    farmer_ids = set(r['farmer_id'] for r in agg)
    farmers = Farmer.objects.in_bulk(farmer_ids) if farmer_ids else {}

    # Pure Python accumulation — no more DB hits
    farmer_data = defaultdict(lambda: {
        'farmer': None,
        'total_quantity': 0.0,
        'grades': defaultdict(lambda: {'kg': 0.0, 'amount': 0.0}),
    })

    for row in agg:
        fid = row['farmer_id']
        grade = row['grade_record__grade_letter']
        kg = float(row['total_kg'])
        price = price_map.get(grade)
        if price is None:
            continue
        amount = kg * price
        fd = farmer_data[fid]
        fd['farmer'] = farmers[fid]
        fd['total_quantity'] += kg
        fd['grades'][grade]['kg'] += kg
        fd['grades'][grade]['amount'] += amount

    results = []
    for fd in farmer_data.values():
        gross = sum(g['amount'] for g in fd['grades'].values())
        results.append({
            'farmer': fd['farmer'],
            'total_quantity': round(fd['total_quantity'], 2),
            'grade_breakdown': {
                grade: {'kg': round(v['kg'], 2), 'amount': round(v['amount'], 2)}
                for grade, v in fd['grades'].items()
            },
            'gross_amount': round(gross, 2),
        })

    return results


def compute_revenue_share(cycle):
    cooperative = cycle.cooperative

    # Aggregate deliveries first — check for existence before touching sales
    agg = (
        Delivery.objects.filter(
            cooperative_id=cycle.cooperative_id,
            date_delivered__date__gte=cycle.start_date,
            date_delivered__date__lte=cycle.end_date,
            status__in=['GRADED', 'ACCEPTED'],
        )
        .values('farmer_id', 'product_type', 'grade')
        .annotate(
            total_kg=Coalesce(Sum('quantity_kg'), Value(Decimal('0')))
            + Coalesce(Sum('volume_litres'), Value(Decimal('0'))),
        )
    )

    farmer_ids = set(r['farmer_id'] for r in agg)
    farmers = Farmer.objects.in_bulk(farmer_ids) if farmer_ids else {}

    # Per-farmer aggregates: total kg and breakdowns
    farmer_total_kg = defaultdict(float)
    farmer_type_kg = defaultdict(lambda: defaultdict(float))
    farmer_grades = defaultdict(lambda: defaultdict(float))
    farmer_map = {}

    for row in agg:
        fid = row['farmer_id']
        ptype = row['product_type']
        grade = row['grade'] or 'UNGRADED'
        kg = float(row['total_kg'])
        farmer_total_kg[fid] += kg
        farmer_type_kg[fid][ptype] += kg
        farmer_grades[fid][grade] += kg
        if fid not in farmer_map:
            farmer_map[fid] = farmers.get(fid)

    total_kg_by_type = defaultdict(float)
    for row in agg:
        total_kg_by_type[row['product_type']] += float(row['total_kg'])

    total_kg = sum(farmer_total_kg.values())

    if total_kg == 0:
        logger.warning("Cycle %s: no deliveries found for revenue share", cycle.id)
        ComputationWarning.objects.create(
            cycle=cycle, severity='WARNING',
            message=(
                f"No graded deliveries found for this period "
                f"({cycle.start_date} to {cycle.end_date}). "
                f"All farmer payments will be zero."
            ),
        )
        return []

    # Edge Case 3 — include unlinked sales (sale_date in range, payment_cycle=None)
    linked = Sale.objects.filter(
        cooperative_id=cycle.cooperative_id,
        payment_cycle=cycle,
        status='COMPLETED',
    )
    unlinked = Sale.objects.filter(
        cooperative_id=cycle.cooperative_id,
        sale_date__gte=cycle.start_date,
        sale_date__lte=cycle.end_date,
        payment_cycle__isnull=True,
        status='COMPLETED',
    )
    sales_by_id = {}
    for s in list(linked) + list(unlinked):
        sales_by_id[s.id] = s

    if not sales_by_id:
        logger.warning("Cycle %s: no sales found for revenue share", cycle.id)
        ComputationWarning.objects.create(
            cycle=cycle, severity='WARNING',
            message=(
                f"No completed sales found for this period "
                f"({cycle.start_date} to {cycle.end_date}). "
                f"All farmer payments will be zero."
            ),
        )
        return []

    # Build revenue pools
    total_revenue_map = defaultdict(float)
    for s in sales_by_id.values():
        total_revenue_map[s.product_type] += float(s.total_amount)

    # Edge Case 1 — single farmer warning
    if len(farmer_total_kg) == 1:
        sole_farmer = next(iter(farmer_map.values()))
        ComputationWarning.objects.create(
            cycle=cycle, severity='INFO',
            message=(
                f"Single farmer ({sole_farmer.first_name} {sole_farmer.last_name}) "
                f"made all deliveries this cycle — receives 100% of revenue share."
            ),
        )

    results = []
    for farmer_id, kg in farmer_total_kg.items():
        farmer = farmer_map[farmer_id]

        # Edge Case 4 — prorate for new members
        if cooperative.prorate_new_members and farmer and farmer.date_joined.date() > cycle.start_date:
            total_days = (cycle.end_date - cycle.start_date).days + 1
            active_days = (cycle.end_date - farmer.date_joined.date()).days + 1
            proration = active_days / total_days if total_days > 0 else 1.0
        else:
            proration = 1.0

        # Edge Case 2 — split revenue by produce_type when enabled
        if cooperative.revenue_share_by_produce_type:
            gross = 0.0
            for ptype, rev in total_revenue_map.items():
                type_kg_total = total_kg_by_type.get(ptype, 0)
                if type_kg_total > 0:
                    farmer_type_qty = farmer_type_kg[farmer_id].get(ptype, 0)
                    gross += (farmer_type_qty / type_kg_total) * rev
        else:
            gross = (kg / total_kg) * sum(total_revenue_map.values())

        gross *= proration

        grade_breakdown = {
            grade: round(qty, 2)
            for grade, qty in farmer_grades[farmer_id].items()
        }
        results.append({
            'farmer': farmer,
            'total_quantity': round(kg, 2),
            'grade_breakdown': grade_breakdown,
            'gross_amount': round(gross, 2),
        })

    return results


def _compute_deductions(farmer_payment, cooperative, active_farmer_count, cycle, undeducted_credits=None):
    """Pure computation of deductions — no DB writes.

    Returns (deductions_dict, net_amount, pending) where pending contains
    objects the caller should bulk_create/bulk_update.
    """
    gross = float(farmer_payment.gross_amount)
    levy = gross * (float(cooperative.levy_percentage) / 100)
    monthly_fee_share = float(cooperative.monthly_fee) / active_farmer_count if active_farmer_count > 0 else 0

    loan_repayment = 0.0
    pending = {
        'loan_repayment_ded': None,
        'loan_repayment_record': None,
        'updated_loan': None,
        'input_credit_deds': [],
        'updated_credits': [],
    }

    from apps.loans.models import Loan
    active_loan = Loan.objects.filter(
        farmer=farmer_payment.farmer,
        status='ACTIVE',
        installments_paid__lt=models.F('number_of_installments'),
    ).first()

    if active_loan:
        loan_repayment = float(active_loan.installment_amount)

        from apps.deductions.models import Deduction
        pending['loan_repayment_ded'] = Deduction(
            cooperative=cycle.cooperative,
            farmer=farmer_payment.farmer,
            cycle=cycle,
            deduction_type='LOAN_REPAYMENT',
            amount=active_loan.installment_amount,
            notes=f'Loan installment {active_loan.installments_paid + 1} of {active_loan.number_of_installments}',
        )

        from apps.loans.models import LoanRepayment
        pending['loan_repayment_record'] = LoanRepayment(
            loan=active_loan,
            farmer_payment=farmer_payment,
            amount=active_loan.installment_amount,
        )

        new_installments = active_loan.installments_paid + 1
        new_status = 'COMPLETED' if new_installments >= active_loan.number_of_installments else 'ACTIVE'
        pending['updated_loan'] = (active_loan.id, new_installments, new_status)

    input_credit_total = 0.0
    from apps.deductions.models import FarmInputCredit as FIC, Deduction as DedModel
    if undeducted_credits is None:
        undeducted = FIC.objects.filter(
            farmer=farmer_payment.farmer,
            deducted_in_cycle__isnull=True,
        )
    else:
        undeducted = undeducted_credits
    for credit in undeducted:
        input_credit_total += float(credit.amount)
        pending['input_credit_deds'].append(
            DedModel(
                cooperative=cycle.cooperative,
                farmer=farmer_payment.farmer,
                cycle=cycle,
                deduction_type='INPUT_CREDIT',
                amount=credit.amount,
                notes=credit.item_description,
            )
        )
        pending['updated_credits'].append(credit)

    deductions = {
        'levy': round(levy, 2),
        'monthly_fee': round(monthly_fee_share, 2),
        'loan_repayment': loan_repayment,
        'input_credit': round(input_credit_total, 2),
    }

    total_deductions = levy + monthly_fee_share + loan_repayment + input_credit_total
    net = max(gross - total_deductions, 0)
    return deductions, round(net, 2), pending


def apply_deductions(farmer_payment, cooperative, active_farmer_count, cycle, undeducted_credits=None):
    """Legacy wrapper — computes and writes. Kept for test backward compatibility."""
    deductions, net, pending = _compute_deductions(
        farmer_payment, cooperative, active_farmer_count, cycle, undeducted_credits,
    )

    if pending['loan_repayment_ded']:
        pending['loan_repayment_ded'].save()
        pending['loan_repayment_record'].save()
        loan_id, installments, status = pending['updated_loan']
        from apps.loans.models import Loan
        Loan.objects.filter(id=loan_id).update(installments_paid=installments, status=status)

    for credit in pending['updated_credits']:
        credit.deducted_in_cycle = cycle
        credit.save(update_fields=['deducted_in_cycle'])

    if pending['input_credit_deds']:
        from apps.deductions.models import Deduction
        Deduction.objects.bulk_create(pending['input_credit_deds'])

    return deductions, net
