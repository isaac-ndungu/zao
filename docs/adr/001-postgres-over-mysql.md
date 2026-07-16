# ADR-001: PostgreSQL over MySQL

**Status:** Accepted  
**Date:** 2026-01-15  
**Deciders:** Backend team

## Context

We need a relational database that supports JSON data, full-text search, and efficient indexing for append-only audit logs. The platform serves multiple cooperatives with strict data isolation, and the payment engine relies heavily on JSON aggregation.

## Decision

We chose PostgreSQL 16.

## Alternatives Considered

- **MySQL 8:** Wider hosting support, but lacks `JSONField` with indexable JSONB, `BrinIndex` for time-series audit logs, `SearchVectorField` for full-text search, and partial indexes.
- **MongoDB:** Flexible schema, but foreign key integrity would require application-level enforcement — unacceptable for a financial platform where referential integrity is non-negotiable.
- **SQLite:** Development only. No concurrent writes, no connection pooling, no production-grade features.

## Consequences

**Positive:**
- `JSONField` with JSONB storage supports `grade_breakdown`, `totals`, `computation_log`, and `deductions` with index queries.
- `SearchVectorField` with `gin_trgm_ops` enables farmer full-text search by name.
- `BrinIndex` on `created_at` fields provides space-efficient indexing for append-only `AuditLog`.
- Partial indexes on `deleted_at IS NULL` optimize soft-delete query patterns.
- `psycopg[binary,pool]` with `CONN_MAX_AGE=600` handles Celery worker connection pooling.

**Negative:**
- Requires more operational expertise than MySQL.
- Connection pool tuning is necessary to avoid exhaustion under Celery worker concurrency.
- Some ORM features (e.g., `JSONBAgg`, window functions) require raw SQL for complex analytics queries.
