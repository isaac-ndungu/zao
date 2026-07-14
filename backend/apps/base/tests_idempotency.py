import json
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase, override_settings

from apps.base.idempotency import (
    _build_cached_response,
    _cache_response,
    _make_cache_key,
    idempotent,
)


class TestMakeCacheKey:
    def test_deterministic(self):
        factory = RequestFactory()
        request = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='key-1')
        key1 = _make_cache_key(request, 'key-1')
        key2 = _make_cache_key(request, 'key-1')
        assert key1 == key2

    def test_different_methods_different_keys(self):
        factory = RequestFactory()
        post_req = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='key-1')
        put_req = factory.put('/api/test/', HTTP_IDEMPOTENCY_KEY='key-1')
        assert _make_cache_key(post_req, 'key-1') != _make_cache_key(put_req, 'key-1')

    def test_different_paths_different_keys(self):
        factory = RequestFactory()
        req1 = factory.post('/api/a/', HTTP_IDEMPOTENCY_KEY='key-1')
        req2 = factory.post('/api/b/', HTTP_IDEMPOTENCY_KEY='key-1')
        assert _make_cache_key(req1, 'key-1') != _make_cache_key(req2, 'key-1')

    def test_different_idem_keys_different_keys(self):
        factory = RequestFactory()
        req1 = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='key-1')
        req2 = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='key-2')
        assert _make_cache_key(req1, 'key-1') != _make_cache_key(req2, 'key-2')

    def test_starts_with_prefix(self):
        factory = RequestFactory()
        request = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='key-1')
        key = _make_cache_key(request, 'key-1')
        assert key.startswith('idem:')


class TestCacheResponse:
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_caches_json_response(self):
        response = JsonResponse({'ok': True}, status=201)
        _cache_response('test:cache:key', response, timeout=60)
        cached = cache.get('test:cache:key')
        assert cached is not None
        assert cached['status'] == 201
        assert json.loads(cached['body']) == {'ok': True}

    def test_caches_with_headers(self):
        response = HttpResponse('ok', status=200)
        response['X-Custom'] = 'value'
        _cache_response('test:cache:headers', response, timeout=60)
        cached = cache.get('test:cache:headers')
        assert cached is not None
        assert cached['headers'].get('X-Custom') == 'value'


class TestBuildCachedResponse:
    def test_builds_json_response(self):
        cached = {
            'status': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'id': '123'}),
        }
        response = _build_cached_response(cached)
        assert response.status_code == 201
        assert json.loads(response.content) == {'id': '123'}

    def test_restores_headers(self):
        cached = {
            'status': 200,
            'headers': {'X-Idempotent-Replay': 'true'},
            'body': '{}',
        }
        response = _build_cached_response(cached)
        assert response['X-Idempotent-Replay'] == 'true'


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class TestIdempotentDecorator(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _make_view(self, return_status=200, return_body=None):
        class MockView:
            @idempotent()
            def post(self, request, *args, **kwargs):
                body = return_body or {'result': 'created'}
                return JsonResponse(body, status=return_status)
        return MockView()

    def test_get_bypasses_idempotency(self):
        factory = RequestFactory()
        view = self._make_view()
        request = factory.get('/api/test/')
        resp1 = view.post(request)
        resp2 = view.post(request)
        assert resp1.content == resp2.content

    def test_no_key_header_bypasses_idempotency(self):
        factory = RequestFactory()
        call_count = 0
        nonlocal_ref = {'count': 0}

        class CountingView:
            @idempotent()
            def post(self, request, *args, **kwargs):
                nonlocal_ref['count'] += 1
                return JsonResponse({'count': nonlocal_ref['count']}, status=201)

        view = CountingView()
        request = factory.post('/api/test/')
        view.post(request)
        view.post(request)
        assert nonlocal_ref['count'] == 2

    def test_duplicate_request_returns_cached_response(self):
        factory = RequestFactory()
        call_count = 0
        nonlocal_ref = {'count': 0}

        class CountingView:
            @idempotent()
            def post(self, request, *args, **kwargs):
                nonlocal_ref['count'] += 1
                return JsonResponse({'count': nonlocal_ref['count']}, status=201)

        view = CountingView()
        request = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='idem-1')
        resp1 = view.post(request)
        resp2 = view.post(request)
        assert nonlocal_ref['count'] == 1
        assert resp1.content == resp2.content

    def test_different_keys_execute_separately(self):
        factory = RequestFactory()
        call_count = 0
        nonlocal_ref = {'count': 0}

        class CountingView:
            @idempotent()
            def post(self, request, *args, **kwargs):
                nonlocal_ref['count'] += 1
                return JsonResponse({'count': nonlocal_ref['count']}, status=201)

        view = CountingView()
        req1 = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='idem-a')
        req2 = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='idem-b')
        view.post(req1)
        view.post(req2)
        assert nonlocal_ref['count'] == 2

    def test_delete_also_idempotent(self):
        factory = RequestFactory()
        nonlocal_ref = {'count': 0}

        class CountingView:
            @idempotent()
            def delete(self, request, *args, **kwargs):
                nonlocal_ref['count'] += 1
                return JsonResponse({'deleted': True}, status=200)

        view = CountingView()
        request = factory.delete('/api/test/', HTTP_IDEMPOTENCY_KEY='del-1')
        view.delete(request)
        view.delete(request)
        assert nonlocal_ref['count'] == 1

    def test_caches_status_code_and_body(self):
        factory = RequestFactory()

        class StatusView:
            @idempotent()
            def post(self, request, *args, **kwargs):
                return JsonResponse({'error': 'conflict'}, status=409)

        view = StatusView()
        request = factory.post('/api/test/', HTTP_IDEMPOTENCY_KEY='conflict-1')
        resp1 = view.post(request)
        resp2 = view.post(request)
        assert resp1.status_code == 409
        assert resp2.status_code == 409
        assert resp1.content == resp2.content
