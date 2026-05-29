import logging
from collections import defaultdict

from django.db.models import Sum

from apps.deliveries.models import Delivery
from apps.sales.models import Sale

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
        if not hasattr(delivery, 'grade_record'):
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
    ).select_related('farmer')

    farmer_kg = defaultdict(float)
    for delivery in deliveries:
        farmer_kg[delivery.farmer_id] += get_delivery_quantity(delivery)

    total_kg = sum(farmer_kg.values())

    if total_kg == 0:
        logger.warning("Cycle %s: no deliveries found for revenue share", cycle.id)
        return []

    results = []
    for farmer_id, kg in farmer_kg.items():
        farmer = deliveries.filter(farmer_id=farmer_id).first().farmer
        gross = (kg / total_kg) * total_revenue
        results.append({
            'farmer': farmer,
            'total_quantity': round(kg, 2),
            'grade_breakdown': {},
            'gross_amount': round(gross, 2),
        })

    return results


def apply_deductions(farmer_payment, cooperative, active_farmer_count):
    gross = float(farmer_payment.gross_amount)
    levy = gross * (float(cooperative.levy_percentage) / 100)
    monthly_fee_share = float(cooperative.monthly_fee) / active_farmer_count if active_farmer_count > 0 else 0
    loan_repayment = 0.0

    deductions = {
        'levy': round(levy, 2),
        'monthly_fee': round(monthly_fee_share, 2),
        'loan_repayment': loan_repayment,
    }

    net = max(gross - levy - monthly_fee_share - loan_repayment, 0)
    return deductions, round(net, 2)
