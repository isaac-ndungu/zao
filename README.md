# Zao API - Farmer-First Cooperative Management Platform

## Contributor
Isaac Ndungu

## Overview

**Zao** is a comprehensive farmer-first cooperative management platform built specifically for Kenyan agricultural cooperatives. It digitizes and automates the complete operations cycle - from the moment a farmer arrives at the collection point with produce, through quality grading, inventory management, payment computation, and final disbursement - with full transparency and auditability at every step.

Zao uniquely combines three key capabilities:
- **Offline-first grader interface** that works without internet at rural collection points using IndexedDB and Service Worker PWA
- **USSD self-service channel** that gives every farmer, including those on basic feature phones, direct access to their own delivery and payment data
- **Locked, auditable payment engine** that makes payment disputes resolvable with a permanent, immutable record

### Supported Cooperative Types

Zao supports the following agricultural cooperative models in Kenya:

| Cooperative Type | Pricing Model | Grading Standard | Cycle |
|---|---|---|---|
| **Dairy** | Fixed price per litre by grade | Grade-based (e.g., A, B, C) | Daily |
| **Coffee** | Revenue share | Cherry and parchment stages | Seasonal |
| **Honey** | Revenue share | Moisture content | Seasonal |


---

## Key Features

### For Farmers
- **USSD Self-Service** - Check balance and payment history on any GSM feature phone
- **Farmer Portal** - View delivery history, grade breakdown, payment statements, and cycle details
- **Payment Transparency** - See exact calculations: deliveries, grades, deductions, final payment
- **Downloadable Statements** - PDF statements for each payment cycle
- **SMS Notifications** - Automatic payment confirmations and delivery receipts

### For Cooperatives
- **Offline Grading Interface** - Graders log deliveries offline and sync automatically when online
- **Real-Time Inventory** - Track stock by grade and batch across seasons
- **Flexible Payment Engine** - Support for fixed-price (dairy) and revenue-share (coffee, honey) models
- **Payment Cycle Locks** - Explicit lock mechanism prevents post-disbursement disputes
- **Bulk Disbursement** - Multi-channel payouts: M-Pesa B2C, bank CSV export, cash vouchers
- **Seasonal Reports** - Generate comprehensive cooperative financial statements
- **Route Management** - Plan collection routes with stop assignment and map visualization

### For Accountants and Managers
- **Payment Preview** - Review all computed payments before lock
- **Audit Trail** - Immutable log of every write operation with reasons
- **Deductions Management** - Track cooperative levies, fees, and loan repayments per farmer
- **Financial Reports** - Generate audit-ready seasonal and cycle reports
- **Role-Based Access** - Six roles with granular permission control

### For Auditors
- **Read-Only Access** - Full financial visibility with enforced read-only enforcement
- **Complete Audit Trail** - Every action logged with actor, timestamp, and previous values
- **Immutable Records** - No retrospective edits to locked cycles or audit logs

---


### Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Django 6.0.5 and DRF 3.17.1 | REST API, ORM, admin interface |
| **Frontend** | React with Vite | Single-page application |
| **PWA** | Service Worker and IndexedDB | Offline delivery logging and sync |
| **Database** | PostgreSQL 16 | Transactional data store |
| **Task Queue** | Celery 5.6.3 | Async operations (payments, SMS, reports) |
| **Message Broker** | Redis 7 | Celery broker, session cache, token blacklist |
| **Payments** | M-Pesa Daraja API | B2C disbursement, STK Push |
| **SMS and USSD** | Africa's Talking | Notifications, USSD self-service |
| **PDF Generation** | WeasyPrint 68.1 | Statements, reports, vouchers |
| **API Docs** | drf-spectacular 0.29.0 | Swagger UI and ReDoc auto-docs |
| **AI** | Google Gemini API (gemini-2.0-flash) | API chatbot for cooperative Q&A |
| **Maps and Routing** | OpenRouteService and Leaflet | Route visualization and collection planning |


---

## Prerequisites

You need Docker and Docker Compose to run this project. Everything runs in containers so you do not need to install Python, Node.js, PostgreSQL, or Redis separately on your machine.

### External Services (Required for production)
- **M-Pesa Daraja API** - Safaricom payment gateway account with B2C credentials
- **Africa's Talking** - SMS and USSD gateway account
- **OpenRouteService** - API key from openrouteservice.org for route planning and map visualization
- **Cloudinary** (optional) - Media storage for reports and documents
- **Google AI (Gemini)** - API key from aistudio.google.com for the chatbot
- **Email Server** - SMTP credentials for OTP and notifications

### Important Environment Variables

Several settings must be configured for the system to work properly:

- **FIELD_ENCRYPTION_KEY** - Fernet encryption key for protecting farmer national IDs and bank details. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- **MPESA_CALLBACK_IP_WHITELIST** - Comma-separated CIDR ranges allowed to call M-Pesa callbacks. Leave empty to allow all.
- **MPESA_CALLBACK_HMAC_SECRET** - Optional HMAC secret for additional callback verification
- **CELERY_TASK_ALWAYS_EAGER** - Set to False in production to run tasks asynchronously via Celery. True runs tasks synchronously (no workers needed).

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <repo_url>
cd zao
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp backend/.env.example backend/.env
```

The docker-compose setup uses `DATABASE_URL` and `REDIS_URL` to connect services internally. For local development, the ports are mapped as follows:
- PostgreSQL: localhost:5433
- Redis: localhost:6380
- Web API: localhost:8000
- React Client: localhost:5173

### 3. Start All Services

```bash
docker compose up -d
```

This starts six containers:
- **web** - Gunicorn and Django API
- **db** - PostgreSQL 16
- **redis** - Redis 7
- **celery_worker** - Async task processor
- **celery_beat** - Scheduled task scheduler
- **client** - React frontend with Vite

### 4. Run Migrations

```bash
docker compose exec web python manage.py migrate
```

### 5. Seed Demo Data (Optional)

Populates the database with realistic Kenyan cooperative data for development and presentations:

```bash
docker compose exec web python manage.py seed_demo_data --clear
```

Creates 3 co-ops, 150 farmers, 1,152 deliveries, 30 loans, and more. See seed_demo_data.py for details.

### 6. Create a Superuser (if not using seed data)

```bash
docker compose exec web python manage.py createsuperuser
```


---

## Running the Application

### Development

All services run inside Docker containers. One command starts everything:

```bash
docker compose up -d
```

The API is available at http://localhost:8000 and the React frontend at http://localhost:5173.

### Useful Commands

| Action | Command |
|---|---|
| Start all services | `docker compose up -d` |
| Stop all services | `docker compose down` |
| Restart web only | `docker compose restart web` |
| View web logs | `docker compose logs web -f` |
| Run a Django command | `docker compose exec web python manage.py <command>` |
| Open a shell in the container | `docker compose exec web bash` |
| Check service health | `curl http://localhost:8000/api/health/` |

### Testing

Run the test suite inside Docker:

```bash
docker compose exec web pytest
```

You can run specific test markers:

```bash
docker compose exec web pytest -m api        # API endpoint tests only
docker compose exec web pytest -m model      # Model validation tests only
docker compose exec web pytest -m financial   # Financial logic tests only
docker compose exec web pytest -m soft_delete # Soft-delete cascade tests
```

Or run a specific app's tests:

```bash
docker compose exec web pytest apps/payment_engine/
```

The project uses pytest with the following markers defined in pytest.ini:
- **api** - Tests for API endpoints
- **model** - Tests for model validation and methods
- **financial** - Tests for financial logic (payment_engine, loans, disbursement, deductions, sales)
- **soft_delete** - Tests for soft-delete cascade behavior
- **hypothesis** - Property-based tests using hypothesis
- **async** - Async tests using django.test.AsyncClient

### Management Commands

Beyond the standard Django management commands, Zao includes several custom commands:

| Command | Purpose |
|---|---|
| `seed_demo_data --clear` | Populates the database with demo co-ops, farmers, deliveries, and loans |
| `purge_trashed --days N --execute` | Permanently deletes soft-deleted records older than N days |
| `recompute_stock --check` | Verifies stock consistency without applying changes |
| `sync_legal_documents --mode=seed` | Seeds legal documents (terms, privacy policy) on first install |
| `sync_legal_documents --mode=publish` | Publishes a new version of legal documents |

Run any management command with:

```bash
docker compose exec web python manage.py <command>
```

### Celery Beat Schedule

The following tasks run automatically on the celery_beat container:

| Task | Schedule | Purpose |
|---|---|---|
| reconcile-stuck-disbursements | Every 15 minutes | Retries failed M-Pesa B2C transactions |
| cleanup-expired-ussd-sessions | Daily at 2 AM | Removes stale USSD session data |
| cleanup-expired-otps | Every 30 minutes | Removes expired one-time passwords |
| purge-deleted-records | Daily at 1:30 AM | Permanently deletes records past retention |
| analytics-daily-snapshots | Daily at midnight | Computes daily analytics snapshots |
| analytics-weekly-snapshots | Monday 1 AM | Computes weekly analytics snapshots |
| analytics-monthly-snapshots | 1st of month 2 AM | Computes monthly analytics snapshots |
| analytics-materialized-monthly | 1st of month 3 AM | Refreshes materialized analytics views |
| analytics-warm-cache | Every 15 minutes | Warms analytics cache for faster queries |
| analytics-refresh-leaderboards | Hourly | Refreshes cooperative leaderboard rankings |

### OTPs and Emails in Development

Emails are printed to the container logs when using the console email backend:

```bash
docker compose logs web -f
```

When DEBUG is True, OTP codes are also returned directly in the API response body:

```json
POST /api/auth/2fa/request/ -> {"detail": "OTP sent.", "otp_code": "482916"}
POST /api/auth/farmer/request/ -> {"detail": "OTP sent.", "otp_code": "482916", "login_token": "..."}
```

### Production Deployment

**Using Render or Railway:**
1. Set environment variables in the dashboard
2. Deploy using their CLI or GitHub integration
3. Run migrations on first deploy: `docker compose exec web python manage.py migrate`
4. Configure the Celery worker as a background worker

**Using Docker on a VPS:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Project Structure

```
zao/
├── backend/                          # Django backend
│   ├── apps/                         # Django apps (business logic)
│   │   ├── auth_api/                 # Authentication and JWT tokens
│   │   ├── base/                     # Shared models, permissions, middleware
│   │   ├── cooperatives/             # Cooperative management
│   │   ├── users/                    # User profiles and roles
│   │   ├── farmers/                  # Farmer profiles and data
│   │   ├── deliveries/               # Delivery logging (offline and online)
│   │   ├── grading/                  # Quality grading
│   │   ├── inventory/                # Stock tracking by grade and batch
│   │   ├── routes/                   # Collection routes with map visualization
│   │   ├── sales/                    # Bulk sales to external buyers
│   │   ├── payment_engine/           # Payment computation and locking
│   │   ├── deductions/              # Levies, fees, loan repayments
│   │   ├── loans/                   # Farmer loan tracking
│   │   ├── disbursement/            # M-Pesa B2C, exports, vouchers
│   │   ├── chat/                    # AI chatbot (Gemini)
│   │   ├── notifications/            # SMS, USSD, email
│   │   ├── statements/              # Statements and reports
│   │   ├── analytics/               # Cooperative analytics and reporting
│   │   └── legal/                   # Terms, policies, compliance
│   │
│   ├── zaoapi/                      # Django project config
│   │   ├── settings.py              # Settings, middleware, auth config
│   │   ├── urls.py                  # URL routing
│   │   ├── wsgi.py                  # WSGI app for servers
│   │   ├── asgi.py                  # ASGI app for async servers
│   │   ├── celery.py                # Celery configuration
│   │   └── tasks.py                 # Shared Celery tasks
│   │
│   ├── manage.py                    # Django CLI tool
│   ├── requirements.txt             # Python dependencies
│   ├── doc.md                       # Detailed project documentation
│   └── endpoint.json                # API endpoint reference
│
├── client/                          # React frontend
│   ├── src/                         # React source
│   ├── farmer/                      # Farmer-facing pages
│   ├── public/                      # Static assets
│   ├── package.json                 # Node dependencies
│   └── vite.config.js               # Vite configuration
│
├── docker-compose.yml               # Docker service definitions
├── LICENSE                          # Project license
└── README.md                        # This file
```

### Key Apps Overview

| App | Purpose | Key Models |
|---|---|---|
| `auth_api` | User registration, login, 2FA, JWT tokens | User, OTPVerification |
| `base` | Shared models, permissions, audit logging | AuditLog, TenantMiddleware |
| `cooperatives` | Cooperative profiles and settings | Cooperative |
| `farmers` | Farmer registration and profiles | Farmer, PaymentMethod |
| `deliveries` | Delivery logging (offline-first PWA) | Delivery, DeliveryItem |
| `grading` | Quality grading with audit trail | Grade, GradeBreakdown |
| `inventory` | Stock tracking by grade and batch | InventoryBatch |
| `routes` | Collection route planning and map visualization | CollectionRoute, RouteStop |
| `sales` | Recording bulk sales to external buyers | Sale |
| `payment_engine` | Computing payments and cycle management | PaymentCycle, FarmerPayment |
| `deductions` | Cooperative levies, fees, loans | Deduction |
| `disbursement` | M-Pesa, bank export, cash vouchers | DisbursementBatch, Transaction |
| `chat` | Session-based AI chatbot | ChatMessage |
| `notifications` | SMS, USSD, email | Notification |
| `statements` | Farmer and cooperative statements and reports | Statement |
| `analytics` | Cooperative analytics and data insights | Various query models |
| `legal` | Terms, privacy policies, compliance | LegalDocument |

---

## API Documentation

### Auto-Generated API Docs

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/schema/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/


### Core Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/auth/login/ | User login |
| POST | /api/auth/register/ | User registration |
| POST | /api/auth/2fa/request/ | Request OTP for 2FA |
| POST | /api/auth/2fa/verify/ | Verify OTP |
| POST | /api/auth/refresh/ | Refresh JWT access token |
| POST | /api/auth/logout/ | Logout (blacklist token) |
| GET | /api/farmers/ | List farmers |
| POST | /api/farmers/ | Create farmer |
| GET | /api/deliveries/ | List deliveries |
| POST | /api/deliveries/ | Log delivery |
| POST | /api/deliveries/sync/ | Sync offline deliveries |
| GET | /api/grades/delivery/{id} | Get grades for delivery |
| POST | /api/grades/ | Grade a delivery |
| GET | /api/inventory/ | View stock by grade |
| GET | /api/routes/ | List collection routes |
| POST | /api/routes/ | Create collection route |
| GET | /api/routes/{id}/map/ | Get route map with stops |
| GET | /api/payment-engine/cycles/ | List payment cycles |
| POST | /api/payment-engine/run/ | Compute payments |
| POST | /api/payment-engine/cycles/{id}/lock/ | Lock payment cycle |
| POST | /api/disbursement/initiate/ | Initiate M-Pesa disbursement |
| POST | /api/chat/ | Ask the AI chatbot (JWT required) |
| GET | /api/chat/ | List conversation history |
| GET | /api/statements/farmer/{id}/cycle/{id} | Get farmer statement |
| POST | /api/statements/pdf/generate/ | Generate PDF statement |



---

## Security Features

### Authentication and Authorization

- **JWT Tokens**: 1-day access token and 7-day refresh token
- **HTTP-Only Cookies**: Refresh tokens stored securely, inaccessible to JavaScript
- **Two-Factor Authentication (2FA)**: Email OTP required for Accountant and Manager roles on new device login
- **Role-Based Access Control (RBAC)**: Six roles with granular permissions
  - **Admin**: Full system access
  - **Cooperative Manager**: Cooperative-level management
  - **Accountant**: Financial operations (payments, deductions)
  - **Grader**: Offline-first delivery and grading
  - **Farmer**: Self-service access to own data
  - **Auditor**: Read-only access to financial records

### Data Protection

- **Field-Level Encryption**: Farmer national IDs and bank details encrypted using Fernet symmetric encryption
- **At-Rest Encryption**: PostgreSQL connection security and Neon-managed encryption
- **In-Transit Encryption**: HTTPS and TLS 1.3
- **Environment Variables**: All API credentials (M-Pesa, Africa's Talking) stored as env vars, never in code
- **Multi-Tenancy**: Cooperative-level scoping enforced at ORM level

### Audit and Compliance

- **Immutable Audit Trail**: AuditLog records every write operation (actor, resource, action, timestamp, before and after values)
- **Append-Only**: No update or delete permissions on audit logs at ORM or API level
- **Payment Cycle Locking**: Explicit lock mechanism prevents post-lock modifications. Amendments are flagged in audit trail
- **Callback Validation**: M-Pesa Daraja callbacks validated against IP whitelist and payload format
- **Logout Token Blacklisting**: Redis-backed immediate invalidation of refresh tokens on logout

---

## Integrations

### M-Pesa Daraja API

**Disbursement (B2C):**

- Purpose: Bulk farmer disbursement
- Callback: Result and timeout URLs validated and processed asynchronously

**Payment Receipts (STK Push):**
- Endpoint: POST /mpesa/stkpush/v1/processrequest
- Auth: OAuth 2.0
- Purpose: Payment collection from farmers (v2 feature)

### Africa's Talking

**SMS:**

- Purpose: Payment confirmations, delivery receipts, reminders

**USSD:**

- Purpose: Farmer self-service (balance, last payment) on any GSM feature phone

### OpenRouteService

- Purpose: Route planning and map visualization for collection routes
- Auth: API key in ORS_API_KEY env var
- Features: Route optimization, turn-by-turn directions, stop sequencing

### Cloudinary

- Purpose: Media storage for PDF statements, reports, vouchers

### Google AI (Gemini)

- Purpose: AI chatbot that answers cooperative Q&A - payment queries, member data, cycle insights
- Model: gemini-2.0-flash (configurable via GOOGLE_AI_MODEL)
- Auth: API key in GOOGLE_API_KEY env var
- Endpoint: POST /api/chat/ (JWT required)
- Context: System prompt built from auto-generated API schema description, enabling the model to answer from the cooperative's own data


---

## Support and Documentation

- **Internal Docs**: See doc.md for detailed architecture and data flow
- **API Reference**: Auto-generated at /api/docs/ (Swagger) and /api/redoc/ (ReDoc)
- **Issues**: Report bugs and request features via GitHub Issues
- **Security**: Report security vulnerabilities privately to the maintainers

---

## License

This project is licensed under the MIT License - see LICENSE for details.

---
