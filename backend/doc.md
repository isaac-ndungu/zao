# ZAO: Project documentation

## Project Summary

Zao is a farmer-first cooperative management platform built for Kenyan agricultural cooperatives. It digitizes and automates the full operations cycle, from the moment a farmer arrives at the collection point with produce, through grading, inventory management, payment computation, and final disbursement to farmers, with full transparency at every step for every actor.

Zao provides an offline-first grader interface that works without internet at rural collection points, a USSD self-service channel that gives every farmer, including those on basic feature phones, direct access to their own delivery and payment data, and a locked, auditable payment engine that makes payment disputes resolvable with a permanent record.

The platform serves four agricultural cooperative types in Kenya:
- Dairy cooperatives — daily delivery cycles, fixed price per litre by grade
- Coffee cooperatives — cherry and parchment stages, revenue share payment model
- Honey cooperatives — seasonal, moisture content grading, revenue share

### Scope

- Farmer membership registration, profile management, and payment method configuration
- Offline-first delivery logging at the cooperative gate using IndexedDB + Service Worker PWA
- Quality grading per delivery with grade-based pricing and full audit trail
- Cooperative inventory management by grade and batch with real-time updates
- Sales logging — admin records bulk sales to external processors and exporters
- Payment Engine supporting Fixed Price model (dairy) and Revenue Share model (coffee, honey, tea)
- Deductions management — cooperative levy, cooperative fee, loan repayments
- Payment cycle preview, explicit lock, and disbursement workflow
- Hybrid disbursement — M-Pesa B2C auto-dispatch via Daraja, bank export CSV, cash voucher PDF
- SMS delivery receipt and payment notification via Africa's Talking
- USSD farmer self-service — balance and last payment on any GSM feature phone
- Farmer web portal — delivery history, grade breakdown, statements, payment history
- PDF statement and seasonal cooperative report generation via WeasyPrint
- Multi-tenant architecture — multiple cooperatives fully isolated on one platform
- Role-based access control — six roles: Admin, Cooperative Manager, Accountant, Grader, Farmer, Auditor
- 12 internal Django REST Framework APIs with Swagger/ReDoc auto-documentation

### Assumptions

- Target cooperatives have at least one device (laptop or tablet) at the collection point for the grader
- Target farmers have access to a GSM phone capable of receiving SMS and dialling USSD

### Dependencies

| Dependency | Type | Purpose |
|---|---|---|
| M-Pesa Daraja API | External API | Safaricom STK Push (B2C) |
| Africa's Talking | External API | SMS + USSD |
| Celery + Redis | Infrastructure | Async task queue |
| PostgreSQL | Infrastructure | Cloud database |
| WeasyPrint | Library | PDF generation |
| React PWA | Frontend | Service Worker + IndexedDB for offline support |

## Architecture Overview

Zao follows a layered monolith architecture with async processing, a Django backend exposing REST APIs consumed by a React frontend, with Celery handling all asynchronous operations.

| Layer | Technology | Purpose |
|---|---|---|
| Backend Framework | Django + DRF | REST API server, ORM, admin, routing |
| Frontend Framework | React | Single-page application, all user interfaces |
| PWA | Service Worker + IndexedDB | Offline delivery logging and sync |
| Database | PostgreSQL | Primary data store |
| Task Queue | Celery | Async: M-Pesa, SMS, report generation, reminders |
| Message Broker | Redis | Celery broker and result backend |
| Payments | M-Pesa Daraja API | STK Push (receipts), B2C (disbursement) |
| SMS + USSD | Africa's Talking | SMS receipts, USSD self-service, notifications |
| PDF Generation | WeasyPrint | Farmer statements, seasonal reports, vouchers |
| API Documentation | Swagger / ReDoc | Auto-generated from DRF serializers |
| Hosting | Render / Railway | Web server and Celery worker |

## Data Flow — Payment Cycle

1. Grader logs deliveries at collection point (offline or online)
2. Deliveries sync to Django backend via Deliveries API
3. Grader assigns quality grades — Grading API updates inventory
4. Admin logs bulk sale to external buyer — Sales API records amount
5. Accountant triggers Payment Engine API — Celery task computes all farmer payments
6. Accountant previews computed payments in dashboard
7. Accountant locks the payment cycle — cycle becomes immutable
8. Accountant initiates disbursement — Celery dispatches M-Pesa B2C calls in batches
9. Safaricom sends callbacks — Disbursement API updates per-transaction status
10. Farmers receive SMS payment confirmation via Africa's Talking
11. Farmers can check balance via USSD or download statement from web portal

## API Design

### Internal APIs — Summary

| API App | Base Path | Key Endpoints |
|---|---|---|
| Auth API | `/api/auth/` | `POST /login`, `POST /refresh`, `POST /logout`, `POST /2fa/request`, `POST /2fa/verify` |
| Users API | `/api/users/` | `GET /me`, `PUT /me`, `GET /{id}`, `POST /` (admin), `GET /roles` |
| Cooperatives API | `/api/cooperatives/` | `GET /`, `POST /` (admin), `GET /{id}`, `PUT /{id}/settings` |
| Farmers API | `/api/farmers/` | `GET /`, `POST /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`, `GET /{id}/summary` |
| Deliveries API | `/api/deliveries/` | `GET /`, `POST /`, `POST /sync` (batch offline sync), `GET /farmer/{id}`, `GET /batch/{id}` |
| Grading API | `/api/grades/` | `POST /`, `GET /delivery/{id}`, `PUT /{id}` (override with reason) |
| Inventory API | `/api/inventory/` | `GET /`, `GET /summary`, `GET /batch/{id}`, `GET /alerts` |
| Sales API | `/api/sales/` | `GET /`, `POST /`, `GET /{id}`, `GET /cycle/{id}` |
| Payment Engine API | `/api/payment-engine/` | `POST /run`, `GET /cycles`, `GET /cycles/{id}/preview`, `POST /cycles/{id}/lock` |
| Deductions API | `/api/deductions/` | `GET /`, `POST /`, `GET /farmer/{id}/cycle/{id}`, `DELETE /{id}` |
| Disbursement API | `/api/disbursement/` | `POST /initiate`, `GET /batches`, `GET /batches/{id}`, `POST /retry/{transaction_id}`, `POST /callback/result` |
| Notifications API | `/api/notifications/` | `POST /send`, `GET /log`, `POST /ussd/callback` (Africa's Talking webhook) |
| Statements API | `/api/statements/` | `GET /farmer/{id}/cycle/{id}`, `GET /cooperative/season`, `GET /audit-log`, `POST /pdf/generate` |

### External API Integrations

| Integration | Endpoint Used | Purpose | Auth Method |
|---|---|---|---|
| M-Pesa Daraja | `POST /mpesa/b2c/v3/paymentrequest` | Bulk farmer disbursement | OAuth 2.0 Consumer Key/Secret |
| M-Pesa Daraja | Callback URL (inbound) | Payment result from Safaricom | IP whitelist + payload validation |
| Africa's Talking | `POST /version1/messaging` | Outbound SMS to farmers | API Key |
| Africa's Talking | `POST /version1/ussd` (inbound webhook) | USSD session handling | Username + API Key |
| Daraja STK Push | `POST /mpesa/stkpush/v1/processrequest` | Payment receipts from farmers (v2) | OAuth 2.0 |

### API Conventions

- All responses use consistent envelope: `{ success, data, error, meta }`
- Pagination on all list endpoints: `?page=1&page_size=25`
- Filtering on list endpoints: `?cooperative_id=X&date_from=Y&date_to=Z`
- Error responses include a machine-readable `error_code` and human-readable `message`
- All endpoints documented via drf-spectacular, accessible at `/api/docs/` (Swagger) and `/api/redoc/` (ReDoc)

## Security

### Authentication

- JWT tokens issued on login: 15-minute access token, 7-day refresh token
- Refresh tokens stored in HTTP-only cookies — not accessible to JavaScript
- Access tokens stored in memory (React state) — cleared on tab close
- Logout blacklists the refresh token in Redis immediately
- 2FA via email OTP required for Accountant and Manager roles on every new device login

### Authorization

- RBAC enforced at the Django view level via a custom permission class per endpoint
- Cooperative scoping enforced at the ORM level — not just in view logic
- Auditor role: read-only access enforced by HTTP method restriction (GET only) on all financial endpoints
- Farmers access only their own data — farmer_id in JWT payload, enforced on every farmer-facing endpoint

### Data Protection

- All data encrypted at rest (Neon managed encryption) and in transit (HTTPS, TLS 1.3)
- Farmer national ID numbers and bank details encrypted at field level using Fernet symmetric encryption
- M-Pesa credentials (Consumer Key, Consumer Secret, Passkey) stored as environment variables — never in codebase
- Daraja callback payload validated against expected format and IP range before processing

### Audit Trail

- `AuditLog` model records every write operation: actor, resource, action, previous value, new value, timestamp
- `AuditLog` is append-only — no update or delete permissions exist at the ORM or API level
- Post-lock payment cycle changes create a required `AuditLog` entry; the cycle status shows an `AMENDED` flag visible to all roles
