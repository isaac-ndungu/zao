# Contributing to Zao

Thank you for considering contributing to Zao. This guide covers everything you need to get started.

## Prerequisites

- Python 3.14+
- Node.js 20+
- PostgreSQL 16
- Redis 7
- Docker & Docker Compose (recommended)

## Local Development Setup

### Option A: Docker Compose (recommended)

```bash
git clone <repo_url>
cd zao
cp backend/.env.example backend/.env
# Generate required keys:
#   SECRET_KEY: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
#   FIELD_ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
docker compose up -d
```

This starts all services on their default ports:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380

### Option B: Local (no Docker)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit with your values
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# Celery worker (separate terminal)
celery -A zaoapi worker --loglevel=info

# Celery beat (separate terminal)
celery -A zaoapi beat --loglevel=info

# Frontend (separate terminal)
cd client
npm install
npm run dev
```

## Environment Variables

All environment variables are documented in `backend/.env.example`. The critical ones:

| Variable | Purpose | Required |
|----------|---------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `FIELD_ENCRYPTION_KEY` | Fernet key for field-level encryption | Yes |
| `MPESA_CONSUMER_KEY` | M-Pesa Daraja API key | For disbursement |
| `AT_API_KEY` | Africa's Talking API key | For SMS |
| `GOOGLE_API_KEY` | Google AI (Gemini) key | For chatbot |
| `CLOUDINARY_*` | Cloudinary credentials | For file uploads |

## Project Structure

```
zao/
  backend/
    zaoapi/          # Django project settings, urls, wsgi
    apps/
      base/          # Shared models, permissions, utilities
      auth_api/      # Authentication (JWT, 2FA, OTP)
      users/         # User management
      cooperatives/  # Cooperative CRUD and settings
      farmers/       # Farmer profiles and memberships
      deliveries/    # Delivery logging (offline sync)
      grading/       # Quality grading and grade prices
      inventory/     # Stock management
      sales/         # Buyer and sale records
      payment_engine/# Payment computation engine
      deductions/    # Levies, loan repayments, farm input credits
      loans/         # Loan management
      disbursement/  # M-Pesa B2C disbursement
      notifications/ # SMS, USSD, in-app notifications
      statements/    # PDF statements, audit logs
      analytics/     # Dashboard analytics
      chat/          # AI chatbot
      legal/         # Legal document management
      admin/         # Superadmin endpoints
      routes/        # Delivery route management
    manage.py
    requirements.txt
  client/            # React frontend (Vite + Tailwind)
  docs/              # Documentation
    adr/             # Architecture Decision Records
```

## Coding Conventions

### Python / Django

- **Style**: Follow PEP 8. Use `ruff` if available.
- **Formatting**: 4-space indentation, 120 char line limit.
- **Imports**: Standard library first, third-party second, local third. One blank line between groups.
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- **Models**: All models inherit from `CooperativeScopedModel` where applicable. Soft-delete via `deleted_at` field, not hard delete.
- **Serializers**: One serializer per action where possible. Use `ListSerializer`, `DetailSerializer`, `CreateSerializer` suffixes.
- **Views**: Use `CooperativeScopedViewSet` as the base class for cooperative-scoped resources. Override `get_queryset()` and `get_permissions()`.
- **Permissions**: One permission class per role check. Compose with `OR()` where needed.
- **No comments** unless explicitly requested.
- **Type hints**: Encouraged but not enforced.

### React / TypeScript

- **Components**: Functional components only, no class components.
- **State**: React hooks (`useState`, `useEffect`, `useContext`). No Redux — use React Context for global state.
- **Styling**: Tailwind CSS utility classes. No CSS modules or styled-components.
- **Naming**: `PascalCase` for components, `camelCase` for functions/variables, `kebab-case` for CSS classes.
- **File structure**: One component per file. Co-locate tests and styles.

## Branch Naming

| Pattern | Purpose |
|---------|---------|
| `feat/description` | New feature |
| `fix/description` | Bug fix |
| `refactor/description` | Code refactoring |
| `docs/description` | Documentation changes |
| `test/description` | Test additions/fixes |
| `chore/description` | Maintenance tasks |

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes with clear, atomic commits.
3. Write or update tests for any new functionality.
4. Ensure all tests pass: `pytest` (backend) and `npm test` (frontend).
5. Run linting: `ruff check .` (backend) and `npm run lint` (frontend).
6. Open a PR with:
   - A clear title describing the change.
   - A description explaining **what** and **why** (not just how).
   - Reference any related issues.
7. Request review from at least one maintainer.
8. Address review feedback. Do not self-merge.

## Testing

### Backend

```bash
# Run all tests
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Specific app
pytest apps/payment_engine/

# Specific test
pytest apps/payment_engine/tests.py::TestPaymentEngine::test_fixed_price_computation
```

**Test file naming**: `tests.py` in each app, or `tests_<topic>.py` for large test suites.

**Fixtures**: Use `conftest.py` at the project root and app level. Prefer `@pytest.fixture` over factory patterns where possible.

### Frontend

```bash
cd client
npm test              # Run all tests
npm run test:coverage # With coverage
```

### Test Requirements

- All new features must include tests.
- Bug fixes must include a regression test.
- Minimum coverage target: 80% for new code.
- Financial computation code must have 100% coverage.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add farmer CSV import endpoint
fix: correct revenue share computation for single-farmer cycles
refactor: extract payment computation into separate module
docs: update API versioning strategy
test: add grade override tests
chore: update dependencies
```

## Code Review Guidelines

- Review for correctness, security, and maintainability.
- Check that multi-tenancy scoping is correct (cooperative isolation).
- Verify no secrets or credentials are committed.
- Ensure database migrations are reversible where possible.
- Confirm API changes are backward-compatible or versioned.

## Getting Help

- Check `ARCHITECTURE.md` for system design context.
- Check `docs/adr/` for architectural decisions.
- Run `python manage.py find_cascade_orphans` to check for data integrity issues.
- Open an issue for bugs or feature requests.
