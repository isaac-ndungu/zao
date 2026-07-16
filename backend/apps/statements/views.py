from datetime import date

from django.db.models import Count, Sum
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.base.export_mixins import CsvExportMixin
from apps.base.models import AuditLog
from apps.base.permissions import IsAccountantOrManager, IsFarmer, IsManagerOrAuditor, IsAnyAuditor, IsExternalAuditor
from apps.deductions.models import Deduction
from apps.deliveries.models import Delivery
from apps.farmers.models import Farmer
from apps.payment_engine.models import FarmerPayment, PaymentCycle
from apps.sales.models import Sale

from .pdf_utils import generate_farmer_statement, generate_kra_report, generate_season_report
from .serializers import AuditLogSerializer


def _pdf_response(pdf, filename, download):
    disposition = 'attachment' if download else 'inline'
    return HttpResponse(
        pdf,
        content_type='application/pdf',
        headers={
            'Content-Disposition': f'{disposition}; filename="{filename}"',
            'Content-Length': str(len(pdf)),
        },
    )


class StatementPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get(self, request):
        farmer_payment_id = request.query_params.get('farmer_payment_id')
        if not farmer_payment_id:
            return Response(
                {'error': 'farmer_payment_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = getattr(request.user, 'role', None)
        cooperative_id = getattr(request, 'cooperative_id', None)

        if role == 'admin':
            cooperative_id = None

        if cooperative_id:
            pdf, filename, error = generate_farmer_statement(
                farmer_payment_id, cooperative_id, request.user,
            )
        else:
            fp = FarmerPayment.objects.filter(id=farmer_payment_id).first()
            if not fp:
                return Response(
                    {'error': 'FarmerPayment not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            pdf, filename, error = generate_farmer_statement(
                farmer_payment_id, fp.cooperative_id, request.user,
            )

        if error:
            if 'own statement' in error:
                return Response({'error': error}, status=status.HTTP_403_FORBIDDEN)
            return Response({'error': error}, status=status.HTTP_404_NOT_FOUND)

        download = request.query_params.get('download', '').lower() == 'true'
        return _pdf_response(pdf, filename, download)


class LatestStatementPDFView(APIView):
    permission_classes = [IsAuthenticated, IsFarmer]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get(self, request):
        farmer = Farmer.objects.filter(user=request.user).first()
        if not farmer:
            return Response(
                {'error': 'No farmer profile found for your account.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        fp = FarmerPayment.objects.filter(
            farmer=farmer, payment_status='PAID',
        ).select_related('farmer', 'cycle').order_by('-cycle__end_date').first()
        if not fp:
            return Response(
                {'error': 'No completed payment statements found for your account.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        pdf, filename, error = generate_farmer_statement(
            str(fp.id), getattr(request, 'cooperative_id', None), request.user,
        )
        if error:
            return Response({'error': error}, status=status.HTTP_404_NOT_FOUND)

        download = request.query_params.get('download', '').lower() == 'true'
        return _pdf_response(pdf, filename, download)


class FarmerPaymentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get(self, request):
        farmer_id = request.query_params.get('farmer_id')
        if not farmer_id:
            return Response(
                {'error': 'farmer_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = getattr(request.user, 'role', None)
        cooperative_id = getattr(request, 'cooperative_id', None)

        farmer = Farmer.objects.filter(id=farmer_id).first()
        if not farmer:
            return Response(
                {'error': 'Farmer not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if role == 'farmer':
            if getattr(farmer, 'user_id', None) != request.user.id:
                return Response(
                    {'error': 'You can only view your own payment history.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif role != 'admin' and cooperative_id and farmer.cooperative_id != cooperative_id:
            return Response(
                {'error': 'Farmer not found in your cooperative.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        payments = FarmerPayment.objects.filter(
            farmer=farmer,
        ).select_related('cycle').order_by('-cycle__end_date').values(
            'id', 'cycle__name', 'cycle__start_date', 'cycle__end_date',
            'gross_amount', 'net_amount', 'payment_status',
        )

        return Response({
            'farmer_id': farmer_id,
            'farmer_name': f'{farmer.first_name} {farmer.last_name}',
            'member_number': farmer.primary_membership.member_number if farmer.primary_membership else '',
            'payments': [
                {
                    'farmer_payment_id': str(p['id']),
                    'cycle_name': p['cycle__name'],
                    'period_start': p['cycle__start_date'],
                    'period_end': p['cycle__end_date'],
                    'gross_amount': float(p['gross_amount'] or 0),
                    'net_amount': float(p['net_amount'] or 0),
                    'status': p['payment_status'],
                }
                for p in payments
            ],
        })


class SeasonReportPDFView(APIView):
    permission_classes = [IsAuthenticated, IsAccountantOrManager | IsAnyAuditor]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get(self, request):
        cycle_id = request.query_params.get('cycle_id')
        if not cycle_id:
            return Response(
                {'error': 'cycle_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cooperative_id = getattr(request, 'cooperative_id', None)
        role = getattr(request.user, 'role', None)
        if role == 'admin':
            cooperative_id = None

        pdf, filename, error = generate_season_report(
            cycle_id, cooperative_id, request.user,
        )

        if error:
            if 'over 200' in error:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': error}, status=status.HTTP_404_NOT_FOUND)

        download = request.query_params.get('download', '').lower() == 'true'
        return _pdf_response(pdf, filename, download)


class KRAReportPDFView(APIView):
    permission_classes = [IsAuthenticated, IsAccountantOrManager | IsAnyAuditor]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get(self, request):
        year = request.query_params.get('year')
        if not year:
            return Response(
                {'error': 'year query parameter is required (e.g. ?year=2026).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year)
            if year < 1900 or year > 2099:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'error': 'year must be a valid 4-digit year between 1900 and 2099.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cooperative_id = getattr(request, 'cooperative_id', None)
        role = getattr(request.user, 'role', None)
        if role == 'admin':
            cooperative_id = None

        pdf, filename, error = generate_kra_report(
            year, cooperative_id, request.user,
        )

        if error:
            return Response({'error': error}, status=status.HTTP_404_NOT_FOUND)

        download = request.query_params.get('download', '').lower() == 'true'
        return _pdf_response(pdf, filename, download)


class AnnualReportView(APIView):
    permission_classes = [IsAuthenticated, IsAccountantOrManager | IsAnyAuditor]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get(self, request):
        year = request.query_params.get('year')
        if not year:
            return Response(
                {'error': 'year query parameter is required (e.g. ?year=2026).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year)
            if year < 1900 or year > 2099:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'error': 'year must be a valid 4-digit year between 1900 and 2099.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cooperative_id = getattr(request, 'cooperative_id', None)
        role = getattr(request.user, 'role', None)
        if role == 'admin':
            cooperative_id = None

        fy_start = date(year, 7, 1)
        fy_end = date(year + 1, 6, 30)

        cycles = PaymentCycle.objects.filter(
            end_date__gte=fy_start,
            end_date__lte=fy_end,
        )
        if cooperative_id:
            cycles = cycles.filter(cooperative_id=cooperative_id)

        farmer_payments = FarmerPayment.objects.filter(
            cycle__in=cycles,
        ).select_related('farmer')

        deliveries_qs = Delivery.objects.filter(
            date_delivered__date__gte=fy_start,
            date_delivered__date__lte=fy_end,
        )
        if cooperative_id:
            deliveries_qs = deliveries_qs.filter(cooperative_id=cooperative_id)

        produce_by_type = deliveries_qs.values('product_type').annotate(
            total_kg=Sum('quantity_kg'),
            total_volume=Sum('volume_litres'),
            delivery_count=Count('id'),
        )

        sales_qs = Sale.objects.filter(
            status='COMPLETED',
            sale_date__gte=fy_start,
            sale_date__lte=fy_end,
        )
        if cooperative_id:
            sales_qs = sales_qs.filter(cooperative_id=cooperative_id)

        total_revenue = sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0

        payment_agg = farmer_payments.aggregate(
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_withholding_tax=Sum('withholding_tax_amount'),
        )

        deductions_qs = Deduction.objects.filter(cycle__in=cycles)
        if cooperative_id:
            deductions_qs = deductions_qs.filter(cooperative_id=cooperative_id)

        deductions_by_type = deductions_qs.values('deduction_type').annotate(
            total=Sum('amount'),
        )

        farmer_summaries_data = farmer_payments.values('farmer').annotate(
            total_quantity=Sum('total_quantity'),
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_withholding_tax=Sum('withholding_tax_amount'),
            payment_count=Count('id'),
        )

        farmer_ids = [fs['farmer'] for fs in farmer_summaries_data]
        farmers_map = {
            str(f.id): f for f in Farmer.objects.filter(id__in=farmer_ids)
        }

        farmer_summaries = []
        for fs in farmer_summaries_data:
            farmer = farmers_map.get(str(fs['farmer']))
            farmer_summaries.append({
                'farmer_id': str(fs['farmer']),
                'member_number': farmer.primary_membership.member_number if farmer and farmer.primary_membership else '',
                'farmer_name': f'{farmer.first_name} {farmer.last_name}' if farmer else 'Unknown',
                'total_quantity': float(fs['total_quantity'] or 0),
                'total_gross': float(fs['total_gross'] or 0),
                'total_deductions': float(
                    (fs['total_gross'] or 0) - (fs['total_net'] or 0)
                ),
                'total_net': float(fs['total_net'] or 0),
                'total_withholding_tax': float(fs['total_withholding_tax'] or 0),
                'payment_count': fs['payment_count'],
            })

        farmer_summaries.sort(key=lambda x: x['total_gross'], reverse=True)

        return Response({
            'financial_year': f'{year}/{year + 1}',
            'period': {
                'start': fy_start.isoformat(),
                'end': fy_end.isoformat(),
            },
            'summary': {
                'total_produce_received': {
                    p['product_type']: {
                        'total_kg': float(p['total_kg'] or 0),
                        'total_volume': float(p['total_volume'] or 0),
                        'delivery_count': p['delivery_count'],
                    }
                    for p in produce_by_type
                },
                'total_revenue': float(total_revenue),
                'total_farmer_payments': float(payment_agg['total_net'] or 0),
                'total_deductions_collected': {
                    d['deduction_type']: float(d['total'] or 0)
                    for d in deductions_by_type
                },
                'total_withholding_tax_held': float(payment_agg['total_withholding_tax'] or 0),
                'cycle_count': cycles.count(),
            },
            'farmer_summaries': farmer_summaries,
        })


@extend_schema(
    summary="Audit log",
    description="Read-only audit trail of all write operations. Filters by resource type, action, date range. Internal auditors and managers have access.",
    tags=["Statements"],
)
class AuditLogViewSet(CsvExportMixin, ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('actor', 'cooperative')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAuditor]
    csv_filename = 'audit_log.csv'
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'resource_type', 'action', 'actor__first_name', 'actor__last_name',
        'actor__email', 'resource_id',
    ]
    ordering_fields = ['created_at', 'action', 'resource_type']
    ordering = ['-created_at', '-id']

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_authenticated:
            request.cooperative_id = request.user.cooperative_id

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if user.is_authenticated and getattr(user, 'role', None) != 'admin':
            qs = qs.filter(cooperative_id=self.request.cooperative_id)
        resource_type = self.request.query_params.get('resource_type')
        action = self.request.query_params.get('action')
        resource_id = self.request.query_params.get('resource_id')
        action_category = self.request.query_params.get('action_category')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if action:
            qs = qs.filter(action=action)
        if resource_id:
            qs = qs.filter(resource_id=resource_id)
        if action_category == 'financial':
            qs = qs.filter(
                action__in=_FINANCIAL_ACTIONS,
                resource_type__in=_FINANCIAL_RESOURCE_TYPES,
            )
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        return qs


# Financial action constants used by the external auditor filter.
_FINANCIAL_ACTIONS = {
    'LOCK', 'UNLOCK', 'RUN', 'DISBURSE',
    'CREATE', 'UPDATE', 'DELETE',
}
_FINANCIAL_RESOURCE_TYPES = {
    'PaymentCycle', 'FarmerPayment', 'Deduction', 'Loan',
    'DisbursementBatch', 'DisbursementTransaction', 'Sale', 'FarmInputCredit',
}


@extend_schema(
    summary="External audit log",
    description="Read-only audit log restricted to financial actions (payment cycles, disbursements, deductions, loans). For external auditor access.",
    tags=["Statements"],
)
class ExternalAuditLogViewSet(AuditLogViewSet):
    """Read-only audit log restricted to financial actions only.

    Registered at a separate URL. External auditors only have access to this
    endpoint; internal auditors use the standard /audit/ URL. No conditionals
    inside the queryset — the filtering is always applied unconditionally.
    """

    permission_classes = [IsAuthenticated, IsExternalAuditor]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            action__in=_FINANCIAL_ACTIONS,
            resource_type__in=_FINANCIAL_RESOURCE_TYPES,
        )
