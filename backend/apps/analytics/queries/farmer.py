from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DateField, Q, Sum
from django.db.models.functions import TruncMonth

from apps.deliveries.models import Delivery
from apps.payment_engine.models import FarmerPayment
from apps.loans.models import Loan

from .common import coalesce_sum, compare_periods, parse_period


def get_farmer_production(farmer_id, cooperative_id, start_date, end_date, compare_to=None):
    data = _compute_farmer_production(farmer_id, cooperative_id, start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_farmer_production(farmer_id, cooperative_id, start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_farmer_production(farmer_id, cooperative_id, start_date, end_date):
    qs = Delivery.objects.filter(
        cooperative_id=cooperative_id,
        farmer_id=farmer_id,
        date_delivered__gte=start_date,
        date_delivered__lt=end_date,
    )
    total_kg = float(qs.aggregate(v=coalesce_sum(Sum('quantity_kg')))['v'])

    by_product = dict(
        qs.values('product_type')
        .annotate(kg=coalesce_sum(Sum('quantity_kg')), count=Count('id'))
        .values_list('product_type', 'kg')
    )
    by_status = dict(
        qs.values('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    total = qs.count()
    rejected = qs.filter(status='REJECTED').count()
    rejection_rate = round(rejected / total * 100, 1) if total else 0

    grade_dist = dict(
        qs.exclude(grade='')
        .values('grade')
        .annotate(kg=coalesce_sum(Sum('quantity_kg')))
        .values_list('grade', 'kg')
    )

    monthly = list(
        qs.annotate(month=TruncMonth('date_delivered', output_field=DateField()))
        .values('month', 'product_type')
        .annotate(kg=coalesce_sum(Sum('quantity_kg')), count=Count('id'))
        .order_by('month', 'product_type')
    )
    monthly_series = {}
    for row in monthly:
        m = row['month'].isoformat()
        if m not in monthly_series:
            monthly_series[m] = {}
        monthly_series[m][row['product_type']] = float(row['kg'])

    return {
        'total_kg': total_kg,
        'delivery_count': total,
        'by_product_type': {k: float(v) for k, v in by_product.items()},
        'by_status': {k: v for k, v in by_status.items()},
        'rejection_rate_pct': rejection_rate,
        'grade_distribution': {k: float(v) for k, v in grade_dist.items()},
        'monthly_series': monthly_series,
    }


def get_farmer_financial(farmer_id, cooperative_id, start_date, end_date, compare_to=None):
    data = _compute_farmer_financial(farmer_id, cooperative_id, start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_farmer_financial(farmer_id, cooperative_id, start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_farmer_financial(farmer_id, cooperative_id, start_date, end_date):
    qs = FarmerPayment.objects.filter(
        cooperative_id=cooperative_id,
        farmer_id=farmer_id,
        cycle__end_date__gte=start_date,
        cycle__start_date__lt=end_date,
    )
    agg = qs.aggregate(
        gross=coalesce_sum(Sum('gross_amount')),
        net=coalesce_sum(Sum('net_amount')),
        withholding=coalesce_sum(Sum('withholding_tax_amount')),
        total_quantity=coalesce_sum(Sum('total_quantity')),
    )
    by_status = dict(
        qs.values('payment_status')
        .annotate(count=Count('id'))
        .values_list('payment_status', 'count')
    )
    payment_count = qs.count()

    monthly = list(
        qs.annotate(month=TruncMonth('cycle__end_date', output_field=DateField()))
        .values('month')
        .annotate(gross=coalesce_sum(Sum('gross_amount')), net=coalesce_sum(Sum('net_amount')))
        .order_by('month')
    )
    payout_series = {r['month'].isoformat(): {'gross': float(r['gross']), 'net': float(r['net'])} for r in monthly}

    return {
        'total_gross': float(agg['gross']),
        'total_net': float(agg['net']),
        'total_withholding_tax': float(agg['withholding']),
        'total_quantity': float(agg['total_quantity']),
        'payment_count': payment_count,
        'by_payment_status': {k: v for k, v in by_status.items()},
        'payout_monthly_series': payout_series,
    }


def get_farmer_loans(farmer_id, cooperative_id, start_date, end_date, compare_to=None):
    data = _compute_farmer_loans(farmer_id, cooperative_id, start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_farmer_loans(farmer_id, cooperative_id, start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_farmer_loans(farmer_id, cooperative_id, start_date, end_date):
    qs = Loan.objects.filter(
        cooperative_id=cooperative_id,
        farmer_id=farmer_id,
    )
    agg = qs.aggregate(
        total_outstanding=coalesce_sum(Sum('amount_principal', filter=Q(status__in=['ACTIVE', 'DEFAULTED']))),
        total_disbursed=coalesce_sum(Sum('amount_principal', filter=Q(status__in=['ACTIVE', 'COMPLETED']))),
        active_count=Count('id', filter=Q(status='ACTIVE')),
        defaulted_count=Count('id', filter=Q(status='DEFAULTED')),
        completed_count=Count('id', filter=Q(status='COMPLETED')),
        pending_count=Count('id', filter=Q(status='PENDING')),
    )
    total_loans = agg['active_count'] + agg['defaulted_count'] + agg['completed_count']
    agg['default_rate_pct'] = round(agg['defaulted_count'] / total_loans * 100, 1) if total_loans else 0
    repayment_count = agg['completed_count'] + agg['active_count']
    agg['repayment_rate_pct'] = round(agg['completed_count'] / repayment_count * 100, 1) if repayment_count else 0
    agg['installments_paid'] = int(
        qs.aggregate(v=coalesce_sum(Sum('installments_paid')))['v']
    )
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in agg.items()}
