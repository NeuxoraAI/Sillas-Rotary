# Proposal: Borradores v2 — Finalizar Registro

## Intent

Enable capturistas to finalize a full registration (socioeconomico + tecnica + gestion) in a single atomic action via a master "Finalizar Registro" button, and prevent editing of completed records. Implements PRD_Borradores_Donacion_Sillas_v2.md using Opcion B (minimal viable: keep 3 separate HTML pages, keep existing schema).

## Scope

### In Scope
- Backend: `POST /api/finalizar-registro` router — atomically validates + finalizes both estudio and solicitud
- Frontend: "Finalizar Registro" button in `gestion.html` that validates all 3 steps before calling the endpoint
- Frontend: Disable/hide edit pencil for `status='completo'` records in `perfil-capturista.html`
- Tests: pytest unit + integration tests for the new endpoint and completion logic

### Out of Scope
- Tab unification (keeping 3 separate HTML pages)
- Separate borradores table (reusing `status='borrador'/'completo'` on existing tables)
- Auto-save on tab navigation
- Version history for drafts
- Notifications/reminders for pending drafts
- Admin or tecnico editing of completed records (already exists)

## Capabilities

### New Capabilities
- `finalizar-registro`: Atomic endpoint that validates completeness of all 3 forms and transitions both estudio and solicitud from borrador to completo in a single DB transaction

### Modified Capabilities
- `draft-flow`: Existing draft save/resume flow gains finalization gate — "Guardar Borrador" remains per-step, "Finalizar Registro" is the master completion button
- `perfil-capturista`: Edit pencil visibility changes — disabled for status=completo, enabled for status=borrador

## Approach

1. **New router** `backend/routers/finalizar.py` with `POST /api/finalizar-registro` that:
   - Accepts `{estudio_id, solicitud_id}` (from localStorage)
   - Validates ALL required fields across beneficiario, tutores, estudio, and solicitud using VALIDATION_RULES.md completeness rules
   - Opens DB transaction → PATCHes both records to `status='completo'` or rolls back on any validation failure
   - Returns 200 with confirmation or 422 with field-level errors

2. **Frontend `gestion.html`**: Add "Finalizar Registro" button alongside existing "Guardar Borrador". On click:
   - Validate frontend-side completeness for all 3 forms
   - If valid, POST `/api/finalizar-registro`
   - On success: clear localStorage draft IDs, redirect to perfil-capturista
   - On error: display field-level error messages

3. **Frontend `perfil-capturista.html`**: Gate the edit pencil icon on `can_edit = (status === 'borrador')`. Completed records show no pencil for capturista role.

4. **Tests**: TDD — write failing tests first, then implement.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routers/finalizar.py` | New | Atomic finalization endpoint |
| `backend/main.py` | Modified | Register new router |
| `front/Capturista-view/gestion.html` | Modified | Add "Finalizar Registro" master button + JS logic |
| `front/Capturista-view/perfil-capturista.html` | Modified | Gate edit pencil on borrador status |
| `backend/tests/test_finalizar.py` | New | Unit + integration tests for finalization |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Transaction rollback scope — estudio fails after solicitud succeeds (or vice versa) | Low | Single DB transaction wraps both PATCHes; atomicity guaranteed |
| Frontend validation diverges from backend VALIDATION_RULES.md | Medium | Frontend calls validation functions already in validations.js; backend is SSoT |
| localStorage draft IDs stale after finalization | Medium | Clear estudio_id + solicitud_id from localStorage on success |
| Capturista hits "Finalizar" with partial data in earlier steps | Low | Frontend collects + validates ALL steps before POST; returns field-level 422 |

## Rollback Plan

- Remove `POST /api/finalizar-registro` router and its registration in `main.py`
- Remove "Finalizar Registro" button from `gestion.html`
- Revert edit pencil logic in `perfil-capturista.html` to original behavior
- Delete `backend/tests/test_finalizar.py`
- No schema changes needed (reuses existing `status` column)

## Dependencies

- VALIDATION_RULES.md (docs/) must remain the single source of truth
- Existing `status='borrador'` PATCH endpoints must work correctly (already implemented)
- localStorage must hold valid `estudio_id` and `solicitud_id` (already established)

## Success Criteria

- [ ] `POST /api/finalizar-registro` atomically marks both records completo or rolls back
- [ ] "Finalizar Registro" button validates all 3 forms client-side before POST
- [ ] Completed records hide edit pencil for capturista in perfil-capturista.html
- [ ] All tests pass (pytest) covering: success path, partial-data rejection, atomicity, role gate
- [ ] No changes to DB schema