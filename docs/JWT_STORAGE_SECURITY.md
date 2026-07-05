# JWT Storage Security Decision

This project keeps JWT access tokens in `localStorage` for the current web app, but treats that as an accepted short-term risk, not as the final security posture.

## Decision

| Topic | Decision |
|------|----------|
| Current storage | Keep `localStorage['session'] = { token, nombre, rol, usuario_id }` for now. |
| Risk status | Accepted short-term risk because any XSS can read the bearer token. |
| Target posture | Migrate to `httpOnly`, `Secure`, `SameSite` cookies with CSRF protection when the backend/frontend auth boundary is intentionally redesigned. |
| Required mitigation while localStorage remains | Harden CSP, remove unnecessary third-party scripts, keep strict sanitization, and review token lifetime by role. |

This is a deliberate decision for Issue #115. It avoids a risky half-migration where cookies are introduced without CSRF design, logout semantics, local/mobile QA, and same-origin deployment guarantees.

## Current Flow

1. `POST /api/auth/login` returns `access_token`, `rol`, `nombre`, and `usuario_id`.
2. `front/login.html` stores the token in `localStorage['session']`.
3. `front/assets/js/session-guard.js` reads `localStorage['session']` and builds `Authorization: Bearer <token>`.
4. `front/assets/js/apiClient.js` attaches that header to protected API requests.
5. `backend/routers/auth.py` validates HS256 JWTs with `JWT_EXPIRE_HOURS`, defaulting to 8 hours.

## Risk

If an attacker lands JavaScript in the page through XSS, the attacker can read `localStorage['session'].token` and impersonate the user until the token expires or the user is deactivated.

The highest-impact roles are:

| Role | Impact If Token Is Stolen |
|------|----------------------------|
| `admin` | User, region, organization, and beneficiary administration. |
| `organizacion` | Captures and organization-scoped records. |
| `capturista` | Beneficiary and study draft/completion records. |
| `tecnico` | Technical workflow and review actions. |

## Required Mitigations While Using localStorage

| Area | Requirement |
|------|-------------|
| CSP | Add a production `Content-Security-Policy` after inline scripts and CDN Tailwind are removed or nonce/hash-managed. The target policy must include `default-src 'self'`, a restricted `script-src`, and no broad wildcard script sources. |
| Sanitization | Any value interpolated into `innerHTML`, attributes, or template strings must go through the shared escaping/sanitization helper. No new local partial `_esc()` implementations. |
| Third-party scripts | No new third-party scripts may be added to authenticated pages unless the PR explains why they need access to pages that can read tokens. |
| Current third-party inventory | Authenticated pages currently load Tailwind from `https://cdn.tailwindcss.com` and fonts/icons from Google Fonts. Tailwind CDN is development-oriented and must be replaced by built/static CSS before strict CSP enforcement. |
| Token lifetime | Keep `JWT_EXPIRE_HOURS` configurable. Review lowering admin and organization session lifetime before adding privileged destructive flows. |
| Logout/deactivation | Logout must remove `localStorage['session']`; backend must continue rejecting inactive users on every authenticated request. |

## Cookie Migration Plan

Do not switch only the storage location. A safe cookie migration must be a complete auth design change:

1. Backend sets access/session cookie with `HttpOnly`, `Secure`, `SameSite=Lax` or stricter.
2. State-changing endpoints require CSRF protection, such as a synchronizer token or double-submit token.
3. Frontend `ApiClient` sends credentials intentionally and no longer manually injects bearer tokens.
4. Logout clears the cookie server-side and client-side session state.
5. Mobile/tablet QA validates field-worker flows across reloads, offline-ish drafts, and role redirects.
6. Tests cover login, logout, CSRF failure, CSRF success, inactive-user rejection, and cross-role access.

## Review Checklist

Use this checklist on PRs that touch auth, session handling, shared rendering helpers, or external scripts:

- [ ] Does the change keep `localStorage['session']` limited to the current session object only?
- [ ] Does the change avoid adding third-party scripts to authenticated pages?
- [ ] Are any `innerHTML` insertions escaped or generated from trusted static markup?
- [ ] Does the change preserve server-side role checks instead of relying only on frontend redirects?
- [ ] If auth storage changes, does the PR include a CSRF design and tests?

## Next Step

Before enabling a strict CSP in production, replace Tailwind CDN usage with built CSS or add a nonce/hash-based policy that covers existing inline scripts without allowing arbitrary script execution.
