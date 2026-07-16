# ADR-003: Dual-SPA Frontend Architecture

**Status:** Accepted  
**Date:** 2026-02-01  
**Deciders:** Frontend team

## Context

We serve two fundamentally different user populations:
1. **Cooperative staff** (managers, accountants, graders, auditors) who need a full-featured admin dashboard with complex data tables, charts, and multi-step workflows.
2. **Farmers** who need a simple portal to view their delivery history, grade breakdowns, payment statements, and loan status.

These populations have different design complexity, different deployment surfaces (staff use desktop browsers, farmers use mobile browsers), and different feature velocity (admin features change weekly, farmer features are stable).

## Decision

We built two separate React single-page applications sharing a common component library:

- `client/` — Admin Dashboard (staff-facing)
- `client/farmer/` — Farmer Portal (farmer-facing)

Both share:
- The same API client layer
- The same authentication flow (JWT + HTTP-only cookie refresh)
- Common UI components (tables, forms, modals)
- Tailwind CSS theme tokens

## Alternatives Considered

- **Single SPA with role-based routing:** Simpler deployment, but mixes concerns. Admin routes bloat the farmer bundle. A farmer loading the app downloads admin code they will never use. Feature flags for role-based route gating add complexity.
- **Micro-frontends (Module Federation):** Overkill for a two-consumer app. Adds build complexity and runtime coordination overhead.

## Consequences

**Positive:**
- Farmer portal stays lightweight (<100KB gzipped) — fast on 3G connections.
- Admin dashboard can use heavy libraries (Recharts, complex form libraries) without affecting farmer performance.
- Independent deployment: farmer portal changes don't require admin dashboard redeployment.
- Clear separation of concerns: farmer UI stays simple by design.

**Negative:**
- Some component duplication between the two apps (mitigated by shared component library).
- Two build pipelines instead of one.
- Shared authentication logic must be kept in sync manually.
