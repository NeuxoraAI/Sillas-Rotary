# Tasks: Visual Improvements

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 550-750 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | force-chained |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Backend profile payload + filters | PR 1 | Base = feature/tracker branch; include API tests/rollback notes. |
| 2 | Login split layout + static video asset | PR 2 | Base = PR 1 branch; desktop/mobile verification, no auth changes. |
| 3 | Capturista profile UI refresh | PR 3 | Base = PR 2 branch; connect counters, year filter, search, avatar fallback. |

## Phase 1: Foundation / API Contract

- [x] 1.1 Update `backend/routers/perfiles.py` to return `pendientes`, `last_activity_date`, and compatible `avatar_url` in `/api/me/perfil`.
- [x] 1.2 Extend `backend/routers/perfiles.py` to accept `year` on `/api/me/heatmap` and `q`/`status` on `/api/me/beneficiarios`.
- [x] 1.3 Update `backend/init_db.py` only if needed to initialize `usuarios.avatar_url` without breaking existing rows.

Note: `backend/init_db.py` DDL remains intentionally unqualified because runtime/test schema selection is controlled by the connection `search_path`; forcing `public.` would break isolated test-schema initialization.

## Phase 2: Login Visual Redesign

- [x] 2.1 Rewrite `front/login.html` into the reference-driven two-column layout with video on desktop and stacked mobile fallback.
- [x] 2.2 Add `front/assets/video/VIDEOLOGIN.mp4` as the static video source and keep the form fully functional if video fails.
- [x] 2.3 Preserve password toggle, JWT storage, and role redirects exactly as before.

## Phase 3: Capturista Profile UI Wiring

- [ ] 3.1 Redesign `front/Capturista-view/perfil-capturista.html` to match the reference cards, counters, avatar, and action areas.
- [ ] 3.2 Wire year selector, beneficiary search, and status filter to the updated API params without page reloads.
- [ ] 3.3 Add deterministic avatar fallback and empty-state handling for no activity / no beneficiary matches.

## Phase 4: Verification / Cleanup

- [x] 4.1 Add/adjust backend tests for `/api/me/perfil`, `/api/me/heatmap?year=YYYY`, and beneficiary search/filter scenarios.
- [ ] 4.2 Verify login and profile responsiveness at 320px, 768px, and desktop; confirm no horizontal scroll or auth/session regressions.
- [ ] 4.3 Document rollback boundaries: revert frontend markup first, then API/schema additions if review fails.
