# Tasks: borrador-maestro (Master Draft Save)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 600–750 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: backend → PR 2: frontend → PR 3: tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend: validate_optional + guardar_borrador.py + router registration | PR 1 | base: main; ~270 lines |
| 2 | Frontend: "Guardar Borrador" button on 3 forms + profile draft-resume | PR 2 | base: main (after PR 1); ~210 lines |
| 3 | Tests: unit + integration for validate_optional, POST, GET, ownership | PR 3 | base: main (after PR 2); ~200 lines |

## Phase 1: Backend Foundation

- [ ] 1.1 Add `validate_optional()` wrapper to `backend/validators.py` — accepts a validator callable, returns a new function that skips validation when value is `None` or `""`, delegates to the original validator otherwise
- [ ] 1.2 Create `backend/routers/guardar_borrador.py` with `GuardarBorradorRequest` Pydantic model — all fields Optional; use `validate_optional` for format-only draft validation
- [ ] 1.3 Add `POST /api/guardar-borrador` endpoint — atomic CREATE (BEGIN→INSERT beneficiario+estudio+solicitud→COMMIT) or UPDATE mode when `estudio_id` provided; return `{estudio_id, solicitud_id, beneficiario_id, folio, status}`
- [ ] 1.4 Add `GET /api/borrador/{estudio_id}` endpoint — owner-only access (403 for non-owner), 404 for non-borrador status; return full payload (beneficiario + estudio + solicitud + tutores)
- [ ] 1.5 Register router in `backend/main.py` — add `app.include_router(guardar_borrador.router, prefix="/api")`

## Phase 2: Frontend Implementation

- [ ] 2.1 Add "Guardar Borrador" button to `front/Capturista-view/socioeconomico.html` — amber-styled, capturista-only; on click collect DOM data, merge localStorage drafts, POST to `/api/guardar-borrador`; show toast on success/error; save `estudio_id` to localStorage on success
- [ ] 2.2 Add "Guardar Borrador" button to `front/Capturista-view/tecnica.html` — same pattern; collect solicitud DOM fields + merge socioecon/gestion from localStorage
- [ ] 2.3 Add "Guardar Borrador" button to `front/Capturista-view/gestion.html` — same pattern; extend existing localStorage merge (lines 668-674) to include all 3 forms
- [ ] 2.4 Wire draft-resume in `front/Capturista-view/perfil-capturista.html` — pencil click on borrador record sets `localStorage.estudio_id`, navigates to `socioeconomico.html?estudio_id={id}`
- [ ] 2.5 Add draft-resume loader to `front/Capturista-view/socioeconomico.html` — on page load, if `estudio_id` param or localStorage, call `GET /api/borrador/{id}`, populate localStorage for all 3 forms, fill current page DOM

## Phase 3: Testing

- [ ] 3.1 Unit test `validate_optional` in `backend/tests/test_validators.py` — test with None, empty string, and valid values for each validator type (string, int, catalog)
- [ ] 3.2 Integration test POST `/api/guardar-borrador` CREATE mode in `backend/tests/test_guardar_borrador.py` — all null fields → 201 with folio; partial valid data → 201; format validation rejects with 422
- [ ] 3.3 Integration test POST `/api/guardar-borrador` UPDATE mode — existing borrador estudio_id → PATCH all 3 records atomically; verify 201 response
- [ ] 3.4 Integration test GET `/api/borrador/{estudio_id}` — owner gets 200 with full payload; non-owner gets 403; non-borrador status gets 404; unauthenticated gets 401
- [ ] 3.5 Integration test ownership/permissions — tecnico role gets 403; admin role can access any borrador; verify `assert_resource_owner` integration