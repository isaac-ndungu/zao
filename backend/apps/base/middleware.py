import uuid
import logging

from django.conf import settings
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.utils import timezone

from apps.farmers.models import Farmer


logger = logging.getLogger(__name__)


class CorrelationIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID') or str(uuid.uuid4())
        request.correlation_id = correlation_id
        with context_log(correlation_id=correlation_id):
            return self.get_response(request)


class context_log:
    """Temporary context to attach correlation ID to log records.

    Usage:
        with context_log(correlation_id='...'):
            logger.info('message')

    Logging formatter reads ``correlation_id`` from the record's
    ``__context__`` dict (set by the adapter below).
    """

    _contexts: list[dict] = []

    def __init__(self, **kwargs):
        self._data = kwargs

    def __enter__(self):
        self.__class__._contexts.append(self._data)
        return self

    def __exit__(self, *args):
        self.__class__._contexts.pop()


class ContextAdapter(logging.LoggerAdapter):
    """Adapter that injects correlation ID context into every log call."""

    def process(self, msg, kwargs):
        ctx = {}
        if context_log._contexts:
            ctx.update(context_log._contexts[-1])
        kwargs['extra'] = {**(kwargs.get('extra') or {}), '__context__': ctx}
        return msg, kwargs


def get_logger(name=None):
    return ContextAdapter(logging.getLogger(name), {})


class RequestLoggingMiddleware:
    """Logs every API request with method, path, status, duration, and correlation ID."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = getattr(request, 'correlation_id', '')
        start = timezone.now()
        with context_log(correlation_id=correlation_id):
            logger.info(
                'Request: method=%s path=%s correlation_id=%s',
                request.method, request.get_full_path_info(), correlation_id,
            )
            try:
                response = self.get_response(request)
            except Exception as exc:
                duration = (timezone.now() - start).total_seconds()
                logger.exception(
                    'Unhandled exception: method=%s path=%s duration=%s correlation_id=%s',
                    request.method, request.get_full_path_info(), duration, correlation_id,
                )
                raise
        duration = (timezone.now() - start).total_seconds()
        logger.info(
            'Response: method=%s path=%s status=%s duration=%s correlation_id=%s',
            request.method, request.get_full_path_info(),
            response.status_code, duration, correlation_id,
        )
        return response


class SecurityHeadersMiddleware:
    """Adds Content-Security-Policy and Permissions-Policy to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not hasattr(response, '_headers'):
            return response
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', None)
        if csp:
            response['Content-Security-Policy'] = csp
        permissions = getattr(settings, 'PERMISSIONS_POLICY', None)
        if permissions:
            response['Permissions-Policy'] = permissions
        return response


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user_role = getattr(request.user, 'role', None)
            if user_role == 'farmer':
                coop_id = request.META.get('HTTP_X_COOPERATIVE_ID', '')
                if coop_id:
                    farmer = getattr(request.user, 'farmer_profile', None)
                    if farmer and farmer.memberships.filter(
                        cooperative_id=coop_id, is_active=True
                    ).exists():
                        request.cooperative_id = coop_id
                    else:
                        request.cooperative_id = getattr(request.user, 'cooperative_id', None)
                else:
                    farmer = getattr(request.user, 'farmer_profile', None)
                    if farmer:
                        active_memberships = list(
                            farmer.memberships.filter(is_active=True)
                        )
                        if len(active_memberships) == 1:
                            request.cooperative_id = active_memberships[0].cooperative_id
                        else:
                            request.cooperative_id = getattr(request.user, 'cooperative_id', None)
                    else:
                        request.cooperative_id = getattr(request.user, 'cooperative_id', None)
            else:
                request.cooperative_id = getattr(request.user, 'cooperative_id', None)
        else:
            request.cooperative_id = None
        return self.get_response(request)


class LegalAcceptanceMiddleware:
    """Block authenticated users who haven't accepted required legal documents.

    Must be placed after AuthenticationMiddleware. Skips legal endpoints,
    admin endpoints, and authentication endpoints to avoid lockout loops.
    """

    SAFE_PATHS = {
        '/api/legal/',
        '/api/admin/',
        '/api/auth/',
        '/api/health/',
        '/api/schema/',
        '/api/docs/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.role == 'admin':
                return self.get_response(request)
            path = request.path_info
            if not any(path.startswith(p) for p in self.SAFE_PATHS):
                from apps.legal.models import LegalDocument, LegalAcceptance

                # Phase 2 simplification: with the partial UniqueConstraint
                # in place, at most one active row exists per slug, so
                # ``document=OuterRef('pk')`` is sufficient to mark a doc as
                # accepted for this user. (Previously, ``version=OuterRef(
                # 'version')`` caused users to be re-prompted for v1 after
                # v2 was published even though v2 implies v1 acceptance.)
                has_pending = LegalDocument.objects.filter(
                    is_active=True,
                    requires_acceptance=True,
                    published_at__lte=timezone.now(),
                ).annotate(
                    has_accepted=Exists(
                        LegalAcceptance.objects.filter(
                            user=request.user,
                            document=OuterRef('pk'),
                        )
                    ),
                ).filter(has_accepted=False).exists()

                if has_pending:
                    return JsonResponse(
                        {'requires_legal_acceptance': True},
                        status=403,
                    )
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """Block authenticated users who have must_change_password=True.

    Returns 403 with {"must_change_password": true} on every authenticated
    API request until the user changes their password via the change-password
    endpoint. Frontend-only gates are insufficient because API clients can
    bypass them.

    Must be placed after AuthenticationMiddleware and TenantMiddleware.
    """

    SAFE_PATHS = {
        '/api/auth/change-password/',
        '/api/auth/logout/',
        '/api/auth/refresh/',
        '/api/health/',
        '/api/schema/',
        '/api/docs/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'must_change_password', False)
        ):
            path = request.path_info
            if not any(path.startswith(p) for p in self.SAFE_PATHS):
                return JsonResponse(
                    {
                        'must_change_password': True,
                        'detail': 'You must change your password before continuing.',
                    },
                    status=403,
                )
        return self.get_response(request)
