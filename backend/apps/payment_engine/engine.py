import logging
from collections import defaultdict

from django.db import models
from django.db.models import Sum

from apps.deliveries.models import Delivery
from apps.sales.models import Sale

from .models import ComputationWarning

logger = logging.getLogger(__name__)


def get_delivery_quantity(delivery):
    return float(delivery.quantity_kg or delivery.volume_litres or 0)


def compute_fixed_price(cycle):
    deliveries = Delivery.objects.filter(
        cooperative_id=cycle.cooperative_id,
        date_delivered__date__gte=cycle.start_date,
        date_delivered__date__lte=cycle.end_date,
        status__in=['GRADED', 'ACCEPTED'],
    ).select_related('grade_record', 'farmer').order_by('farmer_id')

    farmer_data = defaultdict(lambda: {
        'farmer': None,
        'total_quantity': 0.0,
        'grades': defaultdict(lambda: {'kg': 0.0, 'amount': 0.0}),
    })

    for delivery in deliveries:
        if not hasattr(delivery, 'grade_record') or not delivery.grade_record:
            logger.warning(
                "Delivery %s (farmer %s) has status GRADED but no grade record — skipping",
                delivery.id, delivery.farmer,
            )
            ComputationWarning.objects.create(
                cycle=cycle,
                severity='WARNING',
                message=(
                    f"Delivery {delivery.batch_id} for {delivery.farmer.first_name} "
                    f"{delivery.farmer.last_name} is GRADED but has no Grade record."
                ),
                delivery_id=delivery.id,
                farmer_id=delivery.farmer_id,
            )
            continue

        grade = delivery.grade_record
        if not grade.grade_letter or grade.price_per_unit is None:
            logger.warning(
                "Delivery %s has grade record without grade_letter or price_per_unit, skipping",
                delivery.id,
            )
            continue

        farmer = delivery.farmer
        kg = get_delivery_quantity(delivery)
        amount = kg * float(grade.price_per_unit)

        fd = farmer_data[farmer.id]
        fd['farmer'] = farmer
        fd['total_quantity'] += kg
        fd['grades'][grade.grade_letter]['kg'] += kg
        fd['grades'][grade.grade_letter]['amount'] += amount

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
    total_revenue = Sale.objects.filter(
        cooperative_id=cycle.cooperative_id,
        payment_cycle=cycle,
        status='COMPLETED',
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    total_revenue = float(total_revenue)

    deliveries = Delivery.objects.filter(
        cooperative_id=cycle.cooperative_id,
        date_delivered__date__gte=cycle.start_date,
        date_delivered__date__lte=cycle.end_date,
        status__in=['GRADED', 'ACCEPTED'],
    ).select_related('farmer').order_by('farmer_id')

    farmer_kg = defaultdict(float)
    farmer_grades = defaultdict(lambda: defaultdict(float))
    farmer_map = {}

    for delivery in deliveries:
        farmer_kg[delivery.farmer_id] += get_delivery_quantity(delivery)
        grade = delivery.grade or 'UNGRADED'
        farmer_grades[delivery.farmer_id][grade] += get_delivery_quantity(delivery)

        if delivery.farmer_id not in farmer_map:
            farmer_map[delivery.farmer_id] = delivery.farmer

    total_kg = sum(farmer_kg.values())

    if total_kg == 0:
        logger.warning("Cycle %s: no deliveries found for revenue share", cycle.id)
        ComputationWarning.objects.create(
            cycle=cycle,
            severity='WARNING',
            message=(
                f"No graded deliveries found for this period "
                f"({cycle.start_date} to {cycle.end_date}). "
                f"All farmer payments will be zero."
            ),
        )
        return []

    results = []
    for farmer_id, kg in farmer_kg.items():
        farmer = farmer_map[farmer_id]
        gross = (kg / total_kg) * total_revenue
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


def apply_deductions(farmer_payment, cooperative, active_farmer_count, cycle, undeducted_credits=None):
    gross = float(farmer_payment.gross_amount)
    levy = gross * (float(cooperative.levy_percentage) / 100)
    monthly_fee_share = float(cooperative.monthly_fee) / active_farmer_count if active_farmer_count > 0 else 0

    loan_repayment = 0.0

    from apps.loans.models import Loan
    active_loan = Loan.objects.filter(
        farmer=farmer_payment.farmer,
        status='ACTIVE',
        installments_paid__lt=models.F('number_of_installments'),
    ).first()

    if active_loan:
        loan_repayment = float(active_loan.installment_amount)

        from apps.deductions.models import Deduction
        Deduction.objects.create(
            cooperative=cycle.cooperative,
            farmer=farmer_payment.farmer,
            cycle=cycle,
            deduction_type='LOAN_REPAYMENT',
            amount=active_loan.installment_amount,
            notes=f'Loan installment {active_loan.installments_paid + 1} of {active_loan.number_of_installments}',
        )

        from apps.loans.models import LoanRepayment
        LoanRepayment.objects.create(
            loan=active_loan,
            farmer_payment=farmer_payment,
            amount=active_loan.installment_amount,
        )

        active_loan.installments_paid += 1
        if active_loan.installments_paid >= active_loan.number_of_installments:
            active_loan.status = 'COMPLETED'
        active_loan.save(update_fields=['installments_paid', 'status'])

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
        credit.deducted_in_cycle = cycle
        credit.save(update_fields=['deducted_in_cycle'])
        DedModel.objects.create(
            cooperative=cycle.cooperative,
            farmer=farmer_payment.farmer,
            cycle=cycle,
            deduction_type='INPUT_CREDIT',
            amount=credit.amount,
            notes=credit.item_description,
        )

    deductions = {
        'levy': round(levy, 2),
        'monthly_fee': round(monthly_fee_share, 2),
        'loan_repayment': loan_repayment,
        'input_credit': round(input_credit_total, 2),
    }

    total_deductions = levy + monthly_fee_share + loan_repayment + input_credit_total
    net = max(gross - total_deductions, 0)
    return deductions, round(net, 2)
