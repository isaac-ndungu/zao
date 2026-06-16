import csv
import hashlib
import io
import json
import logging
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import StreamingHttpResponse
from django.utils.timezone import now
from django.conf import settings
from django.core.cache import cache
import redis as redis_module

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.base.constants import UserRole
from apps.base.permissions import IsManager, IsAccountantOrManager
from apps.deliveries.models import Delivery
from apps.disbursement.models import DisbursementTransaction
from apps.loans.models import Loan
from apps.payment_engine.models import FarmerPayment
from apps.sales.models import Sale

from .cache import (
    get_cached_analytics,
    record_access,
    set_cached_analytics,
    hash_params,
)
from .queries.common import get_role_scope, parse_period, coalesce_sum
from .queries.cooperative import (
    get_dashboard as get_coop_dashboard,
    get_disbursements as get_coop_disbursements,
    get_farmers as get_coop_farmers,
    get_farmer_retention as get_coop_farmer_retention,
    get_financial as get_coop_financial,
    get_loans as get_coop_loans,
    get_operations as get_coop_operations,
    get_payment_efficiency as get_coop_payment_efficiency,
    get_production as get_coop_production,
    get_sales as get_coop_sales,
    get_seasonal as get_coop_seasonal,
)
from .queries.farmer import (
    get_farmer_financial,
    get_farmer_loans,
    get_farmer_production,
)
from .models import AnalyticsExportTask, ExportStatus
from .serializers import (
    AnalyticsQuerySerializer,
    AnalyticsResponseSerializer,
    ExportQuerySerializer,
    LeaderboardQuerySerializer,
)
from .throttles import (
    AnalyticsAdminThrottle,
    AnalyticsExportThrottle,
    AnalyticsFarmerThrottle,
    AnalyticsStaffThrottle,
)

logger = logging.getLogger(__name__)


class AnalyticsViewSet(ViewSet):
    """Role-scoped analytics endpoints.

    Three tiers:
    - Farmer: sees only own personal stats
    - Staff (manager/accountant/grader/auditor): sees cooperative-level
    - Admin: sees app-wide (cross-cooperative) analytics via /api/admin/analytics/
    """

    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return [AnalyticsAdminThrottle()]
        if user.role == UserRole.FARMER:
            return [AnalyticsFarmerThrottle()]
        return [AnalyticsStaffThrottle()]

    def get_permissions(self):
        if self.action in ('leaderboard', 'export'):
            return [IsAuthenticated(), IsAccountantOrManager()]
        return [IsAuthenticated()]

    def _get_scope(self):
        return get_role_scope(self.request.user)

    def _parse_params(self):
        serializer = AnalyticsQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        start, end = parse_period(
            params.get('start_date'), params.get('end_date'), params.get('period'),
        )
        return {
            'start_date': start,
            'end_date': end,
            'compare_to': params.get('compare_to'),
        }

    def _cached_response(self, action_name, params, compute_fn):
        scope = self._get_scope()
        record_access(scope.get('cooperative_id'))

        data, cache_key = get_cached_analytics(
            scope_type=scope.get('scope', 'none'),
            cooperative_id=scope.get('cooperative_id'),
            farmer_id=scope.get('farmer_id'),
            action=action_name,
            params=params,
        )
        if data is not None:
            return Response(data)

        result = compute_fn(scope, params)
        set_cached_analytics(cache_key, result)
        return Response(result)

    # --- Staff endpoints (farmers get 403) ---

    def _staff_only(self):
        scope = self._get_scope()
        if scope['scope'] == 'farmer':
            return Response(
                {'detail': 'Not available for farmers.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if scope['scope'] == 'global':
            return Response(
                {'detail': 'Use /api/admin/analytics/ for cross-cooperative analytics.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    # --- Actions ---

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Executive snapshot for the current scope."""
        params = self._parse_params()

        staff_block = self._staff_only()
        if staff_block:
            return staff_block

        def compute(scope, p):
            return get_coop_dashboard(
                cooperative_id=scope.get('cooperative_id'),
                start_date=p['start_date'],
                end_date=p['end_date'],
                compare_to=p.get('compare_to'),
            )

        return self._cached_response('dashboard', params, compute)

    def _coop_only(self, fn):
        """Helper that builds a compute closure for cooperative-scoped endpoints."""
        staff_block = self._staff_only()
        if staff_block:
            return staff_block

        params = self._parse_params()
        def compute(scope, p):
            return fn(
                cooperative_id=scope.get('cooperative_id'),
                start_date=p['start_date'],
                end_date=p['end_date'],
                compare_to=p.get('compare_to'),
            )
        return params, compute

    def _farmer_aware(self, coop_fn, farmer_fn):
        """Helper that picks farmer vs cooperative query based on user role."""
        params = self._parse_params()
        scope = self._get_scope()

        if scope['scope'] == 'farmer':
            def compute(s, p):
                return farmer_fn(
                    farmer_id=s['farmer_id'],
                    cooperative_id=s.get('cooperative_id'),
                    start_date=p['start_date'],
                    end_date=p['end_date'],
                    compare_to=p.get('compare_to'),
                )
        elif scope['scope'] in ('cooperative', 'global'):
            def compute(s, p):
                return coop_fn(
                    cooperative_id=s.get('cooperative_id'),
                    start_date=p['start_date'],
                    end_date=p['end_date'],
                    compare_to=p.get('compare_to'),
                )
        else:
            return None
        return params, compute

    @action(detail=False, methods=['get'])
    def production(self, request):
        params, compute = self._farmer_aware(get_coop_production, get_farmer_production)
        return self._cached_response('production', params, compute)

    @action(detail=False, methods=['get'])
    def financial(self, request):
        params, compute = self._farmer_aware(get_coop_financial, get_farmer_financial)
        return self._cached_response('financial', params, compute)

    @action(detail=False, methods=['get'])
    def farmers(self, request):
        r = self._coop_only(get_coop_farmers)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('farmers', params, compute)

    @action(detail=False, methods=['get'])
    def sales(self, request):
        r = self._coop_only(get_coop_sales)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('sales', params, compute)

    @action(detail=False, methods=['get'])
    def loans(self, request):
        params, compute = self._farmer_aware(get_coop_loans, get_farmer_loans)
        return self._cached_response('loans', params, compute)

    @action(detail=False, methods=['get'])
    def operations(self, request):
        r = self._coop_only(get_coop_operations)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('operations', params, compute)

    @action(detail=False, methods=['get'])
    def disbursements(self, request):
        r = self._coop_only(get_coop_disbursements)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('disbursements', params, compute)

    @action(detail=False, methods=['get'])
    def seasonal(self, request):
        r = self._coop_only(get_coop_seasonal)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('seasonal', params, compute)

    @action(detail=False, methods=['get'])
    def payment_efficiency(self, request):
        r = self._coop_only(get_coop_payment_efficiency)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('payment_efficiency', params, compute)

    @action(detail=False, methods=['get'])
    def farmer_retention(self, request):
        r = self._coop_only(get_coop_farmer_retention)
        if isinstance(r, Response):
            return r
        params, compute = r
        return self._cached_response('farmer_retention', params, compute)

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        serializer = LeaderboardQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        scope = self._get_scope()
        coop_id = scope.get('cooperative_id')

        _type = params.get('type', 'top_farmers_by_volume')
        limit = params.get('limit', 10)
        period = params.get('period', '30d')

        start, end = parse_period(period=period)
        period_label = period

        redis_key = f'leaderboard:{_type}:{coop_id or "global"}:{period_label}'

        redis_url = settings.CACHES['default']['LOCATION']
        rcon = redis_module.from_url(redis_url)
        raw = rcon.zrevrange(redis_key, 0, limit - 1, withscores=True)
        if raw:
            items = []
            for member, score in raw:
                items.append({'id': member, 'score': round(float(score), 2)})
            return Response({
                'type': _type,
                'limit': limit,
                'period': period_label,
                'data': items,
                'cached': True,
            })

        if _type == 'top_farmers_by_volume':
            qs = Delivery.objects.all()
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            qs = qs.filter(
                date_delivered__gte=start, date_delivered__lt=end,
            )
            agg = list(
                qs.values('farmer_id')
                .annotate(score=coalesce_sum(Sum('quantity_kg')))
                .order_by('-score')[:limit]
                .values_list('farmer_id', 'score')
            )
        elif _type == 'top_farmers_by_payout':
            qs = FarmerPayment.objects.all()
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            qs = qs.filter(
                cycle__end_date__gte=start, cycle__start_date__lt=end,
            )
            agg = list(
                qs.values('farmer_id')
                .annotate(score=coalesce_sum(Sum('net_amount')))
                .order_by('-score')[:limit]
                .values_list('farmer_id', 'score')
            )
        elif _type == 'top_buyers':
            qs = Sale.objects.filter(status='COMPLETED')
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            qs = qs.filter(
                sale_date__gte=start, sale_date__lt=end,
            )
            agg = list(
                qs.values('buyer__name')
                .annotate(score=coalesce_sum(Sum('total_amount')))
                .order_by('-score')[:limit]
                .values_list('buyer__name', 'score')
            )
        else:
            return Response({'detail': 'Invalid leaderboard type.'}, status=400)

        items = [{'id': str(member) if not isinstance(member, str) else member, 'score': round(float(score), 2)} for member, score in agg]

        mapping = {item['id']: item['score'] for item in items}
        if mapping:
            rcon.zadd(redis_key, mapping)
            rcon.expire(redis_key, 3600 * 2)

        return Response({
            'type': _type,
            'limit': limit,
            'period': period_label,
            'data': items,
        })

    @action(detail=False, methods=['get'])
    def export(self, request):
        task_id = request.query_params.get('task_id')
        if task_id:
            try:
                task = AnalyticsExportTask.objects.get(id=task_id)
            except AnalyticsExportTask.DoesNotExist:
                return Response({'detail': 'Export task not found.'}, status=404)
            return Response({
                'task_id': str(task.id),
                'status': task.status,
                'download_url': task.download_url or None,
                'error_message': task.error_message or None,
                'row_count': task.row_count,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            })

        serializer = ExportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        scope = self._get_scope()
        coop_id = scope.get('cooperative_id')

        export_type = params['type']
        export_format = params.get('format', 'csv')
        start, end = parse_period(
            params.get('start_date'), params.get('end_date'), params.get('period'),
        )

        count = self._estimate_export_rows(export_type, coop_id, start, end)

        if count <= 10000:
            return self._export_sync(export_type, coop_id, start, end, export_format)

        export_task = AnalyticsExportTask.objects.create(
            cooperative_id=coop_id,
            requested_by=request.user if request.user.is_authenticated else None,
            export_type=export_type,
            params={'format': export_format, 'start': start.isoformat(), 'end': end.isoformat()},
            status=ExportStatus.PENDING,
            row_count=count,
        )

        from .tasks import generate_export
        generate_export.delay(str(export_task.id))

        return Response({
            'task_id': str(export_task.id),
            'status': ExportStatus.PENDING,
            'row_count': count,
            'detail': 'Export queued. Poll with ?task_id=<id> for status.',
        }, status=status.HTTP_202_ACCEPTED)

    def _estimate_export_rows(self, export_type, coop_id, start, end):
        if export_type in ('dashboard',):
            return 1
        if export_type in ('production', 'operations'):
            qs = Delivery.objects.all()
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            return qs.filter(date_delivered__gte=start, date_delivered__lt=end).count()
        if export_type in ('financial',):
            qs = FarmerPayment.objects.all()
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            return qs.filter(cycle__end_date__gte=start, cycle__start_date__lt=end).count()
        if export_type in ('farmers',):
            return 0
        if export_type in ('sales',):
            qs = Sale.objects.filter(status='COMPLETED')
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            return qs.filter(sale_date__gte=start, sale_date__lt=end).count()
        if export_type in ('loans',):
            return Loan.objects.count() if not coop_id else Loan.objects.filter(cooperative_id=coop_id).count()
        if export_type in ('disbursements',):
            from apps.disbursement.models import DisbursementTransaction
            qs = DisbursementTransaction.objects.all()
            if coop_id:
                qs = qs.filter(cooperative_id=coop_id)
            return qs.filter(created_at__gte=start, created_at__lt=end).count()
        return 0

    def _flatten_row(self, prefix, value):
        rows = []
        if isinstance(value, dict):
            for k, v in value.items():
                rows.extend(self._flatten_row(f'{prefix}_{k}', v))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                rows.extend(self._flatten_row(f'{prefix}_{i}', v))
        else:
            rows.append((prefix, value))
        return rows

    def _dict_to_csv_rows(self, data):
        flat = dict(self._flatten_row('', data))
        return flat

    def _export_sync(self, export_type, coop_id, start, end, fmt):
        from .queries.cooperative import (
            get_production as get_coop_production,
            get_financial as get_coop_financial,
            get_farmers as get_coop_farmers,
            get_sales as get_coop_sales,
            get_loans as get_coop_loans,
            get_operations as get_coop_operations,
            get_disbursements as get_coop_disbursements,
        )

        query_map = {
            'production': get_coop_production,
            'financial': get_coop_financial,
            'farmers': get_coop_farmers,
            'sales': get_coop_sales,
            'loans': get_coop_loans,
            'operations': get_coop_operations,
            'disbursements': get_coop_disbursements,
        }

        fn = query_map.get(export_type)
        if fn is None:
            return Response({'detail': f'Export type "{export_type}" not supported.'}, status=400)

        data = fn(cooperative_id=coop_id, start_date=start, end_date=end)

        rows = [self._dict_to_csv_rows(data)]
        writer_rows = []
        if rows:
            fieldnames = rows[0].keys()
            writer_rows.append(fieldnames)
            for r in rows:
                writer_rows.append([r.get(f, '') for f in fieldnames])

        def stream():
            buffer = io.StringIO()
            w = csv.writer(buffer)
            for row in writer_rows:
                w.writerow(row)
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        response = StreamingHttpResponse(stream(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{export_type}_{start.isoformat()}_{end.isoformat()}.csv"'
        return response
