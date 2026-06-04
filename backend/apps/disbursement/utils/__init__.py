import re
from datetime import date, datetime, time, timedelta, timezone as dt_timezone

from django.conf import settings
from django.db.models import Sum

from apps.payment_engine.models import FarmerPayment


EAT = dt_timezone(timedelta(hours=3))
KENYA_PHONE_RE = re.compile(r'^(?:\+?254|0)?([17]\d{8})$')


def normalize_mpesa_number(phone: str) -> str:
    phone = phone.strip().replace(' ', '')
    match = KENYA_PHONE_RE.match(phone)
    if not match:
        raise ValueError(f'Invalid Kenyan phone number: {phone}')
    return f'254{match.group(1)}'


def validate_disbursement_window() -> None:
    now = datetime.now(EAT).time()
    start_str = settings.MPESA_DISBURSEMENT_BLACKOUT_START
    end_str = settings.MPESA_DISBURSEMENT_BLACKOUT_END
    try:
        start = time.fromisoformat(start_str)
        end = time.fromisoformat(end_str)
    except (ValueError, TypeError):
        start = time(1, 0)
        end = time(4, 0)

    if start <= end:
        in_blackout = start <= now <= end
    else:
        in_blackout = now >= start or now <= end

    if in_blackout:
        raise RuntimeError(
            f'M-Pesa disbursements are unavailable between {start_str} '
            f'and {end_str} EAT. Please initiate after {end_str}.'
        )


def compute_withholding_tax(farmer_id: str, cycle_id: str) -> tuple:
    today = date.today()
    fy_start = date(today.year, 7, 1)
    if today < fy_start:
        fy_start = date(today.year - 1, 7, 1)
    fy_end = date(fy_start.year + 1, 6, 30)

    cumulative = FarmerPayment.objects.filter(
        farmer_id=farmer_id,
        cycle__status='DISBURSED',
        cycle__end_date__gte=fy_start,
        cycle__end_date__lte=fy_end,
    ).exclude(cycle_id=cycle_id).aggregate(
        total=Sum('net_amount'),
    )['total'] or 0
    cumulative = float(cumulative)

    current_net = FarmerPayment.objects.filter(
        farmer_id=farmer_id, cycle_id=cycle_id,
    ).values_list('net_amount', flat=True).first() or 0
    current_net = float(current_net)

    threshold = 24000.0

    if cumulative < threshold:
        amount_above = max((cumulative + current_net) - threshold, 0)
        capped = min(amount_above, current_net)
        tax = round(capped * 0.05, 2)
    else:
        tax = round(current_net * 0.05, 2)

    return tax, tax > 0


def compute_withholding_taxes(farmer_ids, cycle):
    """Batch withholding tax for all farmers in two queries total."""
    today = date.today()
    fy_start = date(today.year, 7, 1)
    if today < fy_start:
        fy_start = date(today.year - 1, 7, 1)
    fy_end = date(fy_start.year + 1, 6, 30)

    current = dict(
        FarmerPayment.objects.filter(
            cycle=cycle, farmer_id__in=farmer_ids,
        ).values_list('farmer_id', 'net_amount')
    )

    cumulative = dict(
        FarmerPayment.objects.filter(
            farmer_id__in=farmer_ids,
            cycle__status='DISBURSED',
            cycle__end_date__gte=fy_start,
            cycle__end_date__lte=fy_end,
        ).exclude(cycle=cycle).values('farmer_id').annotate(
            total=Sum('net_amount'),
        ).values_list('farmer_id', 'total')
    )

    threshold = 24000.0
    result = {}
    for fid in farmer_ids:
        cum = float(cumulative.get(fid, 0) or 0)
        net = float(current.get(fid, 0) or 0)
        if cum < threshold:
            above = max((cum + net) - threshold, 0)
            capped = min(above, net)
            tax = round(capped * 0.05, 2)
        else:
            tax = round(net * 0.05, 2)
        result[fid] = (tax, tax > 0)
    return result
