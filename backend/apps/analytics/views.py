import logging

from django.utils.timezone import now

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.base.constants import UserRole
from apps.base.permissions import IsManager, IsAccountantOrManager

from .cache import (
    get_cached_analytics,
    record_access,
    set_cached_analytics,
)
from .queries.common import get_role_scope, parse_period
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
from .serializers import AnalyticsQuerySerializer, AnalyticsResponseSerializer
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
    - Admin: sees app-wide (cross-cooperative) analytics
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
        else:
            def compute(s, p):
                return coop_fn(
                    cooperative_id=s.get('cooperative_id'),
                    start_date=p['start_date'],
                    end_date=p['end_date'],
                    compare_to=p.get('compare_to'),
                )
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
        return Response({'detail': 'Not implemented yet'}, status=501)

    @action(detail=False, methods=['get'])
    def export(self, request):
        return Response({'detail': 'Not implemented yet'}, status=501)
