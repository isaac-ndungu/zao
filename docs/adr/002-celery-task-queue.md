# ADR-002: Celery as Task Queue

**Status:** Accepted  
**Date:** 2026-01-15  
**Deciders:** Backend team

## Context

We need async processing for M-Pesa B2C disbursement (rate-limited at 50 requests/minute), SMS delivery, report generation (PDF), and scheduled tasks (reconciliation, analytics aggregation). Tasks must be durable (survive worker restarts) and support rate limiting with blackout windows.

## Decision

We chose Celery 5.6.3 with Redis 7 as the broker and result backend, plus `django-celery-beat` for periodic task scheduling via the database.

## Alternatives Considered

- **Django-Q2:** Simpler setup, but lacks mature rate limiting, chord/group primitives, and the ecosystem maturity needed for M-Pesa callback handling with retry and dedup.
- **RQ (Redis Queue):** Lightweight, but no built-in periodic scheduling, no priority queues, and limited monitoring.
- **ARQ (async):** Requires async Django, which DRF does not natively support. Premature migration risk.
- **Huey:** Minimal features, no database-backed scheduler.

## Consequences

**Positive:**
- Mature ecosystem with `django-celery-beat` for database-backed periodic scheduling.
- Built-in rate limiting via `RateLimiter` for M-Pesa B2C dispatch.
- `group()` and `chord()` primitives enable parallel disbursement with aggregation callbacks.
- `celery.task.apply_async(countdown=30)` handles chunked disbursement with 30-second delays.
- Flower integration for production monitoring.
- Redis as broker provides sub-millisecond task dispatch latency.

**Negative:**
- Redis is a single point of failure — requires monitoring and backup.
- `django-celery-beat` scheduler polls the database every 60 seconds, introducing latency for schedule changes.
- Worker concurrency tuning (`CELERY_WORKER_CONCURRENCY`) must match database connection pool limits to avoid exhaustion.
