# Tasks: Borradores v2 — Finalizar Registro

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~780 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend) → PR 2 (frontend) |
| Delivery strategy | ask-always |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend: migration + models + endpoint + tests | PR 1 | Base: feature/borradores-v2; TDD: RED→GREEN per task |
| 2 | Frontend: gestion.html button + perfil pencil gate | PR 2 | Base: PR 1 branch; depends on PR 1 API |

## Dependency Graph

```
1.1 ──► 1.2 ──► 2.1 ──► 2.2 ──► 2.3 ──► 2.4 ──► 2.5 ──► 3.1
                                                        │
                                                        └──► 3.2
                                                         └──► 4.1 ──► 4.2 ──► 4.3
```

## Phase 1: Foundation / Infrastructure

- [x] 1.1 Create `migrations/add_finalizado_at.sql` — ALTER TABLE both `estudios_socioeconomicos` and `solicitudes_tecnicas` ADD COLUMN `finalizado_at TIMESTAMPTZ NULL`. Run migration against DB. (~15 lines)
- [x] 1.2 Create `backend/routers/finalizar.py` skeleton with Pydantic models: `FinalizarRegistroRequest(estudio_id: int, solicitud_id: int)` and `FinalizarRegistroResponse(estudio_id, solicitud_id, status, finalizado_at, already_completed: bool = False)`. (~30 lines)

## Phase 2: Core Backend (TDD)

- [x] 2.1 **RED** — Write failing test in `backend/tests/test_finalizar.py`: test `_validate_all_complete()` returns missing-field list when estudio row lacks `fecha_estudio`. (~60 lines)
- [x] 2.2 **GREEN** — Implement `_validate_all_complete(estudio_row, solicitud_row, beneficiario_row, tutores_rows)` in `finalizar.py`. Returns list of `{form, field}` dicts per VALIDATION_RULES.md + existing Pydantic validators. (~80 lines)
- [x] 2.3 **RED** — Write failing tests in `test_finalizar.py`: (a) happy path → 200 both `completo`, (b) missing fields → 422 with `detail.missing[]`, (c) tecnico role → 403, (d) non-owner capturista → 403, (e) already completo → 200 idempotent. (~150 lines)
- [x] 2.4 **GREEN** — Implement `POST /api/finalizar-registro` in `finalizar.py`: `require_roles("capturista","admin","organizacion")`, `assert_resource_owner` on both records, idempotency early-exit, BEGIN → validate → UPDATE both → COMMIT, structured 422 on missing. (~120 lines)
- [x] 2.5 Register router: add `from routers import finalizar` in `backend/main.py` + `app.include_router(finalizar.router, prefix="/api")`. (~5 lines)

## Phase 3: Frontend

- [x] 3.1 Modify `front/Capturista-view/gestion.html` — Add "Finalizar Registro" button (role-gated), `finalizarRegistro()` JS: pre-check via GET estudios + solicitudes, validate all 3 forms, POST `/api/finalizar-registro`, success toast + clear localStorage + redirect to perfil-capturista, error toast per PRD RF-06. (~120 lines)
- [x] 3.2 Modify `front/Capturista-view/perfil-capturista.html` — Gate edit pencil: hide when `status === 'completo'` for capturista/organizacion roles. Verify status badge: amber "En borrador" / green "Completo". (~20 lines)

## Phase 4: Integration Verification

- [x] 4.1 Integration test in `test_finalizar.py`: full happy path — create pais+region+beneficiario+estudio+solicitud as borrador, call `/api/finalizar-registro`, assert both status='completo' + `finalizado_at` set. (~60 lines)
- [x] 4.2 Integration test: error paths — (a) incomplete estudio fields → 422 with `detail.missing[]`, (b) tecnico JWT → 403, (c) different capturista JWT → 403. (~80 lines)
- [x] 4.3 Integration test: idempotency — finalize once, finalize again, assert 200 + `already_completed=true` + no second `finalizado_at` update. (~40 lines)
- [x] 4.4 Manual validation checklist: toast messages per RF-06, button visibility by role, redirect flow, pencil hidden for completo, amber/green badges. — _Requires manual E2E validation (no E2E test runner available)_.
