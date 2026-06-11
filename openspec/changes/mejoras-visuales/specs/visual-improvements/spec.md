# Visual Improvements Specification

## Purpose

Reference-matching visual redesign of login screen and capturista profile with minimal backend API support, preserving existing auth flow and workflows.

## Domain 1 — Login UI & Video Integration

| Requirement | Description |
|-------------|-------------|
| Two-Column Login Layout | Viewports ≥768px: two columns (branding/form left, video right). <768px: single column, video hidden. |
| Video Asset Integration | Embed `VIDEOLOGIN.mp4` as autoplaying, muted, looping background video in right column. Serve from static assets path. |
| Login Visual Hierarchy | Display logos, heading, form matching reference. Preserve password toggle, JWT storage, role redirects. |

**Scenarios:**
- Desktop: viewport ≥768px → left column (logos, heading, form), right column (video player)
- Mobile: viewport <768px → only left column visible, video hidden/not rendered
- Video loads: plays muted, loops without interaction
- Video fails: right column shows fallback background, form remains functional
- Login success: JWT stored in localStorage, redirect by role (capturista → seleccion-region → socioeconomico)

## Domain 2 — Capturista Profile UI & Data

| Requirement | Description |
|-------------|-------------|
| Profile Stats Cards | Display stat cards: total capturas, completados, pendientes. Each shows numeric counter + label. |
| Year-Filtered Activity Heatmap | Heatmap accepts year selector. Default remains last 365 days for backward compatibility. |
| Last Activity Summary | Display most recent activity date from API. Show "No activity yet" if null. |
| Avatar with Deterministic Fallback | Display avatar image. If no URL: show initials fallback, never broken image. |
| Beneficiary Search and Status Filter | Text search by name/folio + status filter (pending/completed). Reactive updates, no page reload. |

**Scenarios:**
- Stats render: API returns total/completados/pendientes → cards display values
- Zero counters: new user with no capturas → all cards show `0`
- Default range: no selection → heatmap shows the existing last-365-days activity window
- Year selection: user picks 2025 → heatmap refreshes to 2025 data
- Activity present: API returns `last_activity_date` → formatted date displayed
- Activity null: API returns null → "No activity yet" message
- Avatar URL: valid URL → avatar image displayed
- No avatar: null URL → initials fallback, no broken image
- Text search: type "María" → only matching beneficiaries shown
- Status filter: set to "Pendientes" → only pending beneficiaries shown
- Empty search: no matches → empty state message displayed

## Domain 3 — Backend API Support

| Requirement | Description |
|-------------|-------------|
| Profile Stats Extension | `/api/me/perfil` returns `pendientes` count + `last_activity_date`. Backward-compatible. |
| Heatmap Year Filter | `/api/me/heatmap` accepts optional `year` query param. Default remains last 365 days for backward compatibility. |
| Beneficiary Search/Filter | `/api/me/beneficiarios` accepts optional `q` (search) + `status` (filter) params. |

**Scenarios:**
- Extended profile: authenticated capturista with 3 pending → response includes `pendientes: 3` + `last_activity_date`
- Year param: `?year=2025` → only 2025 activity data returned
- Combined filter: `?q=Mar&status=borrador` → only draft/pending beneficiaries matching "Mar"

## Domain 4 — Cross-Cutting Constraints

| Requirement | Description |
|-------------|-------------|
| Auth and Session Preservation | Visual changes MUST NOT alter JWT handling, session keys (`session`, `region_ctx`), token expiry, or role redirects. |
| Responsive Behavior | Fully functional on viewports 320px–1920px. No horizontal scrolling. |
| Performance Budget | Login with video: interactive within 5s on 4G. Video ≤5MB recommended. |
| Accessibility | Form inputs have labels. Keyboard-navigable. WCAG 2.1 AA color contrast. |

**Scenarios:**
- Session intact: logged-in user → `localStorage.session` unchanged, Bearer token in API calls
- 320px viewport: all content accessible without horizontal scroll
- 4G login: form interactive within 5 seconds
- Keyboard nav: Tab moves through email → password → toggle → submit
