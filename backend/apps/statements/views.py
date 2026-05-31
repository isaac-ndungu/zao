from django.http import HttpResponse
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.base.models import AuditLog
from apps.base.permissions import IsAccountantOrManager, IsFarmer, IsManagerOrAuditor
from apps.farmers.models import Farmer
from apps.payment_engine.models import FarmerPayment

from .pdf_utils import generate_farmer_statement, generate_season_report
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
            'member_number': farmer.member_number,
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
    permission_classes = [IsAuthenticated, IsAccountantOrManager]

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


class AuditLogViewSet(ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('actor', 'cooperative')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAuditor]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'resource_type', 'action', 'actor__first_name', 'actor__last_name',
        'actor__email', 'resource_id',
    ]
    ordering_fields = ['created_at', 'action', 'resource_type']
    ordering = ['-created_at']

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
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if action:
            qs = qs.filter(action=action)
        return qs
