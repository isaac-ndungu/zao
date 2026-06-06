# Zao API — Farmer-First Cooperative Management Platform

## Contributor
Isaac Ndungu

## Overview

**Zao** is a comprehensive farmer-first cooperative management platform built specifically for Kenyan agricultural cooperatives. It digitizes and automates the complete operations cycle—from the moment a farmer arrives at the collection point with produce, through quality grading, inventory management, payment computation, and final disbursement—with full transparency and auditability at every step.

Zao uniquely combines three key capabilities:
- **Offline-first grader interface** that works without internet at rural collection points using IndexedDB + Service Worker PWA
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
-  **USSD Self-Service** — Check balance and payment history on any GSM feature phone
-  **Farmer Portal** — View delivery history, grade breakdown, payment statements, and cycle details
-  **Payment Transparency** — See exact calculations: deliveries → grades → deductions → final payment
-  **Downloadable Statements** — PDF statements for each payment cycle
-  **SMS Notifications** — Automatic payment confirmations and delivery receipts

### For Cooperatives
-  **Offline Grading Interface** — Graders log deliveries offline; sync automatically when online
-  **Real-Time Inventory** — Track stock by grade and batch across seasons
-  **Flexible Payment Engine** — Support for fixed-price (dairy) and revenue-share (coffee, honey) models
-  **Payment Cycle Locks** — Explicit lock mechanism prevents post-disbursement disputes
-  **Bulk Disbursement** — Multi-channel payouts: M-Pesa B2C, bank CSV export, cash vouchers
-  **Seasonal Reports** — Generate comprehensive cooperative financial statements

### For Accountants & Managers
-  **Payment Preview** — Review all computed payments before lock
-  **Audit Trail** — Immutable log of every write operation with reasons
-  **Deductions Management** — Track cooperative levies, fees, and loan repayments per farmer
-  **Financial Reports** — Generate audit-ready seasonal and cycle reports
-  **Role-Based Access** — Six roles with granular permission control

### For Auditors
-  **Read-Only Access** — Full financial visibility with enforced read-only enforcement
-  **Complete Audit Trail** — Every action logged with actor, timestamp, and previous values
-  **Immutable Records** — No retrospective edits to locked cycles or audit logs

---



### Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Django 6.0.5 + DRF 3.17.1 | REST API, ORM, admin interface |
| **Frontend** | React | Single-page application |
| **PWA** | Service Worker + IndexedDB | Offline delivery logging & sync |
| **Database** | PostgreSQL 13+ | Transactional data store |
| **Task Queue** | Celery 5.6.3 | Async operations (payments, SMS, reports) |
| **Message Broker** | Redis 7.4.0 | Celery broker, session cache, token blacklist |
| **Payments** | M-Pesa Daraja API | B2C disbursement, STK Push |
| **SMS + USSD** | Africa's Talking | Notifications, USSD self-service |
| **PDF Generation** | WeasyPrint 68.1 | Statements, reports, vouchers |
| **API Docs** | drf-spectacular 0.29.0 | Swagger UI + ReDoc auto-docs |


---

## Prerequisites

- **Python 3.14+**
- **PostgreSQL 13+** (with connection details)
- **Redis 7.0+** (for Celery broker and session cache)
- **Git**

### External Services (Required for production)
- **M-Pesa Daraja API** — Safaricom payment gateway account with B2C credentials
- **Africa's Talking** — SMS and USSD gateway account
- **Cloudinary** (optional) — Media storage for reports and documents
- **Email Server** — SMTP credentials for OTP and notifications

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone <repo_url>
cd zao
```

### 2. Create and Activate Virtual Environment

**On Linux/macOS:**
```bash
python -m venv env
source env/bin/activate
```

**On Windows :**
```powershell
python -m venv env
source env\Scripts\Activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=zao_db
DATABASE_USER=zao_user
DATABASE_PASSWORD=your-secure-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Tokens
JWT_ALGORITHM=HS256
ACCESS_TOKEN_LIFETIME=900  # 15 minutes in seconds
REFRESH_TOKEN_LIFETIME=604800  # 7 days in seconds

# Field-Level Encryption
FIELD_ENCRYPTION_KEY=your-32-character-base64-encoded-key

# M-Pesa Daraja
MPESA_ENVIRONMENT=sandbox  # or 'production'
MPESA_CONSUMER_KEY=your-daraja-consumer-key
MPESA_CONSUMER_SECRET=your-daraja-consumer-secret
MPESA_PASSKEY=your-mpesa-passkey
MPESA_SHORTCODE=your-business-shortcode
MPESA_B2C_RESULT_URL=https://yourdomain.com/api/callback/mpesa/result/
MPESA_B2C_TIMEOUT_URL=https://yourdomain.com/api/callback/mpesa/timeout/
MPESA_DISBURSEMENT_BLACKOUT_START=01:00  # No disbursements between these times
MPESA_DISBURSEMENT_BLACKOUT_END=04:00

# Africa's Talking
AFRICAS_TALKING_USERNAME=sandbox
AFRICAS_TALKING_API_KEY=your-api-key
AFRICAS_TALKING_SHORTCODE=your-shortcode
AFRICAS_TALKING_USSD_CODE=*xxx#

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com  # or your email provider
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@zaocooperatives.com

# Cloudinary (optional, for media storage)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Timezone
TIME_ZONE=Africa/Nairobi
```

### 5. Initialize the Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```



---

## Running the Application

### Development Server

**Start Django Development Server:**
```bash
cd backend
python manage.py runserver 0.0.0.0:8000
```

**In another terminal, start Celery Worker:**
```bash
cd backend
celery -A zaoapi worker -l info
```

**In a third terminal, start Celery Beat (for scheduled tasks):**
```bash
cd backend
celery -A zaoapi beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Production Deployment

**Using Render or Railway:**
1. Set environment variables in the dashboard
2. Deploy using their CLI or GitHub integration
3. Run migrations on first deploy: `python manage.py migrate`
4. Configure the Celery worker as a background worker

**Using Gunicorn + Systemd:**
```bash
# Install gunicorn
pip install gunicorn

# Start with gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8000 zaoapi.wsgi:application
```

---

## Project Structure

```
zao/
├── backend/                          # Django backend
│   ├── apps/                         # Django apps (business logic)
│   │   ├── auth_api/                 # Authentication & JWT tokens
│   │   ├── base/                     # Shared models, permissions, middleware
│   │   ├── cooperatives/             # Cooperative management
│   │   ├── users/                    # User profiles & roles
│   │   ├── farmers/                  # Farmer profiles & data
│   │   ├── deliveries/               # Delivery logging (offline + online)
│   │   ├── grading/                  # Quality grading
│   │   ├── inventory/                # Stock tracking by grade & batch
│   │   ├── routes/                   # Collection routes
│   │   ├── sales/                    # Bulk sales to external buyers
│   │   ├── payment_engine/           # Payment computation & locking
│   │   ├── deductions/               # Levies, fees, loan repayments
│   │   ├── loans/                    # Farmer loan tracking
│   │   ├── disbursement/             # M-Pesa B2C, exports, vouchers
│   │   ├── notifications/            # SMS, USSD, email
│   │   └── statements/               # Statements & reports
│   │
│   ├── zaoapi/                       # Django project config
│   │   ├── settings.py               # Settings, middleware, auth config
│   │   ├── urls.py                   # URL routing
│   │   ├── wsgi.py                   # WSGI app for servers
│   │   ├── asgi.py                   # ASGI app for async servers
│   │   ├── celery.py                 # Celery configuration
│   │   └── tasks.py                  # Shared Celery tasks
│   │
│   ├── manage.py                     # Django CLI tool
│   ├── requirements.txt              # Python dependencies
│   ├── doc.md                        # Detailed project documentation
│   └── endpoint.json                 # API endpoint reference
│
├── env/                              # Python virtual environment
├── LICENSE                           # Project license
└── README.md                         # This file
```

### Key Apps Overview

| App | Purpose | Key Models |
|---|---|---|
| `auth_api` | User registration, login, 2FA, JWT tokens | `User`, `OTPVerification` |
| `base` | Shared models, permissions, audit logging | `AuditLog`, `TenantMiddleware` |
| `cooperatives` | Cooperative profiles and settings | `Cooperative` |
| `farmers` | Farmer registration and profiles | `Farmer`, `PaymentMethod` |
| `deliveries` | Delivery logging (offline-first PWA) | `Delivery`, `DeliveryItem` |
| `grading` | Quality grading with audit trail | `Grade`, `GradeBreakdown` |
| `inventory` | Stock tracking by grade and batch | `InventoryBatch` |
| `sales` | Recording bulk sales to external buyers | `Sale` |
| `payment_engine` | Computing payments and cycle management | `PaymentCycle`, `FarmerPayment` |
| `deductions` | Cooperative levies, fees, loans | `Deduction` |
| `disbursement` | M-Pesa, bank export, cash vouchers | `DisbursementBatch`, `Transaction` |
| `notifications` | SMS, USSD, email | `Notification` |
| `statements` | Farmer & cooperative statements & reports | `Statement` |

---

## API Documentation

### Auto-Generated API Docs

Once the server is running, visit:

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc**: [http://localhost:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/)
- **OpenAPI Schema**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)



### Core Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| **POST** | `/api/auth/login/` | User login |
| **POST** | `/api/auth/register/` | User registration |
| **POST** | `/api/auth/2fa/request/` | Request OTP for 2FA |
| **POST** | `/api/auth/2fa/verify/` | Verify OTP |
| **POST** | `/api/auth/refresh/` | Refresh JWT access token |
| **POST** | `/api/auth/logout/` | Logout (blacklist token) |
| **GET** | `/api/farmers/` | List farmers |
| **POST** | `/api/farmers/` | Create farmer |
| **GET** | `/api/deliveries/` | List deliveries |
| **POST** | `/api/deliveries/` | Log delivery |
| **POST** | `/api/deliveries/sync/` | Sync offline deliveries |
| **GET** | `/api/grades/delivery/{id}` | Get grades for delivery |
| **POST** | `/api/grades/` | Grade a delivery |
| **GET** | `/api/inventory/` | View stock by grade |
| **GET** | `/api/payment-engine/cycles/` | List payment cycles |
| **POST** | `/api/payment-engine/run/` | Compute payments |
| **POST** | `/api/payment-engine/cycles/{id}/lock/` | Lock payment cycle |
| **POST** | `/api/disbursement/initiate/` | Initiate M-Pesa disbursement |
| **GET** | `/api/statements/farmer/{id}/cycle/{id}` | Get farmer statement |
| **POST** | `/api/statements/pdf/generate/` | Generate PDF statement |



---

## Security Features

### Authentication & Authorization

- **JWT Tokens**: 15-minute access token + 7-day refresh token
- **HTTP-Only Cookies**: Refresh tokens stored securely, inaccessible to JavaScript
- **Two-Factor Authentication (2FA)**: Email OTP required for Accountant and Manager roles on new device login
- **Role-Based Access Control (RBAC)**: Six roles with granular permissions
  - **Admin**: Full system access
  - **Cooperative Manager**: Cooperative-level management
  - **Accountant**: Financial operations (payments, deductions)
  - **Grader**: Offline-first delivery & grading
  - **Farmer**: Self-service access to own data
  - **Auditor**: Read-only access to financial records

### Data Protection

- **Field-Level Encryption**: Farmer national IDs and bank details encrypted using Fernet symmetric encryption
- **At-Rest Encryption**: PostgreSQL connection security + Neon-managed encryption
- **In-Transit Encryption**: HTTPS / TLS 1.3
- **Environment Variables**: All API credentials (M-Pesa, Africa's Talking) stored as env vars, never in code
- **Multi-Tenancy**: Cooperative-level scoping enforced at ORM level

### Audit & Compliance

- **Immutable Audit Trail**: `AuditLog` records every write operation (actor, resource, action, timestamp, before/after values)
- **Append-Only**: No update/delete permissions on audit logs at ORM or API level
- **Payment Cycle Locking**: Explicit lock mechanism prevents post-lock modifications; amendments flagged in audit trail
- **Callback Validation**: M-Pesa Daraja callbacks validated against IP whitelist + payload format
- **Logout Token Blacklisting**: Redis-backed immediate invalidation of refresh tokens on logout

---

## Integrations

### M-Pesa Daraja API

**Disbursement (B2C):**

- Purpose: Bulk farmer disbursement
- Callback: Result and timeout URLs validated and processed asynchronously

**Payment Receipts (STK Push):**
- Endpoint: `POST /mpesa/stkpush/v1/processrequest`
- Auth: OAuth 2.0
- Purpose: Payment collection from farmers (v2 feature)

### Africa's Talking

**SMS:**

- Purpose: Payment confirmations, delivery receipts, reminders

**USSD:**

- Purpose: Farmer self-service (balance, last payment) on any GSM feature phone

### Cloudinary

- **Purpose**: Media storage for PDF statements, reports, vouchers


---

## Support & Documentation

- **Internal Docs**: See [doc.md](backend/doc.md) for detailed architecture and data flow
- **API Reference**: Auto-generated at `/api/docs/` (Swagger) and `/api/redoc/` (ReDoc)
- **Issues**: Report bugs and request features via GitHub Issues
- **Security**: Report security vulnerabilities privately to the maintainers

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

