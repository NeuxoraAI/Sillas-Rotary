# Proposal: Visual Improvements

## Intent

Align the login screen and capturista profile with the approved visual references while preserving the current auth flow, roles, navigation, and field-worker workflows.

## Scope

### In Scope
- Redesign `front/login.html` to match `REFERENCIAS/Ref_login.jpeg`, including responsive split layout, video panel using `REFERENCIAS/VIDEOLOGIN.mp4`, logos, hierarchy, form behavior, and mobile fallback.
- Redesign `front/Capturista-view/perfil-capturista.html` to match `REFERENCIAS/Ref_perfil_capturista.jpeg`, including profile cards, counters, activity area, beneficiary list, search/filter, avatar fallback, buttons, and badges.
- Add only minimal backend/API support required for displayed profile data.

### Out of Scope
- Auth-flow rewrites, role changes, database ownership changes, or unrelated dashboard features.
- Modifying files under `REFERENCIAS/`.
- Adding a frontend framework or migrating away from Tailwind CDN unless implementation proves it necessary.

## Capabilities

### New Capabilities
- `visual-improvements`: Reference-matching visual behavior for the login screen and capturista profile.

### Modified Capabilities
- None.

## Approach

Keep the change presentation-focused: update the two target frontend screens against the references, preserve existing login validation/JWT storage/role redirects, and extend or reuse profile APIs only where real displayed data requires it.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `front/login.html` | Modified | Reference-matching login UI and video integration. |
| `front/Capturista-view/perfil-capturista.html` | Modified | Reference-matching profile UI and data rendering. |
| `backend/routers/perfiles.py` | Modified | Profile stats, activity, and beneficiaries support as needed. |
| `backend/init_db.py` / migrations | Conditional | Avatar field only if no existing column can safely provide it. |
| `assets/` or equivalent static path | New/Modified | Safe video/static asset placement if required. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| “Exactly like” is subjective without pixel specs | Medium | Use reference-driven visual checks and keep behavior unchanged. |
| Video increases load time | Medium | Use compressed/static delivery, lazy loading, or mobile fallback. |
| Backend changes affect existing profile data | Low | Preserve response compatibility and add targeted tests. |

## Rollback Plan

Revert the visual screen changes and any minimal API/schema additions for this change; restore previous frontend markup and profile API response shape if needed.

## Dependencies

- Existing reference files in `REFERENCIAS/` remain available and unchanged.
- Current auth/session behavior remains stable.

## Success Criteria

- [ ] Login visually matches `Ref_login.jpeg` on desktop and remains usable on mobile.
- [ ] `VIDEOLOGIN.mp4` appears in the login design without breaking login flow.
- [ ] Capturista profile visually matches `Ref_perfil_capturista.jpeg` and preserves auth protection.
- [ ] Profile counters, year activity, last activity, avatar fallback, and beneficiary search/filter work with real API data.
- [ ] No unrelated UX, auth, role, or navigation changes are introduced.
