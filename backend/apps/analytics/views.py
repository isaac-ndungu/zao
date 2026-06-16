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
from .queries.cooperative import get_dashboard as get_coop_dashboard
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

    @action(detail=False, methods=['get'])
    def production(self, request):
        params = self._parse_params()
        return self._cached_response('production', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def financial(self, request):
        params = self._parse_params()
        return self._cached_response('financial', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def farmers(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('farmers', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def sales(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('sales', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def loans(self, request):
        params = self._parse_params()
        return self._cached_response('loans', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def operations(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('operations', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def disbursements(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('disbursements', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def seasonal(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('seasonal', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def payment_efficiency(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('payment_efficiency', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def farmer_retention(self, request):
        staff_block = self._staff_only()
        if staff_block:
            return staff_block
        params = self._parse_params()
        return self._cached_response('farmer_retention', params, lambda s, p: {})

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        return Response({'detail': 'Not implemented yet'}, status=501)

    @action(detail=False, methods=['get'])
    def export(self, request):
        return Response({'detail': 'Not implemented yet'}, status=501)
