"""Analytics cache layer using generation counter invalidation.

Instead of scanning Redis to delete keys by pattern (a known anti-pattern
that blocks the event loop), we store a per-cooperative generation counter
in Redis. Every cache key includes the generation. Invalidation is one
atomic INCR — old keys expire naturally via TTL.
"""

import hashlib
import json

from django.core.cache import cache

ANALYTICS_CACHE_PREFIX = 'analytics:'
DEFAULT_TTL = 300  # 5 minutes


def _gen_key(cooperative_id=None, scope='cooperative'):
    """Return the generation counter Redis key for a scope."""
    if scope == 'global':
        return f'{ANALYTICS_CACHE_PREFIX}gen:global'
    if cooperative_id:
        return f'{ANALYTICS_CACHE_PREFIX}gen:{cooperative_id}'
    return None


def get_generation(cooperative_id=None, scope='cooperative'):
    """Get the current generation number (never expires, defaults to 0)."""
    key = _gen_key(cooperative_id, scope)
    if key is None:
        return 0
    return cache.get_or_set(key, 0, timeout=None)


def invalidate_analytics_cache(cooperative_id=None, scope='cooperative'):
    """Invalidate analytics cache by incrementing generation counter.

    One atomic INCR — no blocking Redis scan. Old cache keys still
    exist but resolve to a stale generation and are ignored.
    """
    key = _gen_key(cooperative_id, scope)
    if key is not None:
        if cache.get(key) is None:
            cache.set(key, 1, timeout=None)
        else:
            cache.incr(key)


def _make_cache_key(scope_type, cooperative_id, farmer_id, action, params_hash, generation):
    raw = f'{scope_type}:{cooperative_id or ""}:{farmer_id or ""}:{action}:{params_hash}:{generation}'
    h = hashlib.sha256(raw.encode()).hexdigest()
    return f'{ANALYTICS_CACHE_PREFIX}{h}'


def hash_params(params):
    """Deterministic hash of sorted JSON params."""
    raw = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_cached_analytics(scope_type, cooperative_id, farmer_id, action, params):
    """Try to get cached analytics response.

    Returns (data, cache_key) or (None, cache_key) on miss.
    """
    generation = get_generation(cooperative_id, scope_type)
    params_h = hash_params(params)
    key = _make_cache_key(scope_type, cooperative_id, farmer_id, action, params_h, generation)
    data = cache.get(key)
    if data is not None:
        data['cached'] = True
    return data, key


def set_cached_analytics(key, data, ttl=DEFAULT_TTL):
    """Store analytics response in cache with TTL."""
    data['cached'] = False
    data['cached_at'] = str(data.get('cached_at', ''))
    cache.set(key, data, timeout=ttl)


def record_access(cooperative_id):
    """Record that a cooperative's analytics were accessed (for cache warming)."""
    if cooperative_id:
        cache.set(
            f'{ANALYTICS_CACHE_PREFIX}last_access:{cooperative_id}',
            1,
            timeout=1800,  # 30 minutes
        )
