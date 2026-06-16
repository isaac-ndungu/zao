from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DateField, IntegerField, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth, TruncWeek

from apps.deliveries.models import Delivery
from apps.farmers.models import Farmer
from apps.farmers.models import FarmerCooperativeMembership
from apps.sales.models import Sale
from apps.payment_engine.models import PaymentCycle, FarmerPayment
from apps.grading.models import Grade
from apps.loans.models import Loan
from apps.disbursement.models import DisbursementBatch, DisbursementTransaction
from apps.deductions.models import Deduction
from apps.inventory.models import Inventory

from .common import coalesce_sum, compare_periods, parse_period


def get_admin_dashboard(start_date, end_date, compare_to=None):
    data = _compute_admin_dashboard(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_dashboard(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_dashboard(start_date, end_date):
    farmer_stats = Farmer.objects.all().aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        new_this_period=Count('id', filter=Q(
            date_joined__gte=start_date, date_joined__lt=end_date,
        )),
    )

    delivery_qs = Delivery.objects.filter(
        date_delivered__gte=start_date, date_delivered__lt=end_date,
    )
    delivery_agg = delivery_qs.aggregate(
        total=Count('id'),
        total_kg=coalesce_sum(Sum('quantity_kg')),
    )
    delivery_by_status = dict(
        delivery_qs.values('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    rejected = delivery_qs.filter(status='REJECTED')
    total = delivery_agg['total']
    rejection_rate = round(rejected.count() / total * 100, 1) if total else 0

    grade_dist = dict(
        delivery_qs.exclude(grade='')
        .values('grade')
        .annotate(total=coalesce_sum(Sum('quantity_kg')))
        .values_list('grade', 'total')
    )

    sale_qs = Sale.objects.filter(
        status='COMPLETED', sale_date__gte=start_date, sale_date__lt=end_date,
    )
    revenue_agg = sale_qs.aggregate(total_amount=coalesce_sum(Sum('total_amount')))

    cycle_qs = PaymentCycle.objects.filter(
        end_date__gte=start_date, start_date__lt=end_date,
    )
    cycles_by_status = dict(
        cycle_qs.values('status').annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    cycle_count = cycle_qs.count()

    fp_qs = FarmerPayment.objects.filter(
        cycle__in=cycle_qs.values('id'),
    )
    payout_agg = fp_qs.aggregate(
        total_gross=coalesce_sum(Sum('gross_amount')),
        total_net=coalesce_sum(Sum('net_amount')),
        total_withholding_tax=coalesce_sum(Sum('withholding_tax_amount')),
    )

    ded_qs = Deduction.objects.filter(cycle__in=cycle_qs.values('id'))
    deductions_by_type = dict(
        ded_qs.values('deduction_type')
        .annotate(total=coalesce_sum(Sum('amount')))
        .values_list('deduction_type', 'total')
    )

    loan_qs = Loan.objects.all()
    loan_agg = loan_qs.aggregate(
        total_outstanding=coalesce_sum(
            Sum('amount_principal', filter=Q(status__in=['ACTIVE', 'DEFAULTED']))
        ),
        total_disbursed=coalesce_sum(
            Sum('amount_principal', filter=Q(status='ACTIVE'))
        ),
        active_count=Count('id', filter=Q(status='ACTIVE')),
        defaulted_count=Count('id', filter=Q(status='DEFAULTED')),
        completed_count=Count('id', filter=Q(status='COMPLETED')),
    )
    total_loans = loan_agg['active_count'] + loan_agg['defaulted_count'] + loan_agg['completed_count']
    loan_agg['default_rate_pct'] = round(
        loan_agg['defaulted_count'] / total_loans * 100, 1
    ) if total_loans else 0
    repayment_count = loan_agg['completed_count'] + loan_agg['active_count']
    loan_agg['repayment_rate_pct'] = round(
        loan_agg['completed_count'] / repayment_count * 100, 1
    ) if repayment_count else 0

    batch_qs = DisbursementBatch.objects.filter(
        created_at__gte=start_date, created_at__lt=end_date,
    )
    batches_by_status = dict(
        batch_qs.values('status').annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    disb_agg = batch_qs.aggregate(
        total_disbursed=coalesce_sum(Sum('total_amount')),
        total_transactions=coalesce_sum(Sum('total_transactions'), output_field=IntegerField()),
    )
    successful = batch_qs.aggregate(
        s=coalesce_sum(Sum('successful_count'), output_field=IntegerField()),
    )['s']
    failed = batch_qs.aggregate(
        f=coalesce_sum(Sum('failed_count'), output_field=IntegerField()),
    )['f']
    total_txns = disb_agg['total_transactions']
    disb_agg['success_rate_pct'] = round(
        successful / total_txns * 100, 1
    ) if total_txns else 0

    inv_qs = Inventory.objects.all()
    inv_agg = inv_qs.aggregate(
        total_in=coalesce_sum(Sum('quantity_in')),
        total_out=coalesce_sum(Sum('quantity_out')),
    )

    return {
        'farmers': {
            'total_active': farmer_stats['active'],
            'new_this_period': farmer_stats['new_this_period'],
        },
        'production': {
            'total_kg': float(delivery_agg['total_kg']),
            'delivery_count': delivery_agg['total'],
            'by_status': {k: v for k, v in delivery_by_status.items()},
            'rejection_rate_pct': rejection_rate,
            'grade_distribution': {k: float(v) for k, v in grade_dist.items()},
        },
        'financial': {
            'total_revenue': float(revenue_agg['total_amount']),
            'total_gross_payout': float(payout_agg['total_gross']),
            'total_net_payout': float(payout_agg['total_net']),
            'total_withholding_tax': float(payout_agg['total_withholding_tax']),
            'deductions_breakdown': {k: float(v) for k, v in deductions_by_type.items()},
            'cycle_count': cycle_count,
            'cycles_by_status': {k: v for k, v in cycles_by_status.items()},
        },
        'sales': {
            'total_amount': float(revenue_agg['total_amount']),
        },
        'loans': {
            'total_outstanding': float(loan_agg['total_outstanding']),
            'total_disbursed_this_period': float(loan_agg['total_disbursed']),
            'active_count': loan_agg['active_count'],
            'defaulted_count': loan_agg['defaulted_count'],
            'default_rate_pct': loan_agg['default_rate_pct'],
            'repayment_rate_pct': loan_agg['repayment_rate_pct'],
        },
        'disbursements': {
            'total_batches': batch_qs.count(),
            'batches_by_status': {k: v for k, v in batches_by_status.items()},
            'total_disbursed': float(disb_agg['total_disbursed']),
            'total_transactions': disb_agg['total_transactions'],
            'success_rate_pct': disb_agg['success_rate_pct'],
        },
        'inventory': {
            'total_in': float(inv_agg['total_in']),
            'total_out': float(inv_agg['total_out']),
            'running_balance': float(inv_agg['total_in'] - inv_agg['total_out']),
        },
    }


def get_admin_production(start_date, end_date, compare_to=None):
    data = _compute_admin_production(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_production(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_production(start_date, end_date):
    qs = Delivery.objects.filter(
        date_delivered__gte=start_date, date_delivered__lt=end_date,
    )
    total_kg = float(qs.aggregate(v=coalesce_sum(Sum('quantity_kg')))['v'])
    by_product = dict(
        qs.values('product_type')
        .annotate(kg=coalesce_sum(Sum('quantity_kg')), count=Count('id'))
        .values_list('product_type', 'kg')
    )
    by_status = dict(
        qs.values('status').annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    total = qs.count()
    rejected = qs.filter(status='REJECTED').count()
    rejection_rate = round(rejected / total * 100, 1) if total else 0
    grade_dist = dict(
        qs.exclude(grade='').values('grade')
        .annotate(kg=coalesce_sum(Sum('quantity_kg')))
        .values_list('grade', 'kg')
    )
    by_shift = dict(
        qs.exclude(shift='').values('shift')
        .annotate(count=Count('id'), kg=coalesce_sum(Sum('quantity_kg')))
        .values_list('shift', 'kg')
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
        'by_shift': {k: float(v) for k, v in by_shift.items()},
        'monthly_series': monthly_series,
    }


def get_admin_financial(start_date, end_date, compare_to=None):
    data = _compute_admin_financial(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_financial(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_financial(start_date, end_date):
    cycles = PaymentCycle.objects.filter(
        end_date__gte=start_date, start_date__lt=end_date,
    )
    cycle_ids = cycles.values_list('id', flat=True)

    revenue = float(Sale.objects.filter(
        status='COMPLETED', sale_date__gte=start_date, sale_date__lt=end_date,
    ).aggregate(v=coalesce_sum(Sum('total_amount')))['v'])

    fp_qs = FarmerPayment.objects.filter(cycle_id__in=cycle_ids)
    payout = fp_qs.aggregate(
        gross=coalesce_sum(Sum('gross_amount')),
        net=coalesce_sum(Sum('net_amount')),
        withholding=coalesce_sum(Sum('withholding_tax_amount')),
    )
    deductions = dict(
        Deduction.objects.filter(cycle_id__in=cycle_ids)
        .values('deduction_type').annotate(total=coalesce_sum(Sum('amount')))
        .values_list('deduction_type', 'total')
    )
    cycle_funnel = dict(
        cycles.values('status').annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    by_month = list(
        fp_qs.annotate(month=TruncMonth('cycle__end_date', output_field=DateField()))
        .values('month')
        .annotate(gross=coalesce_sum(Sum('gross_amount')), net=coalesce_sum(Sum('net_amount')))
        .order_by('month')
    )
    payout_series = {r['month'].isoformat(): {'gross': float(r['gross']), 'net': float(r['net'])} for r in by_month}

    return {
        'total_revenue': revenue,
        'total_gross_payout': float(payout['gross']),
        'total_net_payout': float(payout['net']),
        'total_withholding_tax': float(payout['withholding']),
        'deductions_breakdown': {k: float(v) for k, v in deductions.items()},
        'cycle_count': cycles.count(),
        'cycles_by_status': {k: v for k, v in cycle_funnel.items()},
        'payout_monthly_series': payout_series,
    }


def get_admin_farmers(start_date, end_date, compare_to=None):
    data = _compute_admin_farmers(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_farmers(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_farmers(start_date, end_date):
    qs = Farmer.objects.all()
    total_active = qs.filter(is_active=True).count()

    by_county = dict(
        qs.filter(is_active=True).values('county')
        .annotate(count=Count('id'))
        .values_list('county', 'count')
    )
    new_registrations = qs.filter(
        date_joined__gte=start_date, date_joined__lt=end_date,
    ).count()
    monthly_new = list(
        qs.filter(date_joined__gte=start_date, date_joined__lt=end_date)
        .annotate(month=TruncMonth('date_joined', output_field=DateField()))
        .values('month').annotate(count=Count('id'))
        .order_by('month')
    )
    registration_series = {r['month'].isoformat(): r['count'] for r in monthly_new}

    return {
        'total_active': total_active,
        'new_this_period': new_registrations,
        'by_county': dict(by_county),
        'registration_monthly_series': registration_series,
    }


def get_admin_sales(start_date, end_date, compare_to=None):
    data = _compute_admin_sales(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_sales(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_sales(start_date, end_date):
    qs = Sale.objects.filter(
        status='COMPLETED', sale_date__gte=start_date, sale_date__lt=end_date,
    )
    total_amount = float(qs.aggregate(v=coalesce_sum(Sum('total_amount')))['v'])
    total_qty = float(qs.aggregate(v=coalesce_sum(Sum('quantity')))['v'])

    by_buyer = dict(
        qs.values('buyer__name').annotate(total=coalesce_sum(Sum('total_amount')))
        .order_by('-total').values_list('buyer__name', 'total')
    )
    by_product = dict(
        qs.values('product_type')
        .annotate(amount=coalesce_sum(Sum('total_amount')))
        .values_list('product_type', 'amount')
    )
    monthly = list(
        qs.annotate(month=TruncMonth('sale_date', output_field=DateField()))
        .values('month').annotate(amount=coalesce_sum(Sum('total_amount')))
        .order_by('month')
    )
    monthly_series = {r['month'].isoformat(): float(r['amount']) for r in monthly}

    return {
        'total_amount': total_amount,
        'total_quantity': total_qty,
        'by_buyer': {k: float(v) for k, v in by_buyer.items()},
        'by_product_type': {k: float(v) for k, v in by_product.items()},
        'monthly_series': monthly_series,
    }


def get_admin_loans(start_date, end_date, compare_to=None):
    data = _compute_admin_loans(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_loans(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_loans(start_date, end_date):
    qs = Loan.objects.all()
    agg = qs.aggregate(
        total_outstanding=coalesce_sum(Sum('amount_principal', filter=Q(status__in=['ACTIVE', 'DEFAULTED']))),
        total_disbursed=coalesce_sum(Sum('amount_principal', filter=Q(status='ACTIVE'))),
        active_count=Count('id', filter=Q(status='ACTIVE')),
        defaulted_count=Count('id', filter=Q(status='DEFAULTED')),
        completed_count=Count('id', filter=Q(status='COMPLETED')),
        pending_count=Count('id', filter=Q(status='PENDING')),
    )
    total = agg['active_count'] + agg['defaulted_count'] + agg['completed_count']
    agg['default_rate_pct'] = round(agg['defaulted_count'] / total * 100, 1) if total else 0
    repayment_total = agg['completed_count'] + agg['active_count']
    agg['repayment_rate_pct'] = round(agg['completed_count'] / repayment_total * 100, 1) if repayment_total else 0
    agg['total_principal'] = float(qs.aggregate(v=coalesce_sum(Sum('amount_principal')))['v'])
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in agg.items()}


def get_admin_operations(start_date, end_date, compare_to=None):
    data = _compute_admin_operations(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_operations(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_operations(start_date, end_date):
    d_qs = Delivery.objects.filter(
        date_delivered__gte=start_date, date_delivered__lt=end_date,
    )
    total = d_qs.count()
    shift_dist = dict(
        d_qs.exclude(shift='').values('shift')
        .annotate(count=Count('id'), kg=coalesce_sum(Sum('quantity_kg')))
        .values_list('shift', 'count')
    )
    g_qs = Grade.objects.filter(
        created_at__gte=start_date, created_at__lt=end_date,
    )
    grader_throughput = list(
        g_qs.values('delivery__grader__email')
        .annotate(count=Count('id'))
        .order_by('-count')
        .values_list('delivery__grader__email', 'count')[:20]
    )
    rejection_reasons = dict(
        d_qs.filter(status='REJECTED').exclude(rejection_reason='')
        .values('rejection_reason').annotate(count=Count('id'))
        .order_by('-count').values_list('rejection_reason', 'count')[:10]
    )
    grade_overrides = g_qs.filter(is_overridden=True).count()
    avg_daily = list(
        d_qs.annotate(day=TruncMonth('date_delivered', output_field=DateField()))
        .values('day').annotate(count=Count('id'), kg=coalesce_sum(Sum('quantity_kg')))
        .order_by('day')
    )
    return {
        'total_deliveries': total,
        'by_shift': {k: v for k, v in shift_dist.items()},
        'top_graders': [{'email': e, 'count': c} for e, c in grader_throughput],
        'rejection_reasons': dict(rejection_reasons),
        'grade_overrides': grade_overrides,
        'monthly_volume': {r['day'].isoformat(): {'count': r['count'], 'kg': float(r['kg'])} for r in avg_daily},
    }


def get_admin_disbursements(start_date, end_date, compare_to=None):
    data = _compute_admin_disbursements(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    if compare_to == 'previous':
        duration = end_date - start_date
        prev = _compute_admin_disbursements(start_date - duration, start_date)
        result['comparison'] = {'previous_period': prev, 'changes': compare_periods(data, prev)}
    return result


def _compute_admin_disbursements(start_date, end_date):
    batch_qs = DisbursementBatch.objects.filter(
        created_at__gte=start_date, created_at__lt=end_date,
    )
    batches_by_status = dict(
        batch_qs.values('status').annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    agg = batch_qs.aggregate(
        total_amount=coalesce_sum(Sum('total_amount')),
        total_txns=coalesce_sum(Sum('total_transactions'), output_field=IntegerField()),
        successful=coalesce_sum(Sum('successful_count'), output_field=IntegerField()),
        failed=coalesce_sum(Sum('failed_count'), output_field=IntegerField()),
    )
    txn_qs = DisbursementTransaction.objects.filter(
        created_at__gte=start_date, created_at__lt=end_date,
    )
    by_method = dict(
        txn_qs.values('payment_method')
        .annotate(total=coalesce_sum(Sum('amount')), count=Count('id'))
        .values_list('payment_method', 'total')
    )
    by_txn_status = dict(
        txn_qs.values('status').annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    total_txns = agg['total_txns']
    success_rate = round(agg['successful'] / total_txns * 100, 1) if total_txns else 0
    approved = batch_qs.exclude(approved_at__isnull=True)
    avg_approval_hours = approved.extra(
        select={'hours': "EXTRACT(EPOCH FROM (approved_at - created_at)) / 3600"}
    ).aggregate(avg=Avg('hours'))['avg']
    return {
        'total_batches': batch_qs.count(),
        'batches_by_status': {k: v for k, v in batches_by_status.items()},
        'total_disbursed': float(agg['total_amount']),
        'total_transactions': agg['total_txns'],
        'success_rate_pct': success_rate,
        'by_payment_method': {k: float(v) for k, v in by_method.items()},
        'by_transaction_status': {k: v for k, v in by_txn_status.items()},
        'avg_approval_time_hours': round(avg_approval_hours, 1) if avg_approval_hours else None,
    }


def get_admin_seasonal(start_date, end_date, compare_to=None):
    data = _compute_admin_seasonal(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    return result


def _season_label(month):
    m = month.month
    if 3 <= m <= 5:
        return 'LONG_RAINS'
    if 10 <= m <= 12:
        return 'SHORT_RAINS'
    return 'DRY_SEASON'


def _compute_admin_seasonal(start_date, end_date):
    qs = Delivery.objects.filter(
        date_delivered__gte=start_date, date_delivered__lt=end_date,
    )
    monthly = list(
        qs.annotate(month=TruncMonth('date_delivered', output_field=DateField()))
        .values('month', 'product_type')
        .annotate(kg=coalesce_sum(Sum('quantity_kg')), count=Count('id'))
        .order_by('month', 'product_type')
    )
    series = []
    for row in monthly:
        series.append({
            'month': row['month'].isoformat(),
            'product_type': row['product_type'],
            'kg': float(row['kg']),
            'delivery_count': row['count'],
            'season': _season_label(row['month']),
        })
    total_annual = sum(s['kg'] for s in series)
    peak = max(series, key=lambda x: x['kg']) if series else None
    low = min(series, key=lambda x: x['kg']) if series else None
    return {
        'series': series,
        'summary': {
            'total_annual': total_annual,
            'peak_month': peak['month'] if peak else None,
            'peak_kg': peak['kg'] if peak else None,
            'low_month': low['month'] if low else None,
            'low_kg': low['kg'] if low else None,
        },
    }


def get_admin_payment_efficiency(start_date, end_date, compare_to=None):
    data = _compute_admin_payment_efficiency(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    return result


def _compute_admin_payment_efficiency(start_date, end_date):
    cycles = PaymentCycle.objects.filter(
        end_date__gte=start_date, start_date__lt=end_date,
    ).exclude(status='DRAFT')
    batch_map = {
        b.payment_cycle_id: b
        for b in DisbursementBatch.objects.filter(
            payment_cycle_id__in=cycles.values_list('id', flat=True),
        )
    }
    cycle_data = []
    for cycle in cycles:
        batch = batch_map.get(cycle.id)
        c = {'cycle_name': cycle.name, 'status': cycle.status, 'end_date': cycle.end_date.isoformat()}
        if cycle.computed_at and cycle.locked_at:
            c['computation_days'] = (cycle.computed_at.date() - cycle.end_date).days
        if batch and batch.approved_at and cycle.computed_at:
            c['approval_days'] = (batch.approved_at.date() - cycle.computed_at.date()).days
        if batch and batch.status in ('COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED') and batch.approved_at:
            end = batch.updated_at.date() if hasattr(batch, 'updated_at') else batch.approved_at.date()
            c['disbursement_days'] = (end - batch.approved_at.date()).days
        days = [v for k, v in c.items() if k.endswith('_days') and isinstance(v, (int, float))]
        if days:
            c['total_days'] = sum(days)
        cycle_data.append(c)
    days_list = [c['total_days'] for c in cycle_data if 'total_days' in c]
    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else None
    sorted_days = sorted(days_list) if days_list else []
    median = sorted_days[len(sorted_days) // 2] if sorted_days else None
    return {
        'cycles': cycle_data,
        'averages': {
            'avg_total_days': avg_days,
            'median_total_days': median,
            'cycle_count': len(cycle_data),
        },
    }


def get_admin_farmer_retention(start_date, end_date, compare_to=None):
    data = _compute_admin_farmer_retention(start_date, end_date)
    result = {'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()}, 'data': data}
    return result


def _compute_admin_farmer_retention(start_date, end_date):
    memberships = FarmerCooperativeMembership.objects.all()
    farmers = Farmer.objects.all()
    monthly = []
    cursor = start_date
    while cursor < end_date:
        next_month = cursor + timedelta(days=32)
        next_month = next_month.replace(day=1)
        start_active = farmers.filter(
            Q(date_joined__lt=cursor),
            Q(deleted_at__isnull=True) | Q(deleted_at__gte=cursor),
            is_active=True,
        ).count()
        new = farmers.filter(
            date_joined__gte=cursor, date_joined__lt=next_month,
        ).count()
        deactivated = memberships.filter(
            is_active=False, left_at__gte=cursor, left_at__lt=next_month,
        ).count()
        end_active = start_active + new - deactivated
        churn_pct = round(deactivated / start_active * 100, 2) if start_active else 0
        monthly.append({
            'month': cursor.strftime('%Y-%m'),
            'start_count': start_active,
            'new': new,
            'deactivated': deactivated,
            'end_count': end_active,
            'churn_pct': churn_pct,
        })
        cursor = next_month
    recent = monthly[-3:] if len(monthly) >= 3 else monthly
    avg_churn = round(sum(m['churn_pct'] for m in recent) / len(recent), 2) if recent else 0
    if avg_churn < 1:
        trend = 'STABLE'
    elif avg_churn < 3:
        trend = 'DECLINING'
    else:
        trend = 'CRITICAL'
    return {
        'monthly': monthly,
        'trend': trend,
        'avg_monthly_churn_pct': avg_churn,
        'net_growth': monthly[-1]['end_count'] - monthly[0]['start_count'] if len(monthly) > 1 else 0,
    }
