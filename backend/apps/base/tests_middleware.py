import json
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, JsonResponse
from django.test import override_settings

from apps.base.middleware import (
    CorrelationIDMiddleware,
    ForcePasswordChangeMiddleware,
    LegalAcceptanceMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TenantMiddleware,
)
from apps.base.constants import UserRole
from apps.auth_api.models import User
from apps.conftest import (
    CooperativeFactory,
    FarmerFactory,
    FarmerCooperativeMembershipFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


def make_request(path='/api/test/', user=None, method='GET', headers=None):
    from django.test import RequestFactory
    factory = RequestFactory()
    request = getattr(factory, method.lower())(path)
    request.user = user or AnonymousUser()
    if headers:
        for key, value in headers.items():
            request.META[f'HTTP_{key.upper().replace("-", "_")}'] = value
    return request


def simple_view(request):
    return JsonResponse({'ok': True})


def simple_http_view(request):
    return HttpResponse('ok', content_type='text/plain')


def make_farmer_user(coop):
    user = UserFactory(role=UserRole.FARMER, cooperative=coop, is_superuser=False, is_staff=False)
    farmer = FarmerFactory(cooperative=coop, user=user)
    return user, farmer


# =============================================================================
# CorrelationIDMiddleware
# =============================================================================


class TestCorrelationIDMiddleware:
    def test_generates_uuid_when_no_header(self):
        request = make_request()
        mw = CorrelationIDMiddleware(simple_view)
        mw(request)
        assert hasattr(request, 'correlation_id')
        assert len(request.correlation_id) == 36

    def test_uses_existing_header(self):
        request = make_request(headers={'X-Correlation-ID': 'my-trace-id'})
        mw = CorrelationIDMiddleware(simple_view)
        mw(request)
        assert request.correlation_id == 'my-trace-id'

    def test_passes_response_through(self):
        request = make_request()
        mw = CorrelationIDMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200


# =============================================================================
# SecurityHeadersMiddleware
# =============================================================================


class TestSecurityHeadersMiddleware:
    @override_settings(CONTENT_SECURITY_POLICY="default-src 'self'")
    def test_adds_csp_header(self):
        request = make_request()
        mw = SecurityHeadersMiddleware(lambda r: simple_http_view(r))
        mw_get_response = mw.get_response

        def patched_view(request):
            resp = simple_http_view(request)
            resp._headers = dict(resp.items())
            return resp

        mw2 = SecurityHeadersMiddleware(patched_view)
        response = mw2(request)
        assert response.get('Content-Security-Policy') == "default-src 'self'"

    @override_settings(PERMISSIONS_POLICY="geolocation=()")
    def test_adds_permissions_policy(self):
        request = make_request()

        def patched_view(request):
            resp = simple_http_view(request)
            resp._headers = dict(resp.items())
            return resp

        mw = SecurityHeadersMiddleware(patched_view)
        response = mw(request)
        assert response.get('Permissions-Policy') == "geolocation=()"

    @override_settings(CONTENT_SECURITY_POLICY=None, PERMISSIONS_POLICY=None)
    def test_no_headers_when_not_configured(self):
        request = make_request()
        mw = SecurityHeadersMiddleware(simple_http_view)
        response = mw(request)
        assert 'Content-Security-Policy' not in response
        assert 'Permissions-Policy' not in response

    def test_passes_response_through(self):
        request = make_request()
        mw = SecurityHeadersMiddleware(simple_http_view)
        response = mw(request)
        assert response.status_code == 200


# =============================================================================
# TenantMiddleware
# =============================================================================


class TestTenantMiddleware:
    def test_unauthenticated_user_gets_none(self):
        request = make_request()
        mw = TenantMiddleware(simple_view)
        mw(request)
        assert request.cooperative_id is None

    def test_admin_user_gets_own_cooperative(self):
        coop = CooperativeFactory()
        user = UserFactory(role=UserRole.ADMIN, cooperative=coop)
        request = make_request(user=user)
        mw = TenantMiddleware(simple_view)
        mw(request)
        assert request.cooperative_id == coop.id

    def test_farmer_with_single_membership(self):
        coop = CooperativeFactory()
        user, farmer = make_farmer_user(coop)
        request = make_request(user=user)
        mw = TenantMiddleware(simple_view)
        mw(request)
        assert request.cooperative_id == coop.id

    def test_farmer_with_header_cooperative(self):
        coop = CooperativeFactory()
        user, farmer = make_farmer_user(coop)
        request = make_request(
            user=user,
            headers={'X-Cooperative-ID': str(coop.id)},
        )
        mw = TenantMiddleware(simple_view)
        mw(request)
        assert str(request.cooperative_id) == str(coop.id)

    def test_farmer_with_invalid_header_falls_back(self):
        coop = CooperativeFactory()
        user, farmer = make_farmer_user(coop)
        fake_coop_id = str(uuid.uuid4())
        request = make_request(
            user=user,
            headers={'X-Cooperative-ID': fake_coop_id},
        )
        mw = TenantMiddleware(simple_view)
        mw(request)
        assert request.cooperative_id == coop.id


# =============================================================================
# ForcePasswordChangeMiddleware
# =============================================================================


class TestForcePasswordChangeMiddleware:
    def test_blocks_user_with_must_change_password(self):
        user = UserFactory(role=UserRole.ADMIN, must_change_password=True)
        request = make_request(user=user)
        mw = ForcePasswordChangeMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 403
        data = json.loads(response.content)
        assert data['must_change_password'] is True

    def test_passes_user_without_must_change_password(self):
        user = UserFactory(role=UserRole.ADMIN, must_change_password=False)
        request = make_request(user=user)
        mw = ForcePasswordChangeMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_allows_change_password_endpoint(self):
        user = UserFactory(role=UserRole.ADMIN, must_change_password=True)
        request = make_request(path='/api/auth/change-password/', user=user)
        mw = ForcePasswordChangeMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_allows_logout_endpoint(self):
        user = UserFactory(role=UserRole.ADMIN, must_change_password=True)
        request = make_request(path='/api/auth/logout/', user=user)
        mw = ForcePasswordChangeMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_allows_health_endpoint(self):
        user = UserFactory(role=UserRole.ADMIN, must_change_password=True)
        request = make_request(path='/api/health/', user=user)
        mw = ForcePasswordChangeMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_unauthenticated_user_passes_through(self):
        request = make_request()
        mw = ForcePasswordChangeMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200


# =============================================================================
# LegalAcceptanceMiddleware
# =============================================================================


class TestLegalAcceptanceMiddleware:
    def test_unauthenticated_user_passes_through(self):
        request = make_request()
        mw = LegalAcceptanceMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_admin_user_passes_through(self):
        user = UserFactory(role=UserRole.ADMIN)
        request = make_request(user=user)
        mw = LegalAcceptanceMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_allows_legal_endpoint(self):
        user = UserFactory(role=UserRole.MANAGER)
        request = make_request(path='/api/legal/terms/', user=user)
        mw = LegalAcceptanceMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    def test_allows_auth_endpoint(self):
        user = UserFactory(role=UserRole.MANAGER)
        request = make_request(path='/api/auth/login/', user=user)
        mw = LegalAcceptanceMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200

    @patch('apps.legal.models.LegalAcceptance')
    @patch('apps.legal.models.LegalDocument')
    def test_blocks_user_with_pending_legal_docs(self, MockDocument, MockAcceptance):
        user = UserFactory(role=UserRole.MANAGER)
        request = make_request(user=user)

        MockDocument.objects.filter.return_value.values_list.return_value = [uuid.uuid4()]
        MockAcceptance.objects.filter.return_value.count.return_value = 0

        mw = LegalAcceptanceMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 403
        data = json.loads(response.content)
        assert data['requires_legal_acceptance'] is True

    @patch('apps.legal.models.LegalAcceptance')
    @patch('apps.legal.models.LegalDocument')
    def test_passes_user_with_all_legal_docs_accepted(self, MockDocument, MockAcceptance):
        user = UserFactory(role=UserRole.MANAGER)
        request = make_request(user=user)

        MockDocument.objects.filter.return_value.values_list.return_value = [uuid.uuid4()]
        MockAcceptance.objects.filter.return_value.count.return_value = 1

        mw = LegalAcceptanceMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200


# =============================================================================
# RequestLoggingMiddleware
# =============================================================================


class TestRequestLoggingMiddleware:
    @patch('apps.base.middleware.logger')
    def test_logs_request_and_response(self, mock_logger):
        request = make_request()
        mw = RequestLoggingMiddleware(simple_view)
        response = mw(request)
        assert response.status_code == 200
        assert mock_logger.info.call_count >= 2

    @patch('apps.base.middleware.logger')
    def test_includes_correlation_id_in_logs(self, mock_logger):
        request = make_request()
        request.correlation_id = 'test-corr-id'
        mw = RequestLoggingMiddleware(simple_view)
        mw(request)
        log_args = str(mock_logger.info.call_args_list)
        assert 'test-corr-id' in log_args

    @patch('apps.base.middleware.logger')
    def test_logs_exception(self, mock_logger):
        def error_view(request):
            raise ValueError('test error')

        request = make_request()
        mw = RequestLoggingMiddleware(error_view)
        with pytest.raises(ValueError, match='test error'):
            mw(request)
        assert mock_logger.exception.called
