# Proposal: Borrador Maestro — Master Draft Save

## Intent

Capturistas currently save each form (socioeconomico, tecnica, gestion) separately via per-form buttons. The PRD (RF-01, RF-02) requires a single "Guardar Borrador" button that persists ALL three forms atomically in one action. Draft mode must accept empty fields (no completeness check) but reject invalid format (regex, catalogs, ranges per VALIDATION_RULES.md). This change adds the master save endpoint and frontend orchestration to collect + validate + persist all form data together.

## Scope

### In Scope
- Backend: `POST /api/guardar-borrador` — creates/updates beneficiario + estudio + solicitud in one transaction with `status='borrador'`, format-only validation
- Backend: `GET /api/borrador/{id}` — returns full draft data (all 3 forms) for editing resumption
- Frontend: Master "Guardar Borrador" button visible from all 3 tabs, collects all form data and POSTs atomically
- Frontend: Format-only validation mode for drafts (skip required checks, enforce regex/catalog/range rules)
- Frontend: Success/error toast messages per RF-06
- Frontend: Draft restoration — clicking pencil on "En borrador" record loads all 3 forms with saved data

### Out of Scope
- Auto-save on tab navigation
- Version history for drafts
- Notifications/reminders for pending drafts
- Admin or tecnico editing of drafts (drafts are capturista-exclusive)
- "Finalizar Registro" button (already in borradores-v2 change)

## Capabilities

### New Capabilities
- `guardar-borrador`: Atomic endpoint that accepts all 3 forms data, validates format only (empty fields OK, invalid format rejected), persists as `status='borrador'`, and returns unified draft ID for later resumption
- `draft-resume`: Endpoint or flow to load a full draft (all 3 forms) for re-editing from perfil-capturista

### Modified Capabilities
- `draft-flow`: Existing per-form localStorage saves become secondary to the master save; the master button replaces individual save buttons (individual saves may remain for incremental UX but are not the primary flow)

## Approach

1. **New Pydantic model** `BorradorMaestroRequest` with optional fields across all 3 forms (beneficiario, tutores, estudio, solicitud). Validators run only on non-empty values — `None`/empty strings skip validation.
2. **New endpoint** `POST /api/guardar-borrador` that upserts beneficiario + estudio + solicitud in a single DB transaction. If no IDs provided, creates new records; if IDs provided, PATCHes existing ones.
3. **New endpoint** `GET /api/borrador/{estudio_id}` returns beneficiario + estudio + solicitud + tutores as a single payload for draft resumption.
4. **Frontend**: Add "Guardar Borrador" master button to all 3 tab pages. On click: collect all form data from DOM, run format-only validation, POST to endpoint, show toast.
5. **Frontend**: On perfil-capturista pencil click → store draft IDs in localStorage → redirect to socioeconomico.html → each form loads from `GET /api/borrador/{id}`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/routers/borrador.py` | New | Master draft save + resume endpoints |
| `backend/main.py` | Modified | Register new router |
| `front/Capturista-view/socioeconomico.html` | Modified | Add master button, draft restore from API |
| `front/Capturista-view/tecnica.html` | Modified | Add master button, draft restore from API |
| `front/Capturista-view/gestion.html` | Modified | Add master button, draft save orchestration |
| `front/Capturista-view/perfil-capturista.html` | Modified | Draft resumption via pencil click |
| `backend/validators.py` | Modified | Draft-mode validation helpers (skip required, enforce format) |
| `backend/tests/test_borrador.py` | New | Unit + integration tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Large request payload (3 forms) may exceed body limits | Low | Pydantic model is ~50 fields; well within limits |
| Frontend state sync — user edits tab 1, switches to tab 2 without saving tab 1 | Medium | All form data collected from DOM at save time; localStorage drafts used for tab state |
| Draft restore loads stale data if another session edited same record | Low | Optimistic locking via `updated_at` timestamp check |

## Rollback Plan

- Remove `backend/routers/borrador.py` and router registration in `main.py`
- Remove "Guardar Borrador" buttons from all 3 HTML pages
- Revert perfil-capturista.html pencil click to previous behavior
- Delete `backend/tests/test_borrador.py`
- No schema changes (reuses existing `status` column)

## Dependencies

- VALIDATION_RULES.md must be the single source of truth for format rules
- Existing `estatus='borrador'` support on estudios_socioeconomicos and solicitudes_tecnicas
- borradores-v2 change (Finalizar Registro) must be implemented or co-implemented

## Success Criteria

- [ ] `POST /api/guardar-borrador` saves all 3 forms atomically with format-only validation
- [ ] Empty fields are accepted for drafts; invalid format fields are rejected with field-level errors
- [ ] `GET /api/borrador/{id}` returns complete draft data for all 3 forms
- [ ] Master "Guardar Borrador" button appears on all 3 tabs and saves all data in one action
- [ ] Draft resumption from perfil-capturista loads all 3 forms with saved data
- [ ] Success/error toasts display correctly per RF-06
- [ ] All tests pass (pytest) covering: empty draft, partial draft, format rejection, atomicity