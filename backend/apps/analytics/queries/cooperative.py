from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Count, IntegerField, Sum, Q
from django.db.models.functions import Coalesce

from apps.deliveries.models import Delivery
from apps.farmers.models import Farmer
from apps.sales.models import Sale
from apps.payment_engine.models import PaymentCycle, FarmerPayment
from apps.loans.models import Loan
from apps.disbursement.models import DisbursementBatch
from apps.deductions.models import Deduction
from apps.inventory.models import Inventory

from .common import coalesce_sum, compare_periods


def get_dashboard(cooperative_id, start_date, end_date, compare_to=None):
    """Compute cooperative dashboard for a date range.

    Returns a dict with period metadata and all dashboard metrics.
    If compare_to='previous', includes a comparison with the prior
    period.
    """
    data = _compute_dashboard(cooperative_id, start_date, end_date)

    result = {
        'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
        'data': data,
    }

    if compare_to == 'previous':
        duration = end_date - start_date
        prev_start = start_date - duration
        prev_data = _compute_dashboard(cooperative_id, prev_start, start_date)
        result['comparison'] = {
            'previous_period': {
                'start': prev_start.isoformat(),
                'end': start_date.isoformat(),
                'data': prev_data,
            },
            'changes': compare_periods(data, prev_data),
        }

    return result


def _compute_dashboard(cooperative_id, start_date, end_date):
    """Core dashboard aggregation. All Sums wrapped in Coalesce."""

    # --- Farmers ---
    farmer_stats = Farmer.objects.filter(
        cooperative_id=cooperative_id,
    ).aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        new_this_period=Count('id', filter=Q(
            date_joined__gte=start_date,
            date_joined__lt=end_date,
        )),
    )

    # --- Deliveries ---
    delivery_qs = Delivery.objects.filter(
        cooperative_id=cooperative_id,
        date_delivered__gte=start_date,
        date_delivered__lt=end_date,
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
    rejection_rate = round(
        (rejected.count() / total * 100) if total else 0, 1
    )

    grade_dist = dict(
        delivery_qs.exclude(grade='')
        .values('grade')
        .annotate(total=coalesce_sum(Sum('quantity_kg')))
        .values_list('grade', 'total')
    )

    # --- Sales ---
    sale_qs = Sale.objects.filter(
        cooperative_id=cooperative_id,
        status='COMPLETED',
        sale_date__gte=start_date,
        sale_date__lt=end_date,
    )
    revenue_agg = sale_qs.aggregate(
        total_amount=coalesce_sum(Sum('total_amount')),
    )
    sales_by_buyer = dict(
        sale_qs.values('buyer__name')
        .annotate(total=coalesce_sum(Sum('total_amount')))
        .values_list('buyer__name', 'total')
    )

    price_trend = defaultdict(lambda: {'total': Decimal('0'), 'count': 0})
    for s in sale_qs.values('grade_letter', 'price_per_unit', 'quantity'):
        grade = s['grade_letter'] or 'UNGRADED'
        price_trend[grade]['total'] += s['price_per_unit'] * s['quantity']
        price_trend[grade]['count'] += s['quantity']
    price_summary = {}
    for grade, vals in price_trend.items():
        avg_price = round(vals['total'] / vals['count'], 2) if vals['count'] else 0
        price_summary[grade] = {'avg_price': avg_price}

    # --- Payment Cycles ---
    cycle_qs = PaymentCycle.objects.filter(
        cooperative_id=cooperative_id,
        end_date__gte=start_date,
        start_date__lt=end_date,
    )
    cycles_by_status = dict(
        cycle_qs.values('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    cycle_count = cycle_qs.count()

    # --- Farmer Payments ---
    fp_qs = FarmerPayment.objects.filter(
        cooperative_id=cooperative_id,
        cycle__in=cycle_qs.values('id'),
    )
    payout_agg = fp_qs.aggregate(
        total_gross=coalesce_sum(Sum('gross_amount')),
        total_net=coalesce_sum(Sum('net_amount')),
        total_withholding_tax=coalesce_sum(Sum('withholding_tax_amount')),
    )

    # --- Deductions ---
    ded_qs = Deduction.objects.filter(
        cooperative_id=cooperative_id,
        cycle__in=cycle_qs.values('id'),
    )
    deductions_by_type = dict(
        ded_qs.values('deduction_type')
        .annotate(total=coalesce_sum(Sum('amount')))
        .values_list('deduction_type', 'total')
    )

    # --- Loans ---
    loan_qs = Loan.objects.filter(cooperative_id=cooperative_id)
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
        (loan_agg['defaulted_count'] / total_loans * 100) if total_loans else 0, 1
    )
    repayment_count = loan_agg['completed_count'] + loan_agg['active_count']
    loan_agg['repayment_rate_pct'] = round(
        (loan_agg['completed_count'] / repayment_count * 100) if repayment_count else 0, 1
    )

    # --- Disbursements ---
    batch_qs = DisbursementBatch.objects.filter(
        cooperative_id=cooperative_id,
        created_at__gte=start_date,
        created_at__lt=end_date,
    )
    batches_by_status = dict(
        batch_qs.values('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    disb_agg = batch_qs.aggregate(
        total_disbursed=coalesce_sum(Sum('total_amount')),
        total_transactions=coalesce_sum(
            Sum('total_transactions'), output_field=IntegerField(),
        ),
    )
    successful = batch_qs.aggregate(
        s=coalesce_sum(Sum('successful_count'), output_field=IntegerField()),
    )['s']
    failed = batch_qs.aggregate(
        f=coalesce_sum(Sum('failed_count'), output_field=IntegerField()),
    )['f']
    total_txns = disb_agg['total_transactions']
    disb_agg['success_rate_pct'] = round(
        (successful / total_txns * 100) if total_txns else 0, 1
    )

    # --- Inventory ---
    inv_qs = Inventory.objects.filter(cooperative_id=cooperative_id)
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
            'by_buyer': {k: float(v) for k, v in sales_by_buyer.items()},
            'price_trend': price_summary,
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
