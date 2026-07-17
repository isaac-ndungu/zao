# ADR-003: Dual-Entry-Point Frontend Architecture

**Status:** Accepted (updated)
**Original Date:** 2026-02-01
**Updated:** 2026-07-17
**Deciders:** Frontend team

## Context

We serve two fundamentally different user populations:

1. **Cooperative staff** who need role-specific dashboards with complex data tables, charts, and multi-step workflows. Roles include: admin (super-admin), manager, grader, accountant, auditor, and external auditor.
2. **Farmers** who need a simple mobile-first portal to view their delivery history, grade breakdowns, payment statements, and loan status.

These populations have different design complexity, different deployment surfaces (staff use desktop browsers, farmers use mobile browsers), and different feature velocity (admin features change weekly, farmer features are stable).

## Decision

We use a **single Vite monorepo** (`client/`) with **two HTML entry points**, producing two separate JavaScript bundles:

- `client/index.html` → Staff SPA — contains all staff roles (admin, manager, grader, accountant, auditor, external-auditor) in a single app, each gated by `<RoleGuard>`.
- `client/farmer/index.html` → Farmer SPA — a standalone, lightweight mobile portal with its own routing and auth.

Both share:
- A common `src/shared/` library: API client, auth helpers, UI components (ErrorBoundary, RoleGuard, ChatWidget, SearchBar, MapView, etc.), Tailwind CSS theme tokens, and React Query provider.
- The same authentication model (JWT + HTTP-only cookie refresh).
- Identical design tokens and component patterns.

### Route structure

**Staff SPA** (`src/App.jsx`):
| Path prefix | Role |
|---|---|
| `/admin/*` | super-admin (admin-guarded) |
| `/manager/*` | manager |
| `/grader/*` | grader |
| `/accountant/*` | accountant |
| `/auditor/*` | internal auditor |
| `/external-auditor/*` | external auditor |
| `/farmer/*` | farmer (duplicated here for SSO/admin impersonation) |

**Farmer SPA** (`src/farmer/App.jsx`):
| Path prefix | Role |
|---|---|
| `/farmer/*` | farmer |

The farmer routes exist in **both** SPAs. The standalone farmer entry (`farmer/index.html`) is the primary production entry for farmers, keeping their bundle lightweight. The main SPA includes farmer routes to support admin impersonation and SSO flows without redirecting to a different origin.

### Build configuration

Vite `rollupOptions.input` defines both entry points. Shared `node_modules` are split into manual chunks (`vendor-react`, `vendor-recharts`, `vendor-leaflet`, `vendor-query`, `vendor-date`, `vendor-misc`) to maximize cache efficiency across both bundles.

## Alternatives Considered

- **Clean two-SPA split (original ADR):** Would have kept farmer and staff as fully independent apps. Rejected because farmer routes in the staff SPA enable admin impersonation and SSO without cross-origin redirects. Also avoids duplicating shared infrastructure in separate repos.
- **Single SPA with role-based routing:** Simpler deployment, but mixes concerns. Admin routes bloat the farmer bundle. A farmer loading the main app downloads staff code they will never use.
- **Micro-frontends (Module Federation):** Overkill for our scale. Adds build complexity and runtime coordination overhead.

## Consequences

**Positive:**
- Farmer portal stays lightweight via the standalone entry point — fast on 3G connections.
- Staff SPA can use heavy libraries (Recharts, Leaflet) without affecting the standalone farmer bundle.
- Shared `src/shared/` library eliminates duplication of components, hooks, API clients, and utilities.
- Admin impersonation of farmers works without cross-origin redirects.
- Vite manual chunking ensures vendor libraries are cached efficiently across both bundles.

**Negative:**
- Farmer code exists in two places (standalone SPA and staff SPA), creating a maintenance surface — changes to farmer pages must be tested in both entry points.
- The staff SPA bundle includes all 6 staff roles plus farmer routes, making it significantly larger than the original "two lightweight SPAs" vision.
- Shared authentication logic must be kept in sync between the farmer auth context and the staff auth context.
- Two `index.html` entry points add minor build complexity (Vite handles this natively via `rollupOptions.input`).
