# Changelog

All notable changes to the Zao platform are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Phase 6: Backend architecture and deployment hardening
  - Self-registering cascade soft-delete registry (cooperative deletion cascades to all child models)
  - Cascade orphan repair data migration and management command
  - API versioning via `/api/v1/` URL prefix (aliasing, no redirects)
  - Chatbot system prompt externalized to `ChatbotConfig` model with Redis cache
  - USSD menus externalized to `USSDMenuConfig` model with EN/SW language support
  - Cooperative-level configurable USSD delivery limit
  - Phase 7: Documentation cleanup and API schema completeness
    - Deleted redundant `doc.md` (subset of `ARCHITECTURE.md`)
    - Created `CONTRIBUTING.md` with development setup and coding conventions
    - Created `CHANGELOG.md` with retroactive version tracking
    - Created `render.yaml` for reproducible deployment
    - Created `docs/adr/` with 5 Architecture Decision Records
    - Added `@extend_schema` decorators to all undocumented viewsets

## [1.0.0] - 2026-07-16

### Core Platform
- Farmer membership registration, profile management, and payment method configuration
- Offline-first delivery logging via PWA (IndexedDB + Service Worker)
- Quality grading with grade-based pricing and audit trail
- Cooperative inventory management by grade and batch
- Sales logging to external buyers
- Payment engine supporting Fixed Price (dairy) and Revenue Share (coffee, honey) models
- Deductions: cooperative levy, cooperative fee, loan repayments, farm input credits
- Withholding tax computation by KRA fiscal year threshold
- Payment cycle preview, lock, and disbursement workflow
- M-Pesa B2C disbursement via Daraja API with callback handling
- Bank CSV export (Equity/KCB/Generic formats)
- SMS delivery receipts and payment notifications via Africa's Talking
- USSD farmer self-service (balance, last payment, delivery history)
- Farmer web portal with delivery history, grade breakdown, statements
- PDF statement and seasonal cooperative report generation via WeasyPrint
- Multi-tenant architecture (multiple cooperatives, full data isolation)
- Role-based access control (6 roles: Farmer, Grader, Manager, Accountant, Internal Auditor, External Auditor)
- 12 internal DRF APIs with Swagger/ReDoc auto-documentation
- AI chatbot powered by Google Gemini for farmer self-service
- Legal document management with versioning and acceptance tracking
- Analytics dashboard with role-scoped metrics
- Superadmin panel with cross-cooperative management

### Infrastructure
- Django 6.0.5 + Django REST Framework 3.17.1
- PostgreSQL 16 with connection pooling (psycopg)
- Celery 5.6.3 + Redis 7 for async task processing
- React 19.2.6 + Vite 8.0.12 frontend
- Docker Compose development stack
- Render + Cloudflare Pages production deployment
- Sentry error tracking with PII scrubbing
- JWT authentication with HTTP-only cookie refresh
- 2FA via email OTP for sensitive roles
- Fernet field-level encryption for sensitive data
- Audit trail (append-only AuditLog)
- Soft-delete with trash bin and hard purge
