from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from weasyprint import HTML

from apps.base.utils import log_audit
from apps.cooperatives.models import Cooperative
from apps.deliveries.models import Delivery
from apps.farmers.models import Farmer
from apps.payment_engine.models import FarmerPayment, PaymentCycle


def generate_farmer_statement(farmer_payment_id, cooperative_id, request_user):
    fp = get_object_or_404(
        FarmerPayment.objects.select_related(
            'farmer', 'cycle', 'cycle__cooperative',
        ),
        id=farmer_payment_id,
        cooperative_id=cooperative_id,
    )

    role = getattr(request_user, 'role', None)
    if role == 'farmer':
        if getattr(fp.farmer, 'user_id', None) != request_user.id:
            return None, None, 'You can only view your own statement.'

    deliveries = Delivery.objects.filter(
        farmer=fp.farmer,
        date_delivered__date__gte=fp.cycle.start_date,
        date_delivered__date__lte=fp.cycle.end_date,
    ).select_related('grader').order_by('date_delivered')

    deductions = {}
    if fp.deductions and isinstance(fp.deductions, dict):
        deductions = {
            k: v for k, v in fp.deductions.items()
            if v is not None and (isinstance(v, Decimal) or isinstance(v, (int, float)))
        }
    has_deductions = bool(deductions)

    context = {
        'cooperative': fp.cycle.cooperative,
        'farmer': fp.farmer,
        'cycle': fp.cycle,
        'payment': fp,
        'deliveries': deliveries,
        'deductions': deductions,
        'has_deductions': has_deductions,
        'generated_at': timezone.now(),
    }

    html = render_to_string('statements/farmer_statement.html', context)
    pdf = HTML(string=html).write_pdf()

    member = slugify(fp.farmer.member_number)
    cycle_name = slugify(fp.cycle.name)
    filename = f'coopchain_statement_{member}_{cycle_name}.pdf'

    log_audit(
        actor=request_user,
        resource_type='FarmerPayment',
        resource_id=fp.id,
        action='PDF_GENERATED',
        new_value={'type': 'farmer_statement', 'filename': filename},
        cooperative_id=cooperative_id,
        ip_address=getattr(request_user, '_ip_address', None),
    )

    return pdf, filename, None


def generate_season_report(cycle_id, cooperative_id, request_user):
    cycle = get_object_or_404(
        PaymentCycle.objects.select_related('cooperative'),
        id=cycle_id,
        cooperative_id=cooperative_id,
    )

    farmer_count = FarmerPayment.objects.filter(cycle=cycle).count()
    if farmer_count > 200:
        return None, None, (
            'Season report generation is not supported for cooperatives '
            'with over 200 farmers in this version. Please contact support.'
        )

    payments = FarmerPayment.objects.filter(
        cycle=cycle,
    ).select_related('farmer').order_by('farmer__member_number')

    totals = payments.aggregate(
        total_farmers=Count('id'),
        total_quantity=Sum('total_quantity'),
        total_gross=Sum('gross_amount'),
        total_net=Sum('net_amount'),
    )

    context = {
        'cooperative': cycle.cooperative,
        'cycle': cycle,
        'payments': payments,
        'totals': totals,
        'farmer_count': farmer_count,
        'generated_at': timezone.now(),
    }

    html = render_to_string('statements/season_report.html', context)
    pdf = HTML(string=html).write_pdf()

    coop_slug = slugify(cycle.cooperative.name)[:8]
    cycle_slug = slugify(cycle.name)
    filename = f'coopchain_season_report_{coop_slug}_{cycle_slug}.pdf'

    log_audit(
        actor=request_user,
        resource_type='PaymentCycle',
        resource_id=cycle.id,
        action='PDF_GENERATED',
        new_value={'type': 'season_report', 'filename': filename, 'farmer_count': farmer_count},
        cooperative_id=cooperative_id,
        ip_address=getattr(request_user, '_ip_address', None),
    )

    return pdf, filename, None


def generate_kra_report(year, cooperative_id, request_user):
    cooperative = get_object_or_404(Cooperative, id=cooperative_id)

    farmers_data = (
        FarmerPayment.objects
        .filter(
            cooperative_id=cooperative_id,
            cycle__end_date__year=year,
        )
        .values(
            'farmer_id',
            'farmer__member_number',
            'farmer__first_name',
            'farmer__last_name',
            'farmer__id_number',
        )
        .annotate(
            gross_amount=Sum('gross_amount'),
            withholding_tax_amount=Sum('withholding_tax_amount'),
            net_amount=Sum('net_amount'),
        )
        .order_by('farmer__member_number')
    )

    farmers = [
        {
            'member_number': f['farmer__member_number'],
            'farmer_name': f'{f["farmer__first_name"]} {f["farmer__last_name"]}',
            'id_number': f['farmer__id_number'],
            'gross_amount': float(f['gross_amount'] or 0),
            'withholding_tax_amount': float(f['withholding_tax_amount'] or 0),
            'net_amount': float(f['net_amount'] or 0),
        }
        for f in farmers_data
    ]

    totals = FarmerPayment.objects.filter(
        cooperative_id=cooperative_id,
        cycle__end_date__year=year,
    ).aggregate(
        gross_amount=Sum('gross_amount'),
        withholding_tax_amount=Sum('withholding_tax_amount'),
        net_amount=Sum('net_amount'),
    )

    context = {
        'cooperative': cooperative,
        'year': year,
        'farmers': farmers,
        'farmer_count': len(farmers),
        'totals': {
            'gross_amount': float(totals['gross_amount'] or 0),
            'withholding_tax_amount': float(totals['withholding_tax_amount'] or 0),
            'net_amount': float(totals['net_amount'] or 0),
        },
        'generated_at': timezone.now(),
        'generated_by': request_user.get_full_name() or request_user.email,
    }

    html = render_to_string('statements/kra_report.html', context)
    pdf = HTML(string=html).write_pdf()

    coop_slug = slugify(cooperative.name)[:8]
    filename = f'coopchain_kra_report_{coop_slug}_{year}.pdf'

    log_audit(
        actor=request_user,
        resource_type='Cooperative',
        resource_id=cooperative.id,
        action='PDF_GENERATED',
        new_value={'type': 'kra_report', 'year': year, 'filename': filename, 'farmer_count': len(farmers)},
        cooperative_id=cooperative_id,
        ip_address=getattr(request_user, '_ip_address', None),
    )

    return pdf, filename, None
