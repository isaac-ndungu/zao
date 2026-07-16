# Zao: Project Documentation


## Chapter 1: Project Overview

Zao is a cooperative management platform designed for Kenyan agricultural cooperatives. It digitizes the full operations cycle, from farm-gate delivery recording through quality grading, inventory management, payment computation, and final disbursement via M-Pesa, with full auditability and transparency at every step.

### The Domain Problem

Agricultural cooperatives in Kenya face a fundamentally complex payment computation problem. A single payment cycle must aggregate deliveries from hundreds of farmers, each delivery falling into a different quality grade with a different price per unit, apply cooperative-specific levy percentages, cooperative membership fees, loan repayments, farm input credits, withholding tax based on Kenyan KRA thresholds, and finally arrive at a net amount for each farmer. This computation must be auditable, reproducible, and dispute-free.

The domain complexity is compounded by three structural realities:

1. **Multi-tenancy by design.** Each cooperative operates with complete data isolation, but the platform must host hundreds of cooperatives on a single deployment. Every query must be scoped to the correct cooperative. A bug that omits this scoping leaks every cooperative's data to every other cooperative.

2. **Heterogeneous payment models.** Dairy and honey cooperatives use a fixed-price model where each litre or kilogram is paid at a grade-determined rate set by the cooperative. Coffee cooperatives use revenue share, where farmer payment is proportional to the total quantity they delivered versus the total quantity the cooperative sold to external buyers. These two models require completely different computation algorithms.

3. **Offline-first field operations.** Rural collection points may not have reliable internet connectivity. Graders must be able to record deliveries offline and sync when connectivity returns. The platform must handle duplicate detection, batch ordering, and GPS coordinate capture in an offline context.

### Users and Their Needs

The platform serves six distinct roles:

**Farmers** deliver produce at collection points and need to see their delivery history, grade breakdowns, payment statements, and loan balances. Many operate basic feature phones without internet, so USSD self-service is a first-class interface alongside the React-based web portal.

**Graders** are cooperative staff who inspect farmer deliveries and assign quality grades at the collection point. They need an offline-capable interface that works without internet, a Progressive Web App with IndexedDB storage and Service Worker sync.

**Cooperative Managers** oversee all cooperative operations. They create payment cycles, lock them when satisfied, approve disbursement batches, manage farmer disputes, and configure cooperative settings.

**Accountants** handle the financial pipeline. They run the payment engine, preview computed payments, initiate disbursements, manage deductions and farm input credits, and generate financial reports.

**Internal Auditors** review cooperative financials and operations with read-only access to all cooperative data and the full audit log.

**External Auditors** access only financial actions (payment cycles, disbursements, deductions, loans), a filtered subset of the audit log appropriate for regulatory review.

### Core Workflow

The payment lifecycle follows this sequence:

1. A **Farmer** arrives at a collection point with produce. A **Grader** records the delivery via the offline-capable PWA, assigning a batch ID and provisional status `PENDING`.

2. The **Grader** inspects the produce and assigns a quality grade (`PREMIUM`, `A`, `B`, `C`, or rejection). The grading action updates the delivery status, triggers an inventory update (the cooperative's bulk pool and per-grade stock are incremented), and sends an SMS receipt to the farmer.

3. The cooperative **Accountant** logs a bulk sale to an external buyer at a negotiated price. The sale records revenue against the cooperative's inventory.

4. The **Accountant** creates a payment cycle covering a date range and triggers the payment engine. The Celery task `run_payment_engine` aggregates all graded deliveries in the cycle date range, applies grade prices or computes revenue share, applies deductions (levy, cooperative fee, loan repayments, farm input credits), computes withholding tax, and creates a `FarmerPayment` record for each active farmer.

5. The **Accountant** previews computed payments, resolving any warnings (e.g., deliveries graded but no grade record found). The **Manager** locks the cycle, making it immutable.

6. The **Accountant** initiates a disbursement batch. The **Manager** approves it. The Celery task `process_batch_disbursements` iterates transactions in chunks of 50 with 30-second delays to respect M-Pesa rate limits, dispatching each via the Daraja B2C API. M-Pesa callbacks update transaction status. Farmers receive SMS payment confirmations.

7. Farmers can check their last payment balance via USSD (`*384*11411#`) or download a PDF statement from the web portal.

### Why This Project Is Crucial

The complexity is not in any single operation but in the integration of many domain-specific constraints:

- **Grade price snapshots.** The payment engine must use the grade prices that were effective on the delivery date, not the current prices. A `GradePrice` record has an `effective_from` date, and the engine queries the most recent price before the delivery date.

- **Revenue share with edge cases.** When a single farmer made all deliveries in a cycle, they receive 100% of revenue: a warning is emitted. When `revenue_share_by_produce_type` is enabled, revenue is split proportionally by produce type.

- **Carry-forward minimum payout.** If a farmer's computed net amount is below the cooperative's `minimum_payout_amount` (default KES 0), the amount is carried forward to the next cycle rather than disbursed. Multiple cycles of carry-forward can accumulate.

- **Withholding tax by fiscal year threshold.** Kenya KRA requires 5% withholding tax on farmer payments exceeding KES 24,000 cumulative per fiscal year (July 1 to June 30). The engine tracks cumulative prior payments and computes tax only on the amount above the threshold.

- **Reversible deductions on failed disbursement.** If an M-Pesa B2C transaction fails after deductions were recorded, those deductions must be reversed: loan repayment increments are undone, farm input credit balances are restored, and the farmer payment is marked failed.

- **Offline sync with idempotency.** The `POST /api/deliveries/sync/` endpoint accepts a batch of deliveries with client-generated `local_id` values. It must detect duplicates by `local_id`, return 409 on conflict, and process all valid deliveries atomically.

---

## Chapter 2: Day Zero and Project Decisions

### 2.1 Technology Stack Selection

#### Django + Django REST Framework

**Chosen:** Django 6.0.5 with Django REST Framework 3.17.1

**Alternatives considered:** FastAPI (async-first, Pydantic validation), Django Ninja (faster, type-safe serializers), Node.js/Express (lighter footprint)

**Why Django + DRF:** The project required a system that could be understood by a small team quickly. Django's built-in admin, ORM, and migration system eliminated significant boilerplate. DRF's `ModelViewSet`, `ModelSerializer`, and `BasePermission` patterns provided a consistent API surface across all 14 apps without custom framework code. The existing `CooperativeScopedViewSet` base class enforces multi-tenancy at the ORM level, a pattern that would be significantly more code in FastAPI.

**Tradeoffs accepted:** DRF's serializer validation is synchronous and blocking. For high-volume read endpoints, DRF's nested object serialization can produce N+1 queries if `select_related`/`prefetch_related` are forgotten. The framework does not enforce that API clients use the OpenAPI schema, documentation must be maintained manually alongside code.

**What we would choose differently today:** The `CooperativeScopedViewSet` get_queryset override uses `request.cooperative_id` set by middleware, which works but blurs the line between authentication (who is this user) and authorization (what data can they see). A more explicit permission class would be cleaner. Django Ninja's dependency injection would make this more explicit.

---

#### PostgreSQL

**Chosen:** PostgreSQL 16

**Alternatives considered:** MySQL (wider hosting support, but no JSONField, no BrinIndex, no partial indexes), MongoDB (flexible schema, but foreign key integrity would require application-level enforcement), SQLite (development only, no concurrent writes, no connection pooling)

**Why PostgreSQL:** The data model requires `JSONField` for `grade_breakdown`, `totals`, `computation_log`, and `deductions` , all of which benefit from PostgreSQL's JSONB storage with index support. `SearchVectorField` for farmer full-text search requires PostgreSQL's `tsvector` and `gin_trgm_ops` indexes. `BrinIndex` on `created_at` fields provides space-efficient indexing for append-only audit logs. Connection pooling via `psycopg[binary,pool]` with `CONN_MAX_AGE=600` and `CONN_HEALTH_CHECKS=True` handles the Celery worker concurrency.

**Tradeoffs accepted:** PostgreSQL requires more operational expertise than MySQL. Connection pooling via `psycopg[binary,pool]` with `CONN_MAX_AGE=600` and `CONN_HEALTH_CHECKS=True` handles Celery worker concurrency; this requires careful tuning of `WEB_CONCURRENCY` and `CELERY_WORKER_CONCURRENCY` to avoid connection exhaustion.

---

#### Celery + Redis

**Chosen:** Celery 5.6.3 with Redis 7 as broker and result backend

**Alternatives considered:** Django Q which is simpler setup, but less battle-tested at scale.

**Why Celery:** The payment engine's `run_payment_engine` task must acquire a distributed Redis lock (`SETNX` with TTL) to prevent concurrent computation on the same cycle. Celery's `bind=True` shared task pattern and `AsyncResult` for task state tracking integrate naturally with Django. `django-celery-beat` provides database-backed periodic task scheduling that survives worker restarts. The `CELERY_WORKER_PREFETCH_MULTIPLIER=1` setting ensures large batches don't starve individual tasks.

**Tradeoffs accepted:** `CELERY_TASK_ALWAYS_EAGER=True` is a development convenience only. If Redis becomes unavailable in production, queued tasks resume when it recovers but new tasks cannot be queued until Redis is restored. The distributed lock is best-effort: if a worker crashes while holding the lock, the TTL (30 minutes) provides recovery.

---

#### React + Vite

**Chosen:** React 19.2.6 with Vite 8.0.12

**Alternatives considered:** Next.js (SSR, API routes, but added complexity for a primarily API-consuming SPA) and Vue 3 (simpler reactive model, but smaller ecosystem for fintech dashboards)

**Why React + Vite:** The farmer portal requires offline-first PWA behavior with Service Workers and IndexedDB, this is easier to implement in a Create-React-App-equivalent build system than in a framework with its own SSR model. Vite's fast HMR and multi-entry build support (`input: { main: 'index.html', farmer: 'farmer/index.html' }`) enable the two-SPA architecture without a monorepo tool. React's component model and the existing Tailwind CSS ecosystem provided the dashboard components needed for the admin/manager/accountant interfaces.

**Tradeoffs accepted:** React 19's new features (Actions, startTransition) are not yet used, the codebase uses the className + manual state pattern throughout. Vite's polling file watcher (`usePolling: true`) in settings is a workaround for Docker volume mounts, adding CPU overhead.

---

#### Tailwind CSS

**Chosen:** Tailwind CSS 4.3.1 (via `@tailwindcss/vite`)

**Alternatives considered:** CSS Modules (scoped by default, but no design system consistency enforcement)

**Why Tailwind:** The design system in `client/src/index.css` defines CSS custom properties for a green (`#1a6b3c`) cooperative brand palette. Tailwind's `@tailwindcss/vite` plugin processes these at build time, generating minimal CSS with no runtime overhead. The farmer portal's mobile-first design with `max-w-lg mx-auto` container constraints is straightforward in utility classes.

**Tradeoffs accepted:** Tailwind's ` JIT` mode (now default) generates CSS on demand, but the `safelist` configuration must be kept in sync with dynamically-generated class strings. Long strings of `hover:` and `focus:` modifiers reduce readability.

---

#### Recharts

**Chosen:** Recharts 3.8.1

**Alternatives considered:** Chart.js (canvas-based, more control, but no React integration), 

**Why Recharts:** Pure React SVG-based charts with a simple declarative API (`<LineChart><Line ... />`). The admin dashboard (`client/src/admin/pages/Dashboard.jsx`) uses Recharts for delivery trends, grade distributions, and financial summaries. Recharts' `ResponsiveContainer` handles the dashboard's fluid layouts.

**Tradeoffs accepted:** Recharts has no built-in dark mode support, chart colors are hardcoded. Performance degrades with thousands of data points (no canvas fallback).

---

#### JWT Authentication (Simple JWT)

**Chosen:** `djangorestframework_simplejwt` 5.5.1 with access token lifetime 1 day and refresh token lifetime 30 days

**Alternatives considered:** Session-based auth (Django sessions, but incompatible with the React SPA's separate origin)

**Why JWT:** The React SPA and farmer portal are separate origins from the Django API. Cookie-based sessions would require CORS configuration and a CSRF token dance that adds complexity. JWT access tokens stored in React component state (not localStorage, to reduce XSS exposure) with HTTP-only refresh tokens in cookies provides a secure middle ground. `ROTATE_REFRESH_TOKENS=True` ensures old refresh tokens are invalidated on use, a stolen refresh token has at most 30 days of validity.

**Tradeoffs accepted:** JWT access tokens are not revocable before expiry. If an token is compromised, the only remedy is to blacklist the refresh token (which `rest_framework_simplejwt.token_blacklist` does via Redis) or change the user's password. The refresh cookie path is set to `/api/auth/` ; any cross-origin request to refresh does not include the cookie.

---

#### Cloudinary (Media Storage)

**Chosen:** Cloudinary via `django-cloudinary-storage`

**Alternatives considered:** AWS S3 (cheaper at scale, but more configuration), local file storage (free, but no CDN, unsuitable for production), WhiteNoise (static files only, not media)

**Why Cloudinary:** The cooperative logo uploads, grade image attachments, and PDF statement storage benefit from Cloudinary's automatic image transformation and CDN delivery. The `DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'` setting routes all file uploads through Cloudinary without application code changes.

**Tradeoffs accepted:** Cloudinary's free tier has bandwidth limits unsuitable for high-volume cooperatives. The `CLOUDINARY_URL` environment variable must be kept secret, if exposed, anyone can write to the Cloudinary account.

---

#### Django SMTP Email Backend

**Chosen:** `django.core.mail.backends.smtp.EmailBackend` with SendGrid SMTP relay (`smtp.sendgrid.net`)

**Alternatives considered:** Gmail SMTP (free, but 500 emails/day limit on consumer accounts, 2000/day on Workspace), Anymail (abstracts providers, but adds a dependency)

**Why SendGrid:** Dedicated transactional email service with higher rate limits than Gmail. Uses Django's standard SMTP backend — no additional Python packages required. The `apikey` is the `EMAIL_HOST_USER` and the SendGrid API key is the `EMAIL_HOST_PASSWORD`.

**Tradeoffs accepted:** SendGrid's free tier is limited (100 emails/day). Paid tiers start at around $20/month for higher volumes. If SendGrid is unavailable, emails queue in the SMTP connection and retry automatically.

---

#### Africa's Talking (SMS + USSD)

**Chosen:** Africa's Talking SDK (`africastalking==2.0.2`)

**Alternatives considered:** Twilio (more expensive, but better USSD support), direct M-Pesa SMS (no USSD self-service)

**Why Africa's Talking:** Africa's Talking provides both SMS and USSD on a single account with Kenyan shortcodes. The USSD self-service (`*384*11411#`) gives every farmer, including those on basic phones without internet, access to delivery history and last payment information. The `NOTIFICATIONS_DRY_RUN=True` default prevents accidental SMS in development.

**Tradeoffs accepted:** Africa's Talking's USSD sessions are stateless, each callback contains only the current input, not the session history. The application implements state via the `USSDSession` database model, storing `current_menu` and replaying the session from the database on each callback. This requires a database write on every USSD interaction.

---

#### M-Pesa Daraja B2C API

**Chosen:** Safaricom M-Pesa Daraja API B2C (Business to Customer) payment

**Alternatives considered:** Bank-only disbursement (cheaper per transaction, but farmers may not have bank accounts), Pesapal (aggregator, but higher fees), direct M-Pesa API without Daraja (requires B2C contract with Safaricom)

**Why M-Pesa:** Over 80% of Kenyan adults have M-Pesa accounts. B2C disbursement transfers directly to farmer phone numbers without requiring bank account details. The Daraja API provides OAuth authentication (consumer key/secret), certificate-based security credential encryption, and callback webhooks for transaction status.

**Tradeoffs accepted:** The B2C API has rate limits (typically 50 transactions per second per shortcode, configurable by Safaricom). The `process_batch_disbursements` task chunks at 50 with 30-second delays between chunks. M-Pesa does not guarantee callback delivery, the `reconcile_stuck_transactions` task polls every 15 minutes for transactions stuck in `QUEUED` or `SENT` status.

---

#### Render (Backend) + Cloudflare Pages (Frontend)

**Chosen:** Render for the Django backend (web service + Celery worker), Cloudflare Pages for the React frontend

**Alternatives considered:** AWS (full control, but complex setup), Railway (simpler, but less predictable pricing at scale), Vercel (frontend only, no backend)

**Why Render:** Render's `gunicorn` web server, Celery worker, and Celery beat can all run as separate services within the same deployment. The `Dockerfile` builds the Django image; Render pulls from the GitHub repository and sets environment variables from its dashboard.

**Tradeoffs accepted:** Render's free tier has sleep behavior (services spin down after 15 minutes of inactivity). Cold starts on the Celery worker can delay payment disbursement initiation. There is no Render-specific `render.yaml` ; deployment is configured via Render dashboard environment variables. The `backend/entrypoint.sh` handles database migrations, static file collection, and starting both Celery workers and the Gunicorn web server.

---

### 2.2 Architecture Decisions

#### Multi-Tenancy Approach

**Chosen:** Cooperative-scoped models via `CooperativeScopedModel` abstract base class with a `TenantManager` that auto-filters `deleted_at__isnull=True` and requires `cooperative_id` on every query.

**Alternatives considered:**

- **Database-per-tenant:** Spin up a separate PostgreSQL database for each cooperative. Rejected because 500+ databases would exceed the hosting plan limits, and migrations would need to run on each database separately.
- **Schema-per-tenant:** Use PostgreSQL schemas (`CREATE SCHEMA cooperative_xxx`). Rejected because schema migration tooling is more complex and cross-cooperative reporting would require querying all schemas.
- **Row-level security (RLS):** PostgreSQL RLS policies that filter rows by `cooperative_id`. Rejected because RLS policies are invisible to the Django ORM, debugging missing data would require deep PostgreSQL knowledge.

**Why `CooperativeScopedModel` works:** Every model that holds cooperative data inherits from this abstract class. The `TenantManager` (the default manager on all cooperative-scoped models) overrides `get_queryset()` to add `deleted_at__isnull=True` filtering. The `CooperativeScopedViewSet` base class applies `cooperative_id` filtering at the viewset level. This two-layer approach keeps soft-delete handling at the model layer and tenant filtering at the API layer.

**Failure modes:** Tenant scoping is enforced at the **viewset layer**, not the model or manager layer. If a developer creates a `ModelViewSet` without inheriting from `CooperativeScopedViewSet`, or bypasses the viewset's `get_queryset()` in any other way, data from all cooperatives is returned without filtering. `TenantManager` only handles soft-delete filtering (`deleted_at__isnull=True`) — it does not scope by `cooperative_id`. Raw SQL (`MyModel.objects.raw()`) bypasses the ORM entirely and must include explicit `WHERE cooperative_id = ?` clauses. Celery tasks that use model methods directly must also apply cooperative filtering explicitly. No lint rule or automated test enforces viewset-level tenant isolation.

#### Monorepo vs Separate Repositories

**Chosen:** Monorepo, backend and frontend in one repository

**Why:** The project was built by a small team where coordinating separate repo releases for API contract changes would add overhead. The `endpoint.json` at `backend/endpoint.json` (175KB) is an auto-generated Postman API reference covering 172 endpoints. Docker Compose orchestrates six services from `docker-compose.yml`.

**Tradeoffs:** The frontend build (Vite) and backend build (Django collectstatic) are independent but share the same CI pipeline. Cloudflare Pages must be configured to build the React app and serve it from a CDN while the Django API runs on Render.

#### Django App Structure

**Chosen:** 14 Django apps (base, auth_api, cooperatives, users, farmers, deliveries, grading, inventory, routes, sales, payment_engine, deductions, loans, disbursement, notifications, statements, analytics, legal, chat, admin)

**Dependency order (not arbitrary):**

```
base → auth_api → cooperatives → users → farmers → deliveries → grading → inventory → routes → sales → payment_engine → deductions → loans → disbursement → notifications → statements → analytics → legal → chat → admin
```

**Why this ordering matters:** `base` defines `CooperativeScopedModel` and `TenantManager`. Every other app depends on these. `auth_api.User` is the AUTH_USER_MODEL and is referenced by `Farmer` (`OneToOneField`), `Delivery` (`grader` FK), and all cooperative staff models. `cooperatives` defines the `Cooperative` model that all cooperative-scoped models reference via FK. `farmers` defines `Farmer` and `FarmerCooperativeMembership` ; these are referenced by `Delivery`, `Grade`, `FarmerPayment`, `DisbursementTransaction`, and `Loan`. `payment_engine` depends on `Deliveries`, `Grading`, `Farmers`, `Sales` (for revenue share), and `Deductions`/`Loans` (for deduction computation). `disbursement` depends on `payment_engine`. `admin` is the only app that depends on everything (it aggregates across all cooperatives).

#### Async Task Architecture

**What is async:** `run_payment_engine` (Celery, can take 10+ minutes for large cycles), `process_batch_disbursements` (Celery, iterates 50 transactions per chunk with 30-second delays), `update_inventory_on_grade` (Celery, triggered on every grade create/update/override), `send_single_mpesa_disbursement` (Celery), `reconcile_stuck_transactions` (Celery beat, every 15 minutes), `compute_withholding_taxes` (inline in `run_payment_engine`, not a separate task), `send_delivery_sms`, `send_bulk_delivery_sms`, `reverse_deductions_on_failure`, `send_disbursement_sms`, all analytics snapshot tasks (daily, weekly, monthly), all cleanup tasks.

**What is synchronous:** All DRF view CRUD operations, all serializers, grade override (direct function call in view), disbursement batch creation (serializer `create` method), USSD callback handling (returns immediately; state is stored in DB).

**What happens if Redis is unavailable:** `CELERY_TASK_ALWAYS_EAGER=True` must be pre-configured, it is not a runtime failover. With `CELERY_TASK_ALWAYS_EAGER=False` (production), tasks queued before the outage sit in the Redis queue and resume when Redis recovers; new tasks cannot be queued until Redis is restored. If Redis dies mid-run after a task has been dispatched, the worker that picked it up completes it normally. SMS sends are skipped in dry-run mode regardless.

#### Frontend Architecture (Two SPAs)

**Why two entry points (`main: 'index.html'` and `farmer: 'farmer/index.html'`):** The farmer portal has fundamentally different UX requirements, mobile-first, bottom navigation, large touch targets, no complex admin tables. The admin/manager/accountant dashboard uses a sidebar layout with dense data tables. The two entry points produce two separate bundles: `assets/main-[hash].js` (the dashboard) and `assets/farmer-[hash].js` (the farmer portal). 

**Bundle implications:** The main SPA includes Recharts, Leaflet, React Router, and all admin/manager pages. The farmer SPA is lighter but still includes React and the delivery/payment/grade/loan pages. Neither bundle uses code splitting (lazy imports), all pages are loaded eagerly.

### 2.3 Data Model Decisions

#### `FarmerCooperativeMembership` exists separately from `Farmer`

**Why:** A farmer can belong to multiple cooperatives (a real scenario, a farmer might deliver to both a dairy and a coffee cooperative). The farmer's `member_number` is scoped to a cooperative, not globally unique. The membership tracks `payment_method`, `mpesa_number`, `bank_name`, `bank_account` ; all cooperative-specific payment routing. The `Farmer.primary_membership` property returns the membership for the current request's cooperative context.

**Why member_number is on Membership, not Farmer:** Different cooperatives have different numbering schemes. A cooperative with `prefix='DAIRY'` generates `DAIRY-2026-0001`. If the same farmer joins a different cooperative, they get a different member number.

**Alternative considered:** A single `member_number` column on `Farmer`. Rejected because the uniqueness constraint would break multi-cooperative membership.

#### `SaleInventoryLineItem` exists for multi-batch sales

**Why:** When a cooperative sells to a buyer, the sale may draw from multiple inventory pools (e.g., 100L from Grade A tank and 50L from Grade B tank). Rather than requiring the accountant to track this manually, `SaleInventoryLineItem` links a `Sale` to multiple `Inventory` records with per-line quantities. The `Sale.all_inventory` property aggregates these for display.

**Alternative considered:** A single `inventory` FK on `Sale` with a JSON field for extra pools. Rejected because FK constraints and `on_delete=PROTECT` prevent accidental deletion of inventory that has been used in a sale.

#### `grade_breakdown` JSONField has two incompatible shapes

**The inconsistency:** In `FIXED_PRICE` mode, `grade_breakdown` is:
```json
{"A": {"kg": 150.0, "amount": 4500.00}, "B": {"kg": 80.0, "amount": 2000.00}}
```

In `REVENUE_SHARE` mode, `grade_breakdown` is:
```json
{"A": 150.0, "PREMIUM": 75.5}
```

The `FarmerPayment.clean()` validator switches on `cycle.cooperative.payment_model` to validate the correct shape. `revenue_share` stores only quantities, not amounts, amounts are computed later when sales are finalized.

**Why this is a known inconsistency:** The two models were built at different times. A proper design would have separate serializers or a validated dataclass that enforces the shape at construction time, not at save time.

#### `DisbursementTransaction` is separate from `DisbursementBatch`

**Why:** A batch represents the accounting intention ("disburse KES 500,000 to farmers from cycle 12"). A transaction represents a single payment attempt to a single farmer. The batch has a status that aggregates its transactions. The separation allows partial failures, a batch can be `PARTIALLY_COMPLETED` with 95 successes and 5 failures, and each transaction can be retried independently.

#### `AuditLog` is in `base` app, not a dedicated `audit` app

**Why:** The `base` app is the foundation that all other apps depend on. Putting `AuditLog` there avoids a circular dependency (an `audit` app importing from `payment_engine` or `disbursement` would create a dependency cycle). The `base` app already contains middleware, permissions, and utilities shared across all apps.

**Tradeoff:** The `base` app has many responsibilities (models, middleware, permissions, throttles, utilities, encryption, health checks, export mixins). A future refactor could split these into `foundation` and `audit`.

#### Soft-delete (`deleted_at`) added to `User` and `Cooperative`

**Why:** Deactivating a user or cooperative should not immediately delete their data. Financial records (payment cycles, disbursements) depend on the cooperative and farmer records. `SoftDeletableModel` (for `User`) and `CooperativeScopedModel` (for cooperative-scoped models) both have `deleted_at`. The `TenantManager` filters out soft-deleted records by default, but `all_with_trashed()` and `trashed_only()` provide escape hatches.

**Cascade soft-delete:** When a `Cooperative` is soft-deleted, the `Cooperative.delete()` method manually cascades `deleted_at` to all related models (Farmers, Deliveries, PaymentCycles, etc.) by iterating over a hardcoded list and calling `update(deleted_at=now)`. This is manual and must be kept in sync when new models are added.

#### Payment engine uses `GradePriceSnapshot` approach

**Not a separate model:** There is no `GradePriceSnapshot` model. The "snapshot" is implicit in the query : `GradePrice` has `effective_from` and the engine queries the most recent price effective on or before each delivery's date:
```python
all_prices = GradePrice.objects.filter(effective_from__lte=cycle.end_date).order_by('grade_letter', '-effective_from')
price_map = {}
for gp in all_prices:
    if gp.grade_letter not in price_map:
        price_map[gp.grade_letter] = float(gp.price_per_unit)
```

**Why not a snapshot model:** Creating a snapshot record for every grade at the time of delivery would multiply write volume. The query approach is correct for auditability as long as `GradePrice` records are never modified or deleted, only new records with future `effective_from` dates are added.

#### `withholding_tax_amount` is stored but not deducted from `net_amount`

**Why:** The `FarmerPayment.net_amount` is the amount available for disbursement. The `withholding_tax_amount` is a separate KRA obligation that the cooperative must remit, it is not paid to the farmer (the farmer receives `net_amount`, not `net_amount - withholding_tax`). The cooperative must account for withholding tax separately when filing KRA returns. The `DisbursementTransaction.withholding_tax_amount` field is stored on each transaction for reconciliation but does not reduce the disbursement amount.

---

## Chapter 3: Build Sequence

The order in which Django apps and subsystems were built, from the foundational authentication and tenant-isolation layer through to the frontend dashboards.

### Phase 1 - Foundation

**What was built:** `base` app (soft-delete models, `TenantManager`, `TenantMiddleware`, `AuditLog`, `LegalAcceptanceMiddleware`, `ForcePasswordChangeMiddleware`, `CorrelationIDMiddleware`, `RequestLoggingMiddleware`, `SecurityHeadersMiddleware`), `auth_api` app (`User`, `TwoFactorOTP`, `UserManager`), `cooperatives` app (`Cooperative`), `users` app (cooperative-scoped user management views).

**Why first:** Every other app requires the tenant-isolation foundation. The authentication system must exist before any staff or farmer can log in. The `User.cooperative` FK must exist before cooperative-scoped staff models are created.

**Key decisions:** The `TenantMiddleware` extracts `cooperative_id` from the authenticated user and sets `request.cooperative_id`. For farmers, it reads `HTTP_X_COOPERATIVE_ID` header or derives from the farmer's active membership. This header-based approach was necessary because farmers authenticate via OTP (no session), so the mobile app passes the active membership context explicitly. The `LegalAcceptanceMiddleware` subquery was simplified to rely on the `UniqueConstraint (slug, is_active=True)` rather than tracking version numbers — this prevents users being re-prompted when a new legal document version is published.

### Phase 2 - Core Operations

**What was built:** `farmers` app (Farmer, FarmerCooperativeMembership), `deliveries` app (Delivery with offline sync), `grading` app (Grade, GradePrice, FarmerGradeDispute), `inventory` app (Inventory pool, Stock aggregate), `routes` app (CollectionRoute, RouteStop).

**Why this order:** Farmers must exist before deliveries can be recorded. Deliveries must exist before grading. Grading must create grade records that update inventory. Routes provide geographic structure for collection points but are not required for delivery recording (a delivery can be created without a `route_stop`).

**Offline sync design:** The `Delivery.local_id` field accepts client-generated UUIDs for idempotency. The `unique_delivery_local_id` partial constraint (condition: `local_id > ''`) rejects duplicates at the database level, returning 409 Conflict. The `DeliverySyncSerializer` iterates incoming deliveries, checks for existing `local_id`, and bulk-creates valid ones. The `Grade.is_inventory_updated` flag tracks whether the inventory-queue Celery task completed successfully after a grade was recorded.

### Phase 3 - Financial Pipeline

**What was built:** `sales` app (Buyer, Sale, SaleInventoryLineItem), `payment_engine` app (PaymentCycle, FarmerPayment, ComputationWarning), `deductions` app (Deduction, FarmInputCredit), `loans` app (Loan, LoanRepayment, LoanGuarantor).

**Why this order:** Sales revenue is needed for revenue share computation. The payment engine needs deliveries, grades, grade prices, and sales. Deductions and loans feed into the payment engine's deduction computation step.

**Key design decisions:** The `grade_breakdown` JSONField was given two different shapes depending on `payment_model`, avoiding separate models for the two computation paths. The `computation_log` JSONField on `FarmerPayment` stores a forensic record of exactly how the payment was computed — the `DeductionBreakdown` dataclass is serialized as a dict and stored. The `GradePrice` snapshot approach queries prices effective on delivery dates rather than current prices.

### Phase 4 - Disbursement

**What was built:** `disbursement` app (DisbursementBatch, DisbursementTransaction, M-Pesa B2C via Daraja, callbacks, reconciliation).

**M-Pesa integration:** The `MpesaDarajaClient` class encapsulates OAuth token management (with 60-second expiry buffer), security credential encryption using the public certificate, and all B2C API calls. The `send_single_mpesa_disbursement` task is the atomic unit — it uses `select_for_update()` inside a transaction to prevent double-sending.

**Rate limiting:** Batches are processed in chunks of 50 with a 30-second delay between chunks, a batching strategy to avoid overwhelming the Daraja API rather than a true Celery rate limit.

**Idempotency:** Each `DisbursementTransaction` is created with `conversation_id=str(uuid.uuid4())` before the API call. The callback handler queries by `conversation_id`, ensuring a duplicate callback does not create duplicate records.

### Phase 5 - Supporting Systems

**What was built:** `notifications` app (SMS, email, USSD), `statements` app (PDF generation, KRA report, season report), `legal` app (LegalDocument, LegalAcceptance with atomic publish), `analytics` app (snapshots, cache, queries), `chat` app (Gemini AI chatbot).

**USSD session state:** Africa's Talking sends a callback per interaction with no session memory. The `USSDSession` model stores `current_menu` in the database. On each callback, `handle_ussd` reads the session, determines the next state, updates `current_menu`, and returns the response string. The state machine handles: `HOME` → `MEMBER_NUMBER` → (single membership) `MENU` or `COOP_PICKER` → `DELIVERIES` or `PAYMENTS` or `PROFILE`.

### Phase 6 - Admin Infrastructure

**What was built:** `admin` app (superadmin views across all cooperatives: `TrashManagement`, `HealthMonitor`, `OTPTokens`, `UserManagement`, `Cooperatives`, `FarmerLedger`, `FarmerPayments`, `LegalAcceptances`, `LegalDocumentEdit`, `SearchResults`, `AuditTrail`, `Financials`, `SeasonalPatterns`, `FarmerRetention`, `Logistics`, `ProduceReceipts`, `Loans`, `Inventory`, `Support`, `Settings`).

**`SuperAdminIPMiddleware`:** The `/api/admin/` routes are protected by IP whitelist. If `SUPERADMIN_ALLOWED_IPS` is set, requests from non-whitelisted IPs return 404 (not 403), hiding the existence of the endpoint from unauthorized clients.

### Phase 7 - Frontend: Admin Dashboard

**What was built:** React SPA at `client/index.html`. Built with React 19, React Router v7, and Tailwind CSS. Typography uses DM Sans (body), DM Mono (monospace), Merriweather (headings), and Material Symbols (icon font). Maps are rendered with Leaflet + OpenStreetMap tiles; routing uses OSRM.

**Admin routes (23 under `/admin/`):** `dashboard`, `ledger` (farmer ledger), `receipts` (produce receipts), `inventory`, `logistics`, `financials`, `profile`, `settings`, `support`, `users` (user management), `audit` (audit trail), `trash` (trash management), `health` (health monitor), `cooperatives`, `loans`, `farmer-payments`, `otp-tokens`, `grade-prices`, `analytics/seasonal`, `analytics/retention`, `search`, `legal`, `legal/documents/:id`, `legal/acceptances`. All components are code-split via `React.lazy`. The Admin section uses `AdminLayout` with `AdminGuard` (IP whitelist check) and `AdminAuthProvider`. `LegalAcceptanceGate` wraps authenticated routes. `ErrorBoundary` catches rendering errors per section.

**Public routes:** Marketing pages at `/`, `/solutions`, `/farmers`, `/about`, `/contact`, `/legal/:slug`. Auth pages at `/admin/login` and `/accept-invite`.

### Phase 8 - Frontend: Role Dashboards

All six role dashboards are defined in the same `App.jsx` router, each code-split by `React.lazy`.

**Farmer Portal (`farmer/index.html` → `farmer/App.jsx`):** A separate Vite entry point producing an independent bundle. Configured as an installable PWA with `manifest.json`, `apple-mobile-web-app-capable`, and `theme-color: #1a6b3c`. Constrained viewport (`user-scalable=no`) for a native app feel. Renders in a `max-w-lg mx-auto` column with `BottomNav` bar. Routes: `dashboard`, `deliveries`, `payments`, `grades`, `loans`, `profile`, `chat`, `settings`, `notifications`. Auth uses a JWT token in `localStorage` checked by `FarmerAuthProvider`. `FloatingAccessibilityWidget` mounted via `createPortal`. `LegalAcceptanceGate` enforces legal acceptance before any authenticated route. The farmer app has its own React Router context (`BrowserRouter`) separate from the admin app.

**Manager Dashboard (`/manager`):** 19 routes using `ManagerLayout` (sidebar + header). Covers cooperative operations: `dashboard`, `farmers`, `deliveries`, `grading` (grading queue), `cycles`, `disbursements`, `loans`, `sales` (sales + buyers), `inventory`, `deductions`, `reports`, `routes`, `setup/cooperative`, `users`, `audit-log`, `grade-prices`, `profile`, `settings`, `search`.

**Grader Dashboard (`/grader`):** 9 routes using `GraderLayout` (sidebar + header). Core offline-first workflow: `dashboard`, `record-delivery` (offline-capable delivery entry), `grade` (quality grading form), `my-grades`, `sync` (IndexedDB sync), `profile`, `settings`, `search`. `RecordDelivery` and `Grade` forms are designed for field use.

**Accountant Dashboard (`/accountant`):** 10 routes using `AccountantLayout`. Financial operations: `dashboard`, `cycles`, `disbursements`, `loans`, `deductions`, `reports`, `profile`, `settings`, `search`.

**Internal Auditor Dashboard (`/auditor`):** 10 routes using `AuditorLayout`. Read-only review: `dashboard`, `audit-log`, `financial`, `production`, `loans`, `reports`, `profile`, `settings`, `search`.

**External Auditor Dashboard (`/external-auditor`):** 6 routes using `ExternalAuditorLayout`. Restricted to externally-relevant financials: `financial-statements` (default redirect), `audit-trail`, `loan-portfolio`, `profile`, `search`.

All role dashboards use `RoleGuard` (checks `user.role`), `LegalAcceptanceGate`, and `ErrorBoundary`. Charts are rendered with Recharts.


---

## Chapter 4: The Data Model Reference

### `apps.base.models`

**`SoftDeletableModel`** - Abstract base for `User`. Adds `deleted_at`, `restored_at`, `deleted_via_cascade_from`. `soft_delete()` sets `deleted_at=now`. `restore()` clears `deleted_at`. `delete()` calls `soft_delete()` (never hard delete for users).

**`AuditAction`**: `TextChoices` enum with 56 action types covering all write operations (CREATE, UPDATE, DELETE, OVERRIDE, LOCK, UNLOCK, RUN, DISBURSE, GRADE, etc.).

**`LocationMixin`**: Adds `latitude` and `longitude` DecimalFields to `Delivery` and `Farmer`.

**`TenantManager`**: Default manager for all cooperative-scoped models. `get_queryset()` auto-filters `deleted_at__isnull=True`. `all_with_trashed()` returns unfiltered queryset. `trashed_only()` returns only deleted records.

**`CooperativeScopedModel`**: Abstract base with `cooperative` FK, `deleted_at`, `restored_at`, `deleted_via_cascade_from`, and `TenantManager`. All cooperative-data models inherit from this.

**`AuditLog`**: The append-only audit trail. `cooperative` FK is nullable (for superadmin actions that span cooperatives). `actor` FK to `User` is nullable (for system-initiated actions). `resource_type` is a CharField (not FK, avoids circular imports). `previous_value`/`new_value` are JSONFields for storing serializable state before/after writes. `save()` raises `ValueError` if updating an existing record : AuditLogs are insert-only.

**Indexes:** `BrinIndex` on `created_at` (efficient for time-range queries on append-only data), composite `Index(['cooperative', 'resource_type', 'resource_id', 'created_at'])` for filtered queries.

### `apps.auth_api.models`

**`User(AbstractBaseUser, PermissionsMixin, SoftDeletableModel)`**: Custom user model with `email` as `USERNAME_FIELD`. `REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']`. `delete()` raises `ValueError` for superusers (cannot be deleted), calls `soft_delete()` for regular users. `role` is nullable, farmers may not have a role string (they are identified via `farmer_profile`).

**`TwoFactorOTP`**: Stores 6-digit codes with purpose (LOGIN, PASSWORD_RESET, ACTION_CONFIRM, FARMER_LOGIN). `attempts` counter for brute-force protection. `expires_at` for time-boxed validity. Index `idx_otp_usr_purp_used_exp` covers the lookup pattern used in verification.

### `apps.cooperatives.models`

**`Cooperative`**: Not a `CooperativeScopedModel` ; it is the root of the tenant tree. `prefix` for member number generation (`DAIRY-2026-0001`). `last_member_sequence` for atomic member number increment. `payment_model` determines computation algorithm (FIXED_PRICE vs REVENUE_SHARE). `levy_percentage` and `monthly_fee` applied in payment engine. `minimum_payout_amount` for carry-forward threshold. `inventory` JSONField stores cooperative-level inventory configuration. Soft-delete cascades to 18 related model classes manually (not via Django's `on_delete=CASCADE` since Cooperative is not a `CooperativeScopedModel`).

### `apps.farmers.models`

**`Farmer(LocationMixin, CooperativeScopedModel)`**: `user` OneToOneField is nullable (farmer may not have a login account). `search_vector` for full-text search using PostgreSQL `tsvector` and `ts_rank`. `primary_membership` property returns the first active membership by `joined_at`. Indexes: GIN on `search_vector`, compound on `(cooperative, is_active, county)`, partial `idx_farmer_live_records` for `deleted_at__isnull=True`.

**`FarmerCooperativeMembership`**: Not a `CooperativeScopedModel` (it has explicit FKs). `unique_member_per_coop` constraint: `(farmer, cooperative)` is unique. `unique_member_per_coop` (cooperative, member_number) constraint: the same member number cannot be reassigned within a cooperative after the original member leaves. `soft_delete()`/`restore()` work on the membership, not the farmer, a farmer can leave one cooperative and remain active in another.

### `apps.deliveries.models`

**`Delivery(LocationMixin, CooperativeScopedModel)`**: `batch_id` is unique and auto-generated in `DeliverySyncSerializer.create()`. `local_id` for offline sync idempotency. `unique_delivery_local_id` partial constraint only applies when `local_id > ''`. `status` enum: PENDING → GRADED → ACCEPTED → REJECTED → PAID. Index `idx_del_pending_grader` partial index on PENDING deliveries for the grader's queue view.

### `apps.grading.models`

**`GradeImage`**: Not cooperative-scoped. Uploaded images are global. `upload_to='grades/%Y/%m/%d/'` organizes by upload date.

**`Grade(CooperativeScopedModel)`**: OneToOne to `Delivery`. `grade_letter` is nullable (rejected deliveries have no grade). `price_per_unit` is nullable (price is looked up from `GradePrice` effective on delivery date, the stored price is for reference and override). `is_overridden` flag for manager overrides. `is_inventory_updated` flag tracks whether `update_inventory_on_grade` completed.

**`GradePrice`**: Not cooperative-scoped, a grade price applies platform-wide. `unique_together: (grade_letter, effective_from)` ensures only one price per grade per effective date. Queries always order by `-effective_from` and take the first per grade.

**`FarmerGradeDispute`**: Not cooperative-scoped (inherits via `Grade`). `status` enum: PENDING → RESOLVED → REJECTED.

### `apps.inventory.models`

**`Inventory(CooperativeScopedModel)`**: Represents a bulk pool for `(cooperative, payment_cycle, product_type, grade)`. `unique_inventory_cycle_pool` constraint prevents duplicate pools. `running_balance` property computes `quantity_in - quantity_out`. When quantity_in drops to 0 or below, the record is deleted (not soft-deleted, inventory corrections use subtractive updates).

**`Stock(CooperativeScopedModel)`**: The fast aggregate for current sellable stock. `unique_stock_coop_product_grade` constraint. `low_stock_threshold` for alerts. Updated atomically in `update_inventory_on_grade` Celery task.

### `apps.sales.models`

**`Buyer(CooperativeScopedModel)`**: External entity (processors, exporters).

**`SaleInventoryLineItem`**: Links a sale to multiple inventory pools. `unique_together: (sale, inventory)` prevents double-linking. `quantity` is the amount drawn from that pool.

**`Sale(CooperativeScopedModel)`**: `total_amount` is `editable=False` ; computed as `quantity * price_per_unit` in `save()`. `line_items` relation provides the multi-pool breakdown. `invoice_number` is optional but must be unique per cooperative when non-empty.

### `apps.payment_engine.models`

**`PaymentCycle(CooperativeScopedModel)`**: Core financial record. `totals` JSONField stores `{total_quantity, total_gross, total_net, farmer_count}` after computation. `celery_task_id` links to the running Celery task. `status` state machine: DRAFT → COMPUTING → COMPUTED → LOCKED → DISBURSED. `locked_by`/`locked_at` record who locked the cycle. `has_warnings` boolean for UI indication.

**`FarmerPayment(CooperativeScopedModel)`**: One per `(cycle, farmer)`. `grade_breakdown` JSONField has two shapes (see 2.3). `deductions` JSONField has keys: `levy`, `monthly_fee`, `loan_repayment`, `input_credit`. `computation_log` JSONField is the forensic record. `is_on_hold` for payment holds (e.g., dispute in progress). `carried_forward_amount`/`carry_forward_reason` for minimum payout threshold carry-forward. `withholding_tax_amount` stored but not deducted from `net_amount`. `clean()` validates `grade_breakdown` shape, `deductions` keys, and `computation_log` keys.

**`ComputationWarning`**: Created during `run_payment_engine`. `delivery_id`/`farmer_id` for UI linking. `severity`: WARNING (can proceed) vs ERROR (blocks computation).

### `apps.deductions.models`

**`Deduction(CooperativeScopedModel)`**: `deduction_type` enum: LEVY, LOAN_REPAYMENT, INPUT_CREDIT. `cycle` FK for payment-cycle scoping. Levies are auto-generated by the payment engine; repayments and input credits are explicitly created.

**`FarmInputCredit(CooperativeScopedModel)`**: FIFO deduction order by `supplied_date`. `installment_amount` allows spreading over multiple cycles. `deducted_in_cycle` tracks which cycle fully or partially deducted it.

### `apps.loans.models`

**`Loan(CooperativeScopedModel)`**: `total_repayable` and `installment_amount` are computed in `save()` if not set. `status`: PENDING → ACTIVE → COMPLETED → DEFAULTED. `installments_paid` counter. `save()` auto-computes `total_repayable = principal * (1 + rate/100)` and `installment_amount = total_repayable / number_of_installments`.

**`LoanRepayment`**: Through table linking `Loan` to `FarmerPayment`. `unique_together: (loan, farmer_payment)` prevents double-recording.

**`LoanGuarantor(CooperativeScopedModel)`**: `unique_together: (loan, guarantor)`. A farmer cannot guarantee their own loan.

### `apps.disbursement.models`

**`DisbursementBatch(CooperativeScopedModel)`**: `status` state machine: PENDING → APPROVED → PROCESSING → COMPLETED/PARTIALLY_COMPLETED/FAILED. `command_id`: SalaryPayment, BusinessPayment, PromotionPayment (M-Pesa B2C CommandID values). `celery_task_id` for the processing task. `approved_by`/`approved_at` for two-step approval (accountant initiates, manager approves).

**`DisbursementTransaction(CooperativeScopedModel)`**: `unique_together: (conversation_id, transaction_id)` for idempotent callback handling. `conversation_id` is the UUID generated at creation; `transaction_id` is assigned by M-Pesa on success. `status`: PENDING → QUEUED → SENT → SUCCESS/FAILED/CANCELLED. `withholding_tax_amount` stored per transaction for KRA reporting. `retry_count` with max 3 for automatic retry cutoff.

### `apps.notifications.models`

**`Notification(CooperativeScopedModel)`**: `cooperative` is nullable (for farmer-specific notifications where cooperative context varies). `recipient` is nullable (for cooperative-wide broadcasts). `retry_count`/`max_retries` for SMS retry. `external_id` stores the Africa's Talking message ID. `channel`: SMS, USSD, EMAIL, IN_APP.

**`USSDSession`**: Not cooperative-scoped. `session_id` is Africa's Talking's session ID (unique per session). `current_menu` state machine. `farmer`/`membership` FKs for the authenticated context.

### `apps.legal.models`

**`LegalDocument`**: `publish_new()` method performs atomic publish: deactivate all existing docs of this slug, insert new active doc, write audit log, all in one transaction. `uniq_active_slug` partial constraint: only one `(slug, is_active=True)` at a time (database-level enforcement of single-active-version-per-slug).

**`LegalAcceptance`**: `unique_together: (user, document, version)` records which version was accepted. The middleware's subquery fix (document=OuterRef(pk) instead of document=OuterRef(pk) AND version=OuterRef(version)) means accepting a new version implicitly accepts all prior versions.

### `apps.analytics.models`

**`AnalyticsSnapshot`**: Materialized analytics per cooperative per period. `schema_version` for migration handling when analytics schema evolves. `data` JSONField stores denormalized computed values for fast retrieval.

**`MaterializedAnalytics`**: Global (not cooperative-scoped) monthly aggregates. `unique_together: (period_type, period_start)`.

**`AnalyticsExportTask`**: Async export job tracking. `celery_task_id` for status polling. `download_url` for completed exports. `expires_at` for TTL cleanup.

### `apps.chat.models`

**`ChatMessage`**: Stores chat history per session. `session_id` (UUID, indexed), `role` (user/assistant), `content` (text), `created_at` (auto_now_add). The `ChatView` uses this for session-based history retrieval alongside a `SYSTEM_PROMPT` that is a hardcoded 100+ line string describing the API, permissions matrix, and key workflows.

### `apps.statements.models` (referenced but not fully read)

---

## Chapter 5: API Design Reference

### 5.1 API Design Philosophy

The API follows REST conventions with Django DRF patterns:

**Resource naming:** Plural nouns for collections (`/farmers/`, `/deliveries/`). Nested resources for sub-collections (`/grades/delivery/{id}/`). Actions as POST on resources (`/payment-engine/cycles/{id}/run/`, `/disbursements/batches/{id}/approve/`).

**Permission pattern:** Every viewset's `get_permissions()` method returns a list of permission classes specific to each action. `CooperativeScopedViewSet` handles data scoping; permission classes handle authorization.

**Error format:** DRF's default error format, field-level errors as `{"field_name": ["error message"]}`, general errors as `{"detail": "error message"}`.

**Pagination:** `PageNumberPagination` with `PAGE_SIZE=20`. All list endpoints support `?page=` and `?page_size=`.

### 5.1a API Versioning Strategy

**Convention:** URL prefix versioning (`/api/v1/`, `/api/v2/`). Both the unversioned `/api/` prefix and the versioned `/api/v1/` prefix mount the same view functions — no HTTP redirects. The unversioned prefix is kept for backward compatibility with existing clients.

**Version bumping rules:**
- **Major version bump** (`/api/v2/`) = breaking change (removing fields, changing auth, altering response shapes)
- **Minor version bump** = new features, backward-compatible additions (new endpoints, new optional fields)

**Deprecation policy:** Old versions are supported for 6 months after a new major version is released. During the deprecation window, both versions are served simultaneously.

**Why URL aliasing, not HTTP redirects:** A 301/302 redirect changes the URL the client sees, which breaks any client that doesn't follow redirects on POST/PUT/PATCH requests. Many HTTP clients intentionally don't follow redirects on POST for security reasons — this is standard behavior, not a bug. URL aliasing avoids this entirely while still establishing the versioned path as the canonical URL for new integrations.

**External webhooks are permanently unversioned:** M-Pesa callback URLs (`/api/callback/mpesa/...`), Africa's Talking USSD callback (`/api/callback/ussd/`), and any future SMS delivery webhooks are configured once in third-party developer portals outside the codebase's control. These URLs cannot be changed without re-registering in the external portal, so they remain unversioned as a stable contract. This is a permanent architectural rule, not a one-off decision.

### 5.2 Authentication Architecture

**Staff login (email + password + 2FA):**

1. `POST /api/auth/login/` with `{"email": "...", "password": "..."}`. If `user.two_fa_enabled=True`, returns `{"requires_2fa": true, "login_token": "<signed-token>"}`.
2. `POST /api/auth/2fa/request/` with `{"login_token": "<signed-token>"}`. Server generates 6-digit OTP, sends via email (SMTP), returns `{"detail": "OTP sent..."}`. In DEBUG mode, `{"otp_code": "482916"}` is also returned.
3. `POST /api/auth/2fa/verify/` with `{"login_token": "...", "otp_code": "482916"}`. Server validates OTP is unused, not expired, attempts < 5. On success, returns JWT tokens + sets HTTP-only `refresh_token` cookie.
4. `POST /api/auth/refresh/` with `{"refresh": "<cookie-value>"}`. Returns new access token. If `ROTATE_REFRESH_TOKENS=True`, a new refresh token is also issued and the old one is blacklisted.

**Farmer login (phone + OTP via SMS):**

1. `POST /api/auth/farmer/request/` with `{"phone_number": "0712345678"}`. Server generates OTP, sends via Africa's Talking SMS, returns `{"login_token": "<signed-token>"}` with `{"otp_code": "..."}` in DEBUG.
2. `POST /api/auth/farmer/verify/` with `{"login_token": "...", "otp_code": "482916"}`. Server validates OTP and returns JWT tokens. If the farmer has no linked `User` record yet, one is created lazily at this point (the `User` is created with `set_unusable_password()`. the farmer must request a password reset to set a password).

**Google Sign-In (staff only):**

The admin login page loads Google Identity Services (`accounts.google.com/gsi/client`) and renders a "Sign in with Google" button using `VITE_GOOGLE_CLIENT_ID`. The flow:

1. User clicks the button and completes the Google OAuth consent screen in the popup.
2. Google returns a JWT `credential` to the `callback`.
3. Frontend POSTs `{ credential: "<google-jwt>" }` to `POST /api/auth/google/`.
4. `GoogleLoginSerializer` validates the JWT: verifies the signature against Google's public keys (`googleapis.com/oauth2/v3/certs`), checks `audience=GOOGLE_CLIENT_ID`, `issuer='https://accounts.google.com'`, and `email_verified=True`.
5. The serializer looks up the user by `email`. If found and active, it stores `google_sub` on the `User` record and returns JWT tokens. If no active account matches the email, it returns `400 Bad Request: No active account found with this email.`. Google Sign-In cannot create new accounts.
6. The `User.google_sub` field is unique — subsequent Google sign-ins for the same email reuse the same account without re-verification.

Only staff accounts (admin, manager, accountant, etc.) support Google Sign-In. The farmer portal uses phone + OTP only. A `User` must already exist with a matching email for Google Sign-In to succeed — Google login does not auto-register new accounts.

**Token lifecycle:** Access token TTL = 1 day. Refresh token TTL = 30 days. Refresh token rotation is enabled, each use issues a new refresh token and blacklists the old one. The `OutstandingToken` blacklist is stored in PostgreSQL (default) but Redis can be configured as the blacklist backend.

**`must_change_password` gate:** The `ForcePasswordChangeMiddleware` intercepts all authenticated requests (except safe paths: `/api/auth/change-password/`, `/api/auth/logout/`, `/api/auth/refresh/`, `/api/health/`, `/api/schema/`, `/api/docs/`) and returns `{"must_change_password": true, "detail": "..."}` with 403 if `user.must_change_password=True`.

**Legal acceptance gate:** The `LegalAcceptanceMiddleware` intercepts all authenticated requests (except `/api/legal/`, `/api/admin/`, `/api/auth/`, `/api/health/`, `/api/docs/`) and queries for active legal documents that require acceptance. If the user has not accepted all active required documents, returns `{"requires_legal_acceptance": true}` with 403.

### 5.3 Permission Architecture

**Role hierarchy:**
- `admin`: Cooperative admin, full CRUD on cooperative's own data. Admin role can set `cooperative_id` explicitly in serializers.
- `manager`: Cooperative manager, can lock/unlock cycles, approve disbursements, override grades.
- `accountant`: Financial operator, can run payment engine, initiate disbursements, manage deductions and loans.
- `grader`: Field operator, can create deliveries and grades.
- `farmer`: Self-service, can only access their own data (own farmer profile, own deliveries, own payments).
- `auditor`: Read-only internal auditor, can read all cooperative data.
- `external_auditor`: Filtered read-only, can only read financial actions and resources.

**Permission classes used:**

| Permission | Used by | What it checks |
|---|---|---|
| `IsAuthenticated` | All endpoints | JWT valid |
| `IsAdmin` | admin-only endpoints | role == 'admin' |
| `IsManager` | lock/unlock/approve | role == 'manager' |
| `IsAccountantOrManager` | payment engine actions | role in ('accountant', 'manager') |
| `IsManagerOrGrader` | grade create/update | role in ('manager', 'grader') |
| `IsFarmer` | farmer self-service | role == 'farmer' |
| `IsAnyAuditor` | reports | role in ('auditor', 'external_auditor', 'admin') |
| `IsExternalAuditor` | external audit log | role == 'external_auditor' |
| `IsAdminOrSuperUser` | legal documents | role=='admin' OR is_superuser |

### 5.4 Endpoint Reference

**`/api/auth/`**
- `POST /login/`: Staff email+password login. Returns 2FA challenge or JWT tokens.
- `POST /2fa/request/`: Request OTP for 2FA. Requires valid `login_token`.
- `POST /2fa/verify/`: Verify 2FA OTP. Returns JWT tokens.
- `POST /farmer/request/`: Farmer OTP request via SMS.
- `POST /farmer/verify/`: Farmer OTP verification. Returns JWT tokens.
- `POST /password/reset/request/`: Request password reset OTP.
- `POST /password/reset/verify/`: Verify reset OTP and set new password.
- `POST /logout/`: Blacklist refresh token, delete cookie.
- `POST /invite/request/`: Send invite OTP to new staff email.
- `POST /invite/verify/`: Verify invite OTP and set password + activate account.
- `POST /google/`: Google OAuth login (not fully wired).
- `POST /change-password/`: Change own password. Clears `must_change_password`.
- `POST /enable-2fa/`: Enable 2FA (requires password confirmation).
- `POST /disable-2fa/`: Disable 2FA (blocked for manager/accountant/auditor roles).
- `POST /refresh/`: Refresh access token.

**`/api/cooperatives/`**
- `GET /`: List cooperatives (admin only).
- `POST /`: Create cooperative (admin only).
- `GET /{id}/`: Cooperative detail.
- `PUT /{id}/`: Update cooperative (admin).
- `GET /me/`: Current user's cooperative.

**`/api/farmers/`**
- `GET /`: List farmers (scoped to cooperative). Search by name/member number.
- `POST /`: Create farmer (auto-generates member number, creates User with OTP-only login).
- `GET /{id}/`: Farmer detail with membership info.
- `PUT /{id}/`: Update farmer.
- `DELETE /{id}/`: Soft-delete farmer.
- `POST /import/`: Bulk CSV import.
- `GET /{id}/summary`: Farmer summary (deliveries, payments, loans).

**`/api/deliveries/`**
- `GET /`: List deliveries with filtering (date range, status, product type, shift, route).
- `POST /`: Record delivery.
- `POST /sync/`: Bulk sync from offline PWA. Returns 201 or 409 on duplicate `local_id`.
- `GET /map/`: Deliveries with GPS for map display.
- `GET /summary/`: Aggregated counts by product type and status.
- `GET /batches/`: Batch list with aggregated quantities.
- `GET /batches/?batch_id=`: Single batch details.

**`/api/grades/`**
- `GET /`: List grades with filtering by letter, date, delivery.
- `POST /`: Grade a delivery (Grader only). Triggers `update_inventory_on_grade` task.
- `PUT /{id}/`: Update grade.
- `DELETE /{id}/`: Delete grade (reverse inventory updates).
- `POST /{id}/override/`: Manager override with reason (manager only).
- `POST /{id}/dispute/`: Farmer raises dispute.
- `GET /prices/`: List/create grade prices (admin for create).
- `GET /delivery/{id}/`: Get grade for specific delivery.
- `GET /{id}/images/`: Get grade images.
- `POST /{id}/images/`: Upload grade image.

**`/api/inventory/`**
- `GET /`: List inventory pools (cycle × product × grade).
- `GET /summary/`: Aggregated stock by product and grade.
- `GET /batch/{id}/`: Single batch details.
- `GET /alerts/`: Low stock alerts.

**`/api/sales/`**
- `GET /`: List sales with filtering by date, buyer, status.
- `POST /`: Record sale. Selects from available inventory pools.
- `GET /{id}/`: Sale detail with line items.

**`/api/payment-engine/`** (PaymentCycleViewSet + FarmerPaymentViewSet)
- `GET /`: List payment cycles.
- `POST /`: Create payment cycle (DRAFT).
- `GET /{id}/`: Cycle detail.
- `POST /{id}/run/`: Trigger `run_payment_engine` Celery task.
- `GET /{id}/preview/`: Preview computed farmer payments.
- `GET /{id}/status/`: Cycle status, celery task state, warnings.
- `POST /{id}/lock/`: Lock cycle (Manager only).
- `POST /{id}/unlock/`: Unlock cycle (Manager only).
- `POST /{id}/hold/`: Hold individual farmer payment.
- `POST /{id}/release/`: Release held payment.
- `GET /{id}/export/`: CSV export of farmer payments.
- `GET /farmer-payments/`: List farmer payments with filtering by cycle, status, farmer.
- `GET /farmer-payments/?export=csv`: CSV export (throttled, accountant/manager only).

**`/api/deductions/`**
- `GET /`: List deductions.
- `POST /`: Create deduction.
- `GET /farmer/{farmer_id}/cycle/{cycle_id}/`: Farmer's deductions for a cycle.
- `DELETE /{id}/`: Remove deduction.

**`/api/loans/`**
- `GET /`: List loans.
- `POST /`: Create loan.
- `GET /{id}/`: Loan detail with guarantors and repayments.
- `PUT /{id}/`: Update loan.
- `POST /{id}/approve/`: Approve loan.
- `POST /{id}/disburse/`: Disburse loan amount.
- `POST /{id}/add-guarantor/`: Add guarantor.
- `DELETE /{id}/guarantor/{gid}/`: Remove guarantor.

**`/api/disbursements/`** (DisbursementViewSet)
- `GET /`: List disbursement batches.
- `POST /initiate/`: Create batch from LOCKED cycle. Generates transactions for eligible farmers.
- `GET /{id}/`: Batch detail with transactions.
- `POST /{id}/approve/`: Approve batch (Manager only). Two-step: accountant initiates, manager approves.
- `POST /{id}/live/`: Send to M-Pesa (triggers `process_batch_disbursements` task).
- `POST /{id}/reject/`: Reject PENDING batch.
- `POST /{id}/retry_failed/`: Retry failed M-Pesa transactions. Triggers `retry_batch_disbursements` Celery task. Safe retry: queries M-Pesa `TransactionStatusQuery` for each failed transaction first — if it already succeeded (ResultCode='0') it is marked SUCCESS without re-sending. Otherwise, generates a fresh `conversation_id` and re-sends via `send_single_mpesa_disbursement`.
- `GET /{id}/csv/`: Export bank transactions as CSV (equity, kcb, or generic format).
- `POST /{id}/confirm_manual/`: Mark bank/cash transactions as manually confirmed.
- `GET /{id}/transactions/`: Paginated list of transactions with filtering.

**`/api/notifications/`**
- `GET /`: List notifications.
- `GET /{id}/`: Notification detail.

**`/api/routes/`** (Cooperative-scoped)
- `GET /routes/`: List routes (filterable by is_active, day_of_week).
- `POST /routes/`: Create route (Manager only).
- `GET /routes/{id}/`: Route detail.
- `PUT/PATCH /routes/{id}/`: Update route (Manager only).
- `DELETE /routes/{id}/`: Delete route (Manager only).
- `GET /routes/{id}/map/`: Route map data (ordered stops + farmers for display).
- `POST /routes/{id}/assign-stops/`: Assign/replace stops on a route (Manager only).
- `POST /routes/{id}/assign-farmer/`: Assign farmer to a stop (Manager or Grader).
- `POST /routes/{id}/unassign-farmer/`: Unassign farmer from a stop (Manager or Grader).
- `GET /routes/route/`: OpenRouteService (ORS) proxy for geocoding/routing.

**`/api/statements/`**
- `GET /statement/`: Generate farmer payment statement PDF (requires `farmer_payment_id` query param).
- `GET /statement/latest/`: Latest paid statement PDF (farmer only).
- `GET /statement/history/`: Farmer's payment history JSON.
- `GET /report/`: Seasonal cooperative report PDF (requires `cycle_id`).
- `GET /kra-report/`: KRA withholding tax report PDF (requires `year`).
- `GET /annual-report/`: Annual financial report JSON (audit/fiscal year).
- `GET /audit/`: Audit log (paginated, manager/auditor).
- `GET /external-audit/`: External auditor filtered audit log.

**`/api/legal/`**
- `GET /`: List legal documents.
- `POST /`: Create/publish legal document.
- `GET /acceptances/`: List acceptances.
- `POST /accept/`: Accept a legal document.
- `GET /me/pending/`: User's pending acceptances.

**`/api/analytics/`** (role-scoped: farmer sees own stats; staff sees cooperative; admin sees cross-cooperative via `/api/admin/analytics/`)
- `GET /dashboard/`: Analytics dashboard for current cooperative.
- `GET /farmers/`: Farmer analytics.
- `GET /disbursements/`: Disbursement analytics.
- `GET /financial/`: Financial analytics.
- `GET /farmer-retention/`: Farmer retention metrics.
- `GET /seasonal-patterns/`: Seasonal produce patterns.
- `GET /production/`: Cooperative production analytics.
- `GET /operations/`: Cooperative operations analytics.
- `GET /sales/`: Cooperative sales analytics.
- `GET /loans/`: Cooperative loan analytics.
- `GET /payment-efficiency/`: Payment efficiency metrics.
- `GET /export/`: Export analytics as CSV (throttled, accountant/manager only).

**`/api/chat/`**
- `POST /`: Send message to AI chatbot (Gemini). Creates `ChatMessage` records for history.
- `GET /?session_id=`: Retrieve chat history for a session.

**`/api/notifications/`**
- `GET /`: List notifications (scoped to cooperative).
- `GET /{id}/`: Notification detail.

**`/api/admin/`** (Superadmin only, IP-restricted)

*Superuser & user management:*
- `POST /users/create-superuser/`: Create superuser
- `GET /users/`: List all users (filterable by role, cooperative, is_active, include_trashed)
- `POST /users/`: Create user
- `GET /users/{id}/`: User detail
- `PUT/PATCH /users/{id}/`: Update user
- `DELETE /users/{id}/`: Soft-delete user
- `POST /users/{id}/activate/`: Activate user
- `POST /users/{id}/deactivate/`: Deactivate user
- `POST /users/{id}/reset-password/`: Reset password (sends email)
- `POST /users/{id}/toggle-2fa/`: Toggle 2FA
- `POST /users/{id}/delete/`: Soft-delete (separate from deactivate)
- `POST /users/{id}/restore/`: Restore soft-deleted user
- `POST /users/{id}/force-logout/`: Blacklist all user tokens
- `POST /users/bulk-action/`: Bulk activate/deactivate
- `POST /impersonate/{user_id}/`: Impersonate user (15-min JWT access token)

*Cooperative management:*
- `GET /cooperatives/`: List all cooperatives (filterable)
- `POST /cooperatives/`: Create cooperative
- `GET /cooperatives/{id}/`: Cooperative detail
- `PUT/PATCH /cooperatives/{id}/`: Update cooperative
- `DELETE /cooperatives/{id}/`: Soft-delete
- `POST /cooperatives/{id}/activate/`: Activate cooperative
- `POST /cooperatives/{id}/deactivate/`: Deactivate (optionally deactivates users)
- `POST /cooperatives/{id}/restore/`: Restore
- `POST /cooperatives/bulk-action/`: Bulk activate/deactivate

*Farmer management (cross-cooperative):*
- `GET /farmers/`: List all farmers (filterable by cooperative, is_active)
- `POST /farmers/`: Create farmer
- `GET /farmers/{id}/`: Farmer detail
- `PUT/PATCH /farmers/{id}/`: Update farmer
- `POST /farmers/{id}/activate/`: Activate farmer
- `POST /farmers/{id}/deactivate/`: Deactivate farmer
- `POST /farmers/{id}/delete/`: Soft-delete farmer
- `POST /farmers/{id}/restore/`: Restore farmer
- `POST /farmers/bulk-action/`: Bulk activate/deactivate

*Delivery management:*
- `GET /deliveries/`: List all deliveries (filterable)
- `POST /deliveries/`: Create delivery
- `GET /deliveries/{id}/`: Delivery detail
- `POST /deliveries/{id}/force-status/`: Force delivery status (superuser override)
- `POST /deliveries/{id}/assign-grade/`: Assign grade directly to delivery (superuser override)
- `POST /deliveries/{id}/restore/`: Restore soft-deleted delivery
- `POST /deliveries/{id}/purge/`: Hard-delete (only if not graded)

*Payment cycle management:*
- `GET /payment-cycles/`: List all cycles (filterable by status, cooperative)
- `POST /payment-cycles/`: Create cycle
- `GET /payment-cycles/{id}/`: Cycle detail
- `POST /payment-cycles/{id}/lock/`: Lock cycle
- `POST /payment-cycles/{id}/unlock/`: Unlock cycle
- `POST /payment-cycles/{id}/restore/`: Restore
- `POST /payment-cycles/{id}/purge/`: Hard-delete (only if no farmer payments)

*Disbursement management:*
- `GET /disbursement-batches/`: List all batches
- `GET /disbursement-batches/{id}/`: Batch detail
- `POST /disbursement-batches/{id}/approve/`: Approve batch (PROCESSING)
- `POST /disbursement-batches/{id}/reject/`: Reject batch

*Farmer payment management:*
- `GET /farmer-payments/`: List all farmer payments (filterable by cycle, status)
- `GET /farmer-payments/{id}/`: Payment detail
- `POST /farmer-payments/{id}/hold/`: Place payment on hold
- `POST /farmer-payments/{id}/unhold/`: Release hold

*Loan management:*
- `GET /loans/`: List all loans (filterable)
- `GET /loans/{id}/`: Loan detail
- `POST /loans/{id}/approve/`: Approve loan
- `POST /loans/{id}/reject/`: Reject loan
- `POST /loans/{id}/mark-defaulted/`: Mark defaulted
- `POST /loans/{id}/mark-completed/`: Mark completed
- `POST /loans/{id}/restore/`: Restore
- `POST /loans/{id}/purge/`: Hard-delete

*OTP token management:*
- `GET /otp-tokens/`: List OTP tokens (filterable by user, purpose, is_used)
- `POST /otp-tokens/{user_id}/invalidate-all/`: Invalidate all unused OTPs for user

*Invite management:*
- `POST /auth/invite/`: Send invite to new staff (creates pending user + OTP)
- `GET /auth/invites/`: List invites (filterable by status, role, email)
- `GET /auth/invites/{id}/`: Invite detail
- `POST /auth/invite/{id}/revoke/`: Revoke invite
- `POST /auth/invite/{id}/resend/`: Resend invite OTP

*Trash bin:*
- `GET /bin/`: Summary count of all soft-deleted records
- `GET /bin/users/`: List soft-deleted users
- `GET /bin/cooperatives/`: List soft-deleted cooperatives
- `GET /bin/farmers/`: List soft-deleted farmers
- `GET /bin/deliveries/`: List soft-deleted deliveries
- `GET /bin/loans/`: List soft-deleted loans
- `GET /bin/payment-cycles/`: List soft-deleted cycles

*Legal admin (platform-wide):*
- `GET/PUT/PATCH/DELETE /legal/documents/`: CRUD legal documents
- `POST /legal/documents/{id}/publish/`: Publish new version (atomic)
- `POST /legal/documents/{id}/deactivate/`: Deactivate document
- `GET /legal/acceptances/`: List all acceptances
- `GET /legal/compliance/`: Compliance report
- `GET /legal/recent-activity/`: Recent legal activity

*Platform analytics (11 endpoints, all throttled):*
- `GET /analytics/dashboard/`: Global dashboard
- `GET /analytics/production/`: Production analytics
- `GET /analytics/financial/`: Financial analytics
- `GET /analytics/farmers/`: Farmer analytics
- `GET /analytics/sales/`: Sales analytics
- `GET /analytics/loans/`: Loan analytics
- `GET /analytics/operations/`: Operations analytics
- `GET /analytics/disbursements/`: Disbursement analytics
- `GET /analytics/seasonal/`: Seasonal patterns
- `GET /analytics/payment-efficiency/`: Payment efficiency
- `GET /analytics/farmer-retention/`: Farmer retention
- `GET /analytics/leaderboard/`: Cross-cooperative leaderboard (top farmers by volume/payout, top buyers)

*Observability:*
- `GET /health/`: DB, Redis, Celery, email health check
- `GET /migration-health/`: Unapplied migration check
- `GET /celery/tasks/`: Active/reserved/scheduled/failed task inspection
- `POST /auth/revoke-all-sessions/`: Revoke own all refresh tokens

---

## Chapter 6: The Payment Engine - Deep Dive

### The 10-Step Bulk Computation Algorithm

The `run_payment_engine` Celery task implements these steps:

1. **Acquire Redis distributed lock** on `payment_engine:lock:{cycle_id}` with 30-minute TTL. If another worker holds the lock, skip. If Redis is unavailable, proceed without lock.

2. **Transition cycle to COMPUTING.** Set `celery_task_id` and `status='COMPUTING'`. Delete existing `FarmerPayment` and `ComputationWarning` records for this cycle (computation is idempotent, running it again replaces prior results). Delete existing `Deduction` records of type `LOAN_REPAYMENT` and `INPUT_CREDIT` for this cycle.

3. **Call the computation function** based on `payment_model`:
   - `FIXED_PRICE` → `compute_fixed_price(cycle)`
   - `REVENUE_SHARE` → `compute_revenue_share(cycle)`

4. **Handle zero-delivery farmers.** After the main computation, find active farmers with no deliveries this cycle and add them with `total_quantity=0`, `gross_amount=0`, `grade_breakdown={}`.

5. **Batch-fetch carry-forward entries.** Query all `FarmerPayment` records for these farmers with `carry_forward_reason='BELOW_MINIMUM_THRESHOLD'` and `payment_status='PENDING'` from prior cycles. Build `carry_forward_entries[farmer_id] = [payments...]` dictionary.

6. **Batch-fetch undeducted farm input credits.** Query all `FarmInputCredit` with `deducted_in_cycle__isnull=True` and `status='ACTIVE'`. Build `credits_by_farmer[farmer_id] = [credits...]` dictionary.

7. **Batch-compute withholding taxes.** Call `compute_withholding_taxes(farmer_ids, cycle)` ; 2 queries total (one for current cycle net amounts, one for cumulative prior DISBURSED cycle amounts). Returns `dict[farmer_id] = (tax_amount, is_subject)`.

8. **Iterate farmers with chunked DB flushes every 500.** For each farmer:
   - Compute gross (with carry-forward from prior cycles)
   - Call `_compute_deductions()` to get `DeductionBreakdown`, `net_amount`, and `PendingDeductions` objects
   - Set withholding tax
   - Build `FarmerPayment` with `grade_breakdown`, `deductions`, `computation_log`
   - Accumulate totals
   - When `idx % 500 == 0`, flush to DB: `bulk_create(farmer_payments)`, `bulk_create(loan_repayment deductions + loan_repayment records + loan updates)`, `bulk_create(input_credit deductions + credit updates)`, `bulk_create(levy deductions)`, save carry-forward resolutions



9. **Update cycle totals and transition to COMPUTED.** Compute aggregates from DB, update `PaymentCycle.totals`, `total_levy`, `total_cooperative_fee`, `total_loan_repayments`, `total_input_credits`, `status='COMPUTED'`, `computed_at`.

### Grade Price Snapshot Approach (Fixed Price)

The `compute_fixed_price` function:

1. Warns for deliveries with `status=GRADED/ACCEPTED` but no `grade_record`: these are skipped.
2. Queries all `GradePrice` records with `effective_from__lte=cycle.end_date`, ordered by `(grade_letter, -effective_from)`, builds a `price_map`: first occurrence per grade is the effective price.
3. Aggregates deliveries by `(farmer_id, grade_letter)` with a single `Sum(quantity_kg) + Sum(volume_litres)` annotation.
4. For each aggregated row, looks up `price_map[grade]` and computes `amount = kg * price`.

**Why pre-built dictionaries instead of per-farmer queries:** Query 1 (prices) + Query 2 (aggregated deliveries) + Query 3 (bulk farmer fetch) = 3 queries total regardless of farmer count. Without aggregation, each farmer would require a separate price lookup and quantity sum, producing N+1 query patterns.

### Revenue Share Computation

The `compute_revenue_share` function:

1. Same delivery aggregation as fixed price.
2. All completed `Sale` records in the cycle date range (both linked and unlinked: sales not yet assigned to a cycle are included automatically).
3. Builds `total_revenue_map[product_type] = sum(sale.total_amount)`.
4. For each farmer, `gross = (farmer_kg / total_kg) * total_revenue`. If `revenue_share_by_produce_type` is True, splits revenue proportionally by produce type.
5. Single-farmer edge case: emits an INFO warning because they receive 100% of revenue.

### The `_compute_deductions` Function

This is pure computation, no DB writes. It receives the partially-built `FarmerPayment`, `cooperative`, `active_farmer_count`, `cycle`, and `undeducted_credits` list.

**Steps:**
1. `levy = gross * (levy_percentage / 100)`
2. `monthly_fee_share = monthly_fee / active_farmer_count` (equal split among all active farmers)
3. Find active loan (first with `status=ACTIVE` and `installments_paid < number_of_installments`). Set `loan_repayment = installment_amount`. Build `PendingDeductions` with `LoanRepayment` record and loan update.
4. Process farm input credits in FIFO order (sorted by `supplied_date`). For each credit, deduct up to `installment_amount` or remaining credit balance. Track remaining budget (`gross - levy - monthly_fee_share - loan_repayment`) as the ceiling.
5. Return `(DeductionBreakdown, net_amount, PendingDeductions)`.

### Withholding Tax Computation

The Kenyan KRA threshold is KES 24,000 per fiscal year (July 1 to June 30). The `compute_withholding_taxes` batch function:

1. Determines FY boundaries: if today < July 1, FY starts previous July 1.
2. Query 1: `current_nets = {farmer_id: net_amount}` for this cycle (status=DISBURSED).
3. Query 2: `cumulative_nets = {farmer_id: sum(net_amount)}` for prior DISBURSED cycles within FY.
4. For each farmer: if `cumulative < threshold`, tax = 5% × `max(0, cumulative + current - threshold)`. If `cumulative >= threshold`, tax = 5% × `current`. Store `(tax, is_subject)` in result dict.

### State Machine

```
DRAFT ──→ COMPUTING ──→ COMPUTED ──→ LOCKED ──→ DISBURSED
                │                                        │
                └──── (error) ──── back to DRAFT ◄──────┘
```

- `DRAFT → COMPUTING`: When `run_payment_engine.delay()` is called. The task ID is stored in `celery_task_id`.
- `COMPUTING → COMPUTED`: When the task finishes successfully. `computed_at` is set.
- `COMPUTING → DRAFT`: When the task raises an exception. The cycle is reset to DRAFT so it can be retried.
- `COMPUTED → LOCKED`: When a manager calls `POST /{id}/lock/`. `locked_by` and `locked_at` are recorded.
- `LOCKED → COMPUTED`: When a manager calls `POST /{id}/unlock/`. Only possible from LOCKED.
- `LOCKED → DISBURSED`: When all disbursement transactions in all batches reach terminal state (SUCCESS/FAILED/CANCELLED). Set by `update_batch_summary` task.



### Carry-Forward Minimum Payout

When a farmer's `net_amount < cooperative.minimum_payout_amount`:
1. `carried_forward_amount = net_amount` (the entire amount is carried)
2. `carry_forward_reason = 'BELOW_MINIMUM_THRESHOLD'`
3. The farmer receives KES 0 in this cycle
4. In a future cycle, when the farmer earns enough to exceed the threshold, `carried_forward_amount` is added to `gross_amount` before deductions

The `carry_forward_entries` batch query retrieves all prior cycles' carry-forward amounts so they can be resolved (marked `carry_forward_reason='RESOLVED'`) when the farmer finally earns above the threshold.

### Warnings Emitted

The `ComputationWarning` model records:
- Deliveries graded but missing Grade record
- Deliveries graded but no payment cycle exists for the delivery date
- Unit mismatches between inventory pools and deliveries
- Single farmer in a revenue share cycle (100% revenue share warning)
- No deliveries found for the cycle period
- No completed sales found (revenue share mode)

---

## Chapter 7: The Disbursement Pipeline Deep Dive

### M-Pesa Daraja B2C Integration

**Authentication:** `get_oauth_token()` uses consumer key/secret to obtain a bearer token. Tokens are cached in the client instance with `expires_in - 60` seconds buffer.

**Security Credential:** Built using the M-Pesa public certificate (`mpesa_public_cert.cer`). The initiator password is encrypted with RSA OAEP (SHA256) and base64-encoded. The certificate path is configured via `MPESA_PUBLIC_CERT_PATH`.

**B2C Payment Request:**
```python
payload = {
    'OriginatorConversationID': conversation_id,  # UUID generated at transaction creation
    'InitiatorName': initiator_name,
    'SecurityCredential': encrypted_password,
    'CommandID': command_id,  # SalaryPayment, BusinessPayment, PromotionPayment
    'Amount': int(amount),
    'PartyA': shortcode,
    'PartyB': phone_number,  # 254XXXXXXXXX
    'Remarks': f'Coop payment batch {batch_id[:8]}',
    'QueueTimeOutURL': settings.MPESA_B2C_TIMEOUT_URL,
    'ResultURL': settings.MPESA_B2C_RESULT_URL,
    'Occasion': farmer_name[:100],
}
```

**Conversation ID idempotency:** `conversation_id = str(txn.id)` ; the `DisbursementTransaction` UUID. Daraja echoes this back as `OriginatorConversationID` in the callback, allowing the callback handler to find the transaction by UUID even if `transaction_id` is not yet assigned.

### Rate Limiting

`process_batch_disbursements` tasks processes transactions in `CHUNK_SIZE=50` with `CHUNK_DELAY=30` seconds between chunks. This is implemented via:

```python
for t in chunk:
    send_single_mpesa_disbursement.delay(...)
    processed_count += 1

update_batch_summary.apply_async(args=[str(batch.id)], countdown=CHUNK_DELAY)
```

This is not a true API rate limit : Celery Beat controls dispatch timing. The 30-second delay between chunks means a batch of 500 transactions takes approximately 6 minutes to fully dispatch, even if the worker could handle them faster.

### Callback Handling

**Result callback (`mpesa_result_callback`):**

1. Validates IP whitelist (`MPESA_CALLBACK_IP_WHITELIST`)
2. Verifies M-Pesa signature using public certificate (if certificate is available)
3. Verifies HMAC if `MPESA_CALLBACK_HMAC_SECRET` is set
4. Parses payload, extracts `ConversationID` and `TransactionID`
5. Finds `DisbursementTransaction` by `conversation_id` (or `transaction_id` as fallback)
6. On success (`ResultCode='0'`): marks `SUCCESS`, updates `transaction_id` from `ResultParameters.TransactionReceipt`, triggers `update_batch_summary`, sends SMS confirmation
7. On failure: marks `FAILED`, sets `failure_reason`, triggers `reverse_deductions_on_failure`, triggers `update_batch_summary`

**Timeout callback (`mpesa_timeout_callback`):**

Handles the case where Daraja could not deliver the request (user cancelled, timeout). Marks all transactions for that `conversation_id` as `FAILED` with the timeout reason, triggers `reverse_deductions_on_failure`.

### Reconciliation Task (`reconcile_stuck_transactions`)

Runs every 15 minutes via Celery Beat. Finds transactions in `QUEUED` or `SENT` status that have been stuck for > 10 minutes. For each:

1. Queries Daraja `TransactionStatusQuery` API using the `conversation_id`
2. If `ResultCode='0'`: marks `SUCCESS`
3. Otherwise: marks `FAILED` with the result description
4. Triggers `update_batch_summary`
5. Sends SMS confirmation on success

### Retry Failed Transactions (`retry_batch_disbursements`)

Triggered by `POST /{id}/retry_failed/`. Handles M-Pesa disbursements that failed (timeout, user cancellation, or API error). 

**Safe retry design**: before re-sending, it queries M-Pesa's `TransactionStatusQuery` API to check if the payment actually succeeded — this prevents double-payment on timeout cases where the money was deducted but the callback never arrived.

**Flow:**
1. Fetch all `FAILED` transactions for the batch (M-Pesa method only)
2. For each: query `TransactionStatusQuery` using existing `conversation_id`
   - If `ResultCode='0'` → payment actually succeeded; mark `SUCCESS`, update `FarmerPayment.payment_status='PAID'`, skip re-send
   - On query error or non-success → proceed to step 3
3. Generate a **new** `conversation_id` (UUID) for each transaction — the old one may still be in-flight or rejected by M-Pesa's idempotency check
4. Reset txn to `PENDING` with fresh `conversation_id`
5. Enqueue `send_single_mpesa_disbursement` with the new conversation_id
6. Batch status set back to `PROCESSING`

**Why a new conversation_id?** M-Pesa's B2C API uses `OriginatorConversationID` as an idempotency key. If the original request is still in-flight when a retry is sent with the same ID, M-Pesa may reject it. Fresh UUID per retry ensures each M-Pesa API call is treated as independent.

### Blackout Window

`validate_disbursement_window()` checks if current EAT time is between `MPESA_DISBURSEMENT_BLACKOUT_START` (default '01:00') and `MPESA_DISBURSEMENT_BLACKOUT_END` (default '04:00'). If in blackout, raises `RuntimeError` ; the `process_batch_disbursements` task catches this and returns early without processing.

### Pre-flight Balance Check

Before sending any B2C requests, `process_batch_disbursements` calls `MpesaDarajaClient.check_balance()` which queries the Daraja `AccountBalance` API. If the cooperative's available M-Pesa float is less than the total batch amount, the batch is **aborted immediately**:

1. All pending M-PESA transactions are marked `FAILED` with reason `Insufficient float balance. Required: X, Available: Y`
2. Each affected `FarmerPayment` is marked `FAILED`
3. `reverse_deductions_on_failure` is triggered for each failed farmer payment
4. `update_batch_summary` recalculates the batch status (typically to `FAILED`)

This prevents the cooperative from submitting a batch that will partially or fully fail due to insufficient float — avoiding wasted API calls and unnecessary farmer payment reversals. If the balance query itself fails (network error), the check is skipped and processing proceeds normally (with a warning logged).

### Bank CSV Export Formats

The `csv` action supports three bank formats via `?bank=equity|kcb|generic`:

**Equity Bank:**
```
Account Number | Amount | Beneficiary | Narration
```

**KCB:**
```
Account Name | Account Number | Amount | Transaction Code
```

**Generic:**
```
AccountNumber | BeneficiaryName | Amount | Narration
```

The narration is `f'Coop payment {batch_id!s:.8}'` ; truncated to 8 characters of the UUID.

### Two-Step Approval

1. **Accountant** calls `POST /disbursements/initiate/`. Creates `DisbursementBatch` in `PENDING` status. `DisbursementTransaction` records are created for each eligible farmer payment.
2. **Manager** calls `POST /disbursements/{id}/approve/`. Sets `status=APPROVED`, `approved_by`, `approved_at`.
3. **Accountant or Manager** calls `POST /disbursements/{id}/live/`. Triggers `process_batch_disbursements` Celery task. Sets `status=PROCESSING`.

### Deduction Reversal on Failure

When a transaction fails (after M-Pesa callback with error, or timeout), `reverse_deductions_on_failure` runs:
1. Deletes `LoanRepayment` record linking the loan to this farmer payment
2. Decrements `Loan.installments_paid` (using `Greatest(installments_paid - 1, 0)` to prevent negative)
3. Sets `Loan.status='ACTIVE'` (the loan is re-activated)
4. The `Deduction` records for `LOAN_REPAYMENT` and `INPUT_CREDIT` are deleted by the payment engine before recomputation, so the next run of the engine will re-deduct them correctly.

---

## Chapter 8: Frontend Architecture 

### 8.1 The Two-SPA Architecture

The `vite.config.js` defines two entry points:
```javascript
input: {
  main: 'index.html',    // Admin/manager/accountant/auditor SPA
  farmer: 'farmer/index.html',  // Farmer portal SPA
}
```

Both apps live in the same repo under `client/` with separate Vite entry points (`farmer/index.html` and the admin dashboard). The farmer portal builds to `assets/farmer-[hash].js` and the admin dashboard to `assets/main-[hash].js`. Shared code lives in `client/src/shared/` — components like `FloatingAccessibilityWidget`, `ToastProvider`, and utility functions.

**Why separate SPAs:**
- **Bundle size constraints:** Farmers access the portal on low-end Android devices with slow connections. The admin dashboard's Recharts/charting dependencies should not be shipped to farmers. Separate Vite entry points (`farmer/` and `admin/`) produce independent bundles so farmers download only what they need.
- **Different auth policies:** The farmer portal uses JWT in `localStorage` with a simpler `FarmerAuthProvider`, while the admin dashboard uses session-based auth via Django's auth system. Separate apps make cookie policy, session lifetime, and token refresh boundaries cleaner to enforce without cross-contamination.
- **Security blast radius:** A vulnerability in the farmer portal (e.g. an XSS in the grader interface) should not automatically grant access to the admin dashboard. Separate Vite entry points and deploy artifacts provide a real security boundary — a compromise of the farmer bundle does not expose admin credentials or API sessions.

**What is shared:** `FloatingAccessibilityWidget` (accessibility controls), `Toast` notification system, `apiFetch` utility, authentication context pattern.

**What is duplicated:** React Router setup, Axios instance configuration, role-based routing guards.

### 8.2 Role-Based Routing

**Farmer portal** (`farmer/App.jsx`):
- `ProtectedRoute` checks `localStorage.getItem('zao_farmer_token')`
- `FarmerAuthContext` stores the authenticated user and token
- Legal acceptance gate: handled server-side by `LegalAcceptanceMiddleware` ; the server returns `403 {"requires_legal_acceptance": true}`, and the frontend must redirect to the legal acceptance flow
- `must_change_password` gate: server returns `403 {"must_change_password": true}`, frontend redirects to change-password page

**Admin dashboard** (`App.jsx`):
- Role-based rendering in `AppBar.jsx` ; different nav items for different roles
- The `admin/pages/Login.jsx` handles staff email/password/2FA login
- Axios interceptor handles 401 (redirect to login) and 403 (handle `must_change_password` and `requires_legal_acceptance`)

**Token refresh in Axios interceptor:**
```javascript
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Attempt token refresh
      const refreshed = await refreshToken()

      if (refreshed) {
        // Retry original request
        error.config.headers.Authorization = `Bearer ${getAccessToken()}`
        return axios(error.config)
      }
      // Logout
    }
    return Promise.reject(error)
  }
)
```

### 8.3 Component Library

**`client/src/shared/components/`:**
- `FloatingAccessibilityWidget`: Accessibility panel (font size, high contrast, motion reduction). Wraps the app via `createPortal` to `document.body`.

**`client/src/farmer/components/`:**
- `BottomNav`: Fixed bottom tab bar with 5 tabs (Dashboard, Deliveries, Payments, Grades, Profile)
- `FarmerAppBar`: Fixed top app bar with cooperative name, notification bell, settings icon
- `Toast`: Notification toast system
- `DeliveryCard`, `PaymentCard`, `GradeCard` : Mobile-optimized card components for list views

**`client/src/admin/components/`:** Sidebar, header, data tables with sorting/filtering, Recharts chart wrappers.

### 8.4 API Integration Pattern

All API calls go through `apiFetch` ; a thin wrapper around `fetch` or Axios that:
1. Attaches the JWT access token from memory (not localStorage: the token is stored in React context state)
2. Handles `401` by attempting a token refresh
3. Returns parsed JSON or throws an error with the response body

Loading states are managed locally in each page component using `useState`/`useEffect`. React Query is **not used** ; all data fetching is manual `useEffect` on mount with dependency arrays for refetching.

### 8.5 Role Dashboard Reference

**Farmer portal (`/farmer/*`)** : Mobile-first PWA with bottom tab navigation:
- `dashboard`: Summary: last delivery, last payment, active loans
- `deliveries`: Paginated delivery history with grade breakdown
- `payments`: Payment history with downloadable PDF statements
- `grades`: Grade history with dispute capability
- `loans`: Active loans with guarantor info
- `profile`: Personal info, payment method, cooperative membership
- `chat`: Gemini AI chatbot for Q&A
- `settings`: Language, notification preferences
- `notifications`: In-app notification list

**Admin dashboard (`/admin/*`)** : Superuser platform management (27 routes):
- Dashboard, Ledger, Produce Receipts, Inventory, Logistics, Financials, Settings, Support, User Management, Audit Trail, Trash Management, Health Monitor, Cooperatives, Loans, Farmer Payments, OTP Tokens, Seasonal Patterns, Farmer Retention, Profile, Search, Legal Documents, Legal Document Edit, Legal Acceptances

**Manager dashboard (`/manager/*`)** : Cooperative management (19 routes):
- Dashboard, Farmers, Deliveries, Grading Queue, Cycles, Disbursements, Loans, Sales/Buyers, Inventory, Deductions, Reports, Routes, Setup Cooperative, Users, Audit Log, Grade Prices, Profile, Settings, Search Results

**Accountant dashboard (`/accountant/*`)** : Financial operations (9 routes):
- Dashboard, Cycles, Disbursements, Loans, Deductions, Reports, Profile, Settings, Search Results

**Grader portal (`/grader/*`)** : Field operations (8 routes):
- Dashboard, Record Delivery, Grade, My Grades, Sync (offline PWA sync), Profile, Settings, Search Results

**Auditor dashboard (`/auditor/*`)** : Internal auditor (8 routes):
- Dashboard, Audit Log, Financial, Production, Loans, Reports, Profile, Settings, Search Results

**External Auditor portal (`/external-auditor/*`)** : External auditor (6 routes):
- Financial Statements, Audit Trail, Loan Portfolio, Profile, Settings, Search Results

---

## Chapter 9: Infrastructure and Deployment

### Cloudflare Pages Configuration

The frontend build produces a `dist/` folder with two HTML entry points:
- `dist/index.html`: Admin SPA
- `dist/farmer/index.html`: Farmer portal

Cloudflare Pages is configured with:
- **Build command:** `npm install && npm run build`
- **Build output:** `dist`
- **Environment variables:** `VITE_API_PROXY=` (points to Render backend)


Routing: `/* /index.html 200` for the admin SPA, `/farmer/* /farmer/index.html 200` for the farmer SPA.

### Render Backend Configuration

**Entrypoint (`backend/entrypoint.sh`):**
The entrypoint handles the full startup sequence for the `web` service type:
1. **Fresh DB detection**: Checks `django_migrations` table existence via raw SQL. If absent, runs `migrate --noinput`. Otherwise uses `--fake-initial` fallback.
2. **`collectstatic`**: `python manage.py collectstatic --noinput --clear` to gather all static files.
3. **Background Celery**: Starts `celery worker` (concurrency=1, max-tasks-per-child=1000, max-memory-per-child=200000) and `celery beat` (database scheduler) in background.
4. **Gunicorn**: `gunicorn zaoapi.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2} --timeout 120`

**Celery worker and beat** also run as separate container services (`celery_worker`, `celery_beat`) in docker-compose, sharing the same image but with `SERVICE_TYPE=worker` / `SERVICE_TYPE=beat` environment variables.

**Web service health check:** `GET /api/health/` returns `200 OK` with `{"status": "ok", "database": "ok", "redis": "ok", "celery": "ok"}`.

### CORS Configuration

```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173").split(",")
CORS_ALLOW_CREDENTIALS = True
```

The `FRONTEND_URL` setting is used in email templates and SMS messages to generate absolute URLs for the farmer portal.

### Environment Variable Reference

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | Yes | :  | Django secret key |
| `DEBUG` | No | False | Debug mode |
| `DATABASE_URL` | Yes | :  | PostgreSQL connection string |
| `FIELD_ENCRYPTION_KEY` | Yes | :  | Fernet encryption key for farmer ID/bank data |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Celery broker + result backend |
| `MPESA_CONSUMER_KEY` | Yes | :  | Daraja OAuth consumer key |
| `MPESA_CONSUMER_SECRET` | Yes | :  | Daraja OAuth consumer secret |
| `MPESA_PASSKEY` | Yes | :  | Daraja B2C passkey |
| `MPESA_SHORTCODE` | Yes | :  | M-Pesa shortcode |
| `MPESA_INITIATOR_PASSWORD` | Yes | :  | B2C initiator password |
| `MPESA_B2C_RESULT_URL` | Yes | :  | Daraja callback URL |
| `MPESA_B2C_TIMEOUT_URL` | Yes | :  | Daraja timeout callback URL |
| `MPESA_DISBURSEMENT_BLACKOUT_START` | No | '01:00' | Blackout window start (EAT) |
| `MPESA_DISBURSEMENT_BLACKOUT_END` | No | '04:00' | Blackout window end (EAT) |
| `MPESA_CALLBACK_IP_WHITELIST` | No | '' | Comma-separated CIDR for callback IP allowlist |
| `MPESA_CALLBACK_HMAC_SECRET` | No | :  | Additional HMAC verification |
| `AT_API_KEY` | No | :  | Africa's Talking API key |
| `AT_USERNAME` | No | :  | Africa's Talking username |
| `NOTIFICATIONS_DRY_RUN` | No | True | Skip actual SMS sending |
| `EMAIL_BACKEND` | No | `console.EmailBackend` | SMTP or console |
| `FIELD_ENCRYPTION_KEY` | Yes | :  | Fernet key for sensitive fields |
| `GOOGLE_API_KEY` | No | :  | Gemini AI API key |
| `GOOGLE_CLIENT_ID` | No | :  | Google OAuth client ID (not fully wired) |
| `ORS_API_KEY` | No | :  | OpenRouteService API key |
| `CELERY_TASK_ALWAYS_EAGER` | No | False | Run tasks synchronously (dev) |

### Database Migration Strategy

Migrations run automatically on Render deployment via a post-deploy script:
```bash
python manage.py migrate --noinput
```

The `seed_demo_data` command (`python manage.py seed_demo_data --clear`) populates development with 3 cooperatives, 150 farmers, 1,152 deliveries, 30 loans, and realistic financial data.

---

## Chapter 10: Security Architecture

### Multi-Tenant Data Isolation

Every `CooperativeScopedModel` subclass has `TenantManager` as its default manager. `CooperativeScopedViewSet.get_queryset()` adds `cooperative_id` filtering. The `TenantMiddleware` sets `request.cooperative_id` from:
- The authenticated user's `cooperative_id` (for staff roles)
- The `HTTP_X_COOPERATIVE_ID` header (for farmers with multiple memberships)
- The farmer's primary active membership (if only one)


### JWT Security

- Access token lifetime: 1 day. Cannot be revoked before expiry.
- Refresh token lifetime: 30 days. `ROTATE_REFRESH_TOKENS=True` blacklists the old token on each use.
- Refresh tokens stored in HTTP-only cookies (`HttpOnly`, `Secure`, `SameSite=Lax`, path=`/api/auth/`).
- Access tokens stored in React component state (not `localStorage`: XSS cannot directly read component state, only localStorage).
- `rest_framework_simplejwt.token_blacklist` stores blacklisted tokens in PostgreSQL.

### 2FA Implementation

Mandatory for Manager and Accountant roles (cannot be disabled). Optional for Admin. Implemented via:
- `TwoFactorOTP` model with 6-digit code, 5-minute expiry, 5-attempt limit
- Email delivery via SMTP
- `LOGIN_TOKEN_SALT` signed by `TimestampSigner` ; time-limited, tamper-proof login token

### OTP Brute Force Protection

The `TwoFactorOTP.attempts` counter increments on each failed verification. After 5 attempts, the OTP is rejected even if the correct code is provided. The `RequestOTPSerializer` uses a new OTP per request (old OTPs are not automatically invalidated, but the 5-attempt limit on each individual OTP provides protection).

### Soft-Delete and Trash Bin

- All major models inherit from `SoftDeletableModel` or `CooperativeScopedModel` with `deleted_at` field.
- `TenantManager` filters `deleted_at__isnull=True` by default.
- `Cooperative.delete()` cascades soft-delete to 18 related models.
- `TenantManager.all_with_trashed()` and `trashed_only()` provide escape hatches for admin views.
- `purge_deleted_records` Celery beat task permanently deletes records older than `TRASH_RETENTION_DAYS` (default 30 days).

### Audit Logging

`log_audit()` utility creates `AuditLog` records with:
- `actor` (nullable for system actions)
- `resource_type` and `resource_id`
- `action` from `AuditAction` enum
- `previous_value`/`new_value` JSONFields
- `ip_address`
- `cooperative_id` (nullable for superadmin actions)

`AuditLog.save()` raises `ValueError` on update, logs are insert-only.

### Field Encryption

`id_number` and bank details are encrypted at the ORM level using Fernet (AES-128-CBC with HMAC). The `FIELD_ENCRYPTION_KEY` setting is the Fernet key. `encrypt_field()`/`decrypt_field()` in `apps.base.encryption` handle the conversion. The encrypted values are stored as base64-encoded strings.

### Superadmin IP Restriction

`SuperAdminIPMiddleware` intercepts `/api/admin/` routes. If `SUPERADMIN_ALLOWED_IPS` is set, any request from a non-whitelisted IP returns 404 (not 403, the existence of the endpoint is hidden from attackers).

---

## Chapter 11: Known Gaps and Technical Debt

### 11.1 Known Remaining Issues

- **`grade_breakdown` dual-shape:** The `FarmerPayment.grade_breakdown` JSONField has two incompatible shapes depending on `payment_model`. There is no enforced schema at the database level, a payment cycle can switch models and corrupt historical data.

- **Chatbot system prompt hardcoded:** The `SYSTEM_PROMPT` in `chat/views.py` is a large multi-line string. When the API schema evolves, the system prompt must be manually updated to reflect new endpoints, roles, and workflows.

- **No USSD menu customization:** The USSD menu structure is hardcoded in `ussd.py`. A cooperative cannot customize the menu text or add menu items.

### 11.2 Deferred Features

- **Multiple produce types per farmer:** A farmer is currently associated with a single `produce_type` per cooperative. Some farmers deliver both dairy and produce.
- **AGM annual report:** The `AnnualReportView` returns JSON data, but no PDF generation template exists for AGM-style cooperative annual reports.
- **KRA withholding tax remittance flow:** Withholding tax is computed and stored but no UI or report automates the KRA remittance process.
- **Payment advance for cycles:** Some cooperatives want to advance payments before the normal cycle for different reasons. The data model and computation engine do not support advances.
- **Seasonal closure periods:** Cooperatives that close during off-seasons (no deliveries) have no way to configure a closure period: cycles can still be created with date ranges that include closure periods.
- **Deceased/incapacitated farmer handling:** No workflow exists for transferring a deceased farmer's account to a next of kin or settling their final payment.


---

## Chapter 13: How to Run the Project

### 13.1 First-Time Setup

```bash
# Clone the repository
git clone <repo_url>
cd zao

# Copy environment template
cp backend/.env.example backend/.env

# Edit backend/.env with your values:
# SECRET_KEY=<generate-with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
# DATABASE_URL=postgresql://user:password@localhost:5432/zao
# REDIS_URL=redis://localhost:6379/0
# FIELD_ENCRYPTION_KEY=<generate-with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
# (Add M-Pesa, Africa's Talking, Cloudinary, Google AI keys as needed)
```

### 13.2 Database Setup

```bash
# Run migrations
cd backend
python manage.py migrate

# Seed demo data (optional)
python manage.py seed_demo_data --clear

# Create superuser
python manage.py createsuperuser

# Seed legal documents
python manage.py sync_legal_documents --mode=seed
```

### 13.3 Running the Development Stack

**Option A: Docker Compose (recommended)**

```bash
docker compose up -d
```

Services started:
- `web`: Django + Gunicorn on port 8000
- `db`: PostgreSQL 16 on port 5433 (host), 5432 (container)
- `redis`: Redis 7 on port 6380 (host), 6379 (container)
- `celery_worker`: Celery worker
- `celery_beat`: Celery beat scheduler
- `client`: Vite dev server on port 5173

**Option B: Local development (no Docker)**

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# Celery worker (separate terminal)
source .venv/bin/activate
celery -A zaoapi worker --loglevel=info

# Celery beat (separate terminal)
source .venv/bin/activate
celery -A zaoapi beat --loglevel=info

# Frontend
cd client
npm install
npm run dev
```

### 13.4 Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Specific app
pytest apps/payment_engine/

# By marker
pytest -m financial
pytest -m api
pytest -m model

# Hypothesis (property-based tests)
pytest -m hypothesis
```

### 13.5 Deployment

**Render (Backend):**

1. Create a new Web Service on Render
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn zaoapi.wsgi:application --bind 0.0.0.0:8000 --workers 4`
5. Add environment variables from `.env.example`
6. Add a PostgreSQL database (Render Postgres)
7. Add a Redis instance (Render Redis)
8. Deploy

**Celery on Render:**

1. Create a Background Worker service
2. Set start command: `celery -A zaoapi worker --loglevel=info --concurrency=4`
3. Environment variables same as web service

**Celery Beat on Render:**

1. Create another Background Worker
2. Set start command: `celery -A zaoapi beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

**Cloudflare Pages (Frontend):**

1. Create a new Pages project
2. Connect GitHub repository
3. Build command: `npm install && npm run build`
4. Build output directory: `dist`
5. Add environment variable: `VITE_API_PROXY=https://your-render-app.onrender.com`
6. Deploy

---
