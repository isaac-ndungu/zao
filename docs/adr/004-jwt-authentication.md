# ADR-004: JWT Authentication with HTTP-Only Cookie Refresh

**Status:** Accepted  
**Date:** 2026-01-20  
**Deciders:** Backend team

## Context

We need stateless authentication that works across the Django API, React frontend, and USSD webhook callbacks. We need short-lived access tokens, secure refresh without exposing tokens to JavaScript, 2FA for sensitive roles on new device logins, and token blacklisting for logout.

## Decision

We chose `djangorestframework-simplejwt` with:
- **Access tokens**: 15-minute expiry, stored in React state (memory).
- **Refresh tokens**: 7-day expiry, stored in HTTP-only cookies (not accessible to JavaScript).
- **Token blacklisting**: Redis-backed blacklist for logout and admin session revocation.
- **2FA**: Email OTP for Accountant and Manager roles on new device detection.

## Alternatives Considered

- **Session-based auth (Django sessions):** Simpler, but requires CSRF tokens, doesn't work well with the React SPA pattern, and makes USSD webhook auth harder (no browser session).
- **OAuth 2.0 with external IdP:** Overkill for the current scale. Adds dependency on external service availability.
- **API keys:** Stateless but no expiry, no refresh mechanism, harder to revoke.
- **JWT with localStorage refresh:** Vulnerable to XSS — if the React app has a stored XSS vulnerability, the refresh token is stolen.

## Consequences

**Positive:**
- Stateless access tokens enable horizontal scaling without session storage.
- HTTP-only cookie refresh prevents XSS token theft.
- 15-minute access token expiry limits blast radius of compromised tokens.
- Redis-backed blacklist enables instant logout (blacklist the refresh token).
- `must_change_password` gate forces password change on admin reset.
- Legal acceptance gate blocks unauthenticated API access until ToS accepted.

**Negative:**
- 15-minute token expiry requires frequent refresh — the frontend must handle 401 → refresh → retry transparently.
- HTTP-only cookies can't be read by JavaScript, making debugging harder.
- Token blacklist in Redis adds a network hop to every authenticated request (mitigated by short TTL).
- Cross-origin cookie handling requires careful CORS configuration (`CORS_ALLOW_CREDENTIALS=True`).
