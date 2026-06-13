import hashlib
import json
import logging
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL = getattr(settings, 'IDEMPOTENCY_TTL', 86400)  # 24 hours


def idempotent(timeout=IDEMPOTENCY_TTL):
    """Decorator that enforces idempotency via an ``Idempotency-Key`` header.

    Usage::

        @idempotent()
        def post(self, request, *args, **kwargs):
            ...

    The decorator:

    1. Reads ``Idempotency-Key`` from the request headers.
    2. Computes a cache key from the idempotency key + request path.
    3. If a cached response exists for that key, returns it directly
       (avoids duplicate processing).
    4. Otherwise calls the original handler and caches its response
       for ``timeout`` seconds.

    Only ``POST``, ``PUT``, ``PATCH``, and ``DELETE`` methods are
    intercepted — safe methods (``GET``, ``HEAD``, ``OPTIONS``) pass
    through unchanged.

    The cached response stores status code, headers, and body so the
    caller receives the identical result on retry.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                return view_func(self, request, *args, **kwargs)

            idem_key = request.META.get('HTTP_IDEMPOTENCY_KEY') or ''
            if not idem_key:
                return view_func(self, request, *args, **kwargs)

            cache_key = _make_cache_key(request, idem_key)
            cached = cache.get(cache_key)
            if cached is not None:
                logger.info(
                    'Idempotency hit: key=%s method=%s path=%s',
                    idem_key, request.method, request.path,
                )
                return _build_cached_response(cached)

            response = view_func(self, request, *args, **kwargs)

            _cache_response(cache_key, response, timeout)

            return response
        return wrapper
    return decorator


def _make_cache_key(request, idem_key):
    raw = f'{request.method}:{request.path}:{idem_key}'
    return f'idem:{hashlib.sha256(raw.encode()).hexdigest()}'


def _cache_response(cache_key, response, timeout):
    try:
        body = response.rendered_content if hasattr(response, 'rendered_content') else response.content
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        cache.set(cache_key, {
            'status': response.status_code,
            'headers': dict(response.items()),
            'body': body,
        }, timeout)
    except Exception as exc:
        logger.warning('Idempotency cache write failed: %s', exc)


def _build_cached_response(cached):
    resp = JsonResponse(
        json.loads(cached['body']),
        status=cached['status'],
    )
    for key, value in cached.get('headers', {}).items():
        resp[key] = value
    return resp
