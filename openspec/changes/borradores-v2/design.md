# Design: Finalizar Registro — borradores-v2

## Technical Approach

Atomic single-action finalization via a new `POST /api/finalizar-registro` endpoint that transitions both `estudios_socioeconomicos` and `solicitudes_tecnicas` from `borrador` to `completo` in one DB transaction. The backend is the single source of truth for completeness validation; the frontend performs a fast pre-check before calling the endpoint.

---

## Architecture Decisions

### Decision 1: Transaction scope — single request, explicit BEGIN

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `get_db` auto-commit (existing pattern) | Multiple statements in one request auto-commit together — but we need explicit BEGIN so rollback works mid-request | Use `db._conn.execute("BEGIN")` manually inside the endpoint, then `db.commit()` on success or let the exception propagate to trigger `get_db`'s auto-rollback |
| Sub-function with `get_db_ctx()` | Separates transaction from FastAPI dependency; clean | Alternative, but requires refactoring `get_db` override in tests |
| Two-phase commit (two PATCHes in parallel) | Current `gestion.html` pattern — not atomic | Rejected — the whole point is atomicity |

**Rationale**: `_DBAdapter.commit()` and `_DBAdapter.rollback()` exist and are callable. `get_db` only auto-commits after the handler returns, so manual `BEGIN` + `db.commit()` inside the handler gives us explicit transaction control. If an exception escapes, `get_db`'s `finally` block runs `rollback()` automatically.

### Decision 2: Validation strategy — reuse Pydantic, add a finalizer function

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Reuse `EstudioUpdateRequest(status='completo')` and `SolicitudUpdateRequest(status='completo')` via their existing `model_validator` `/_validar_completo_t1/t2` | These already enforce completeness rules when `status='completo'` is set — no duplication | Use these models directly via their existing validators |
| Create new `FinalizarRequest` Pydantic model | Duplicates validation logic from the two existing models | Rejected — adds maintenance burden |
| Custom `validate_completeness()` function that inspects DB rows directly | More flexible, decoupled from Pydantic, works for already-fetched rows | Used as a pre-flight check before Pydantic validation |

**Implementation**: `finalizar.py` fetches both records from DB, runs a custom `_validate_all_complete()` function that checks all required fields per VALIDATION_RULES.md, then calls `EstudioUpdateRequest(status='completo', ...existing_fields)` and `SolicitudUpdateRequest(status='completo', ...existing_fields)` to trigger the built-in validators. If any Pydantic validation fails, the exception causes the transaction to rollback.

**Completeness rules** (from `validators.py` + existing `model_validator` in both UpdateRequest):
- `EstudioUpdateRequest._validar_completo_t1`: requires `fecha_estudio`, `tuvo_silla_previa`, `como_obtuvo_silla` (conditional)
- `SolicitudUpdateRequest._validar_completo_t2`: requires all 7 `medida_*` fields
- Additional: `beneficiario` required fields (nombres, apellido_paterno, apellido_materno, fecha_nacimiento, diagnostico, calle, colonia, ciudad, estado_codigo, sexo, telefonos)
- `tutores`: Tutor 1 required fields (edad, nivel_estudios, estado_civil, vivienda, imss_estatus, infonavit_estatus), plus conditional employment fields

### Decision 3: Timestamps — add `finalizado_at`, reuse `updated_at`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Add `finalizado_at TIMESTAMPTZ NULL` column to both `estudios_socioeconomicos` and `solicitudes_tecnicas` | New columns, requires migration | Use this — clearly distinguishes finalization time from last-edit time |
| Use existing `updated_at` only | Ambiguous — updated_at also updates on any field edit | Rejected |

**Migration**: `ALTER TABLE estudios_socioeconomicos ADD COLUMN finalizado_at TIMESTAMPTZ NULL;` and same for `solicitudes_tecnicas`. Both default to NULL (backwards compatible). Set to `NOW()` on transition to `completo`.

### Decision 4: Idempotency — already-completed records return 200, no re-write

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Return 409 Conflict if either record is already `completo` | Forces client to handle conflict state | Rejected — capturista re-clicking Finalizar should be a no-op, not an error |
| Return 200 with existing data, no update | Idempotent, safe for retries | Use this |

**Implementation**: Check `estudio_row['status']` and `solicitud_row['status']` at the start. If both are `completo`, return `{estudio_id, solicitud_id, status: 'completo', finalizado_at: existing_value}` immediately, without running any transaction.

### Decision 5: Role enforcement

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `require_roles("capturista", "admin", "organizacion")` | Allows admin/organizacion to finalize too — consistent with how `crear_estudio` works | Use this — matches existing auth pattern in socioeconomico.py |
| `require_roles("capturista")` only | Restrictive | Rejected — admin needs to be able to fix records |

`assert_resource_owner` runs on both `estudio_id` and `solicitud_id` before any DB write, preventing cross-user finalization.

---

## Data Flow

```
Frontend (gestion.html)
  "Finalizar Registro" button
        │
        ▼
  fetch GET /api/estudios/{id}   ──► validate socioeconomico form completeness
  fetch GET /api/solicitudes/{id} ──► validate tecnica form completeness
  (fast pre-check, show error if missing)
        │
        ▼ (all fields present client-side)
  POST /api/finalizar-registro
  {estudio_id, solicitud_id}
        │
        ▼
  Backend (finalizar.py)
  ┌─ require_roles("capturista", "admin", "organizacion")  ← 401/403
  ├─ assert_resource_owner(estudio_row['usuario_id'])       ← 403
  ├─ assert_resource_owner(solicitud_row['usuario_id'])      ← 403
  ├─ if both already 'completo' → return 200 (idempotent)   ← early exit
  ├─ BEGIN
  ├─ _validate_all_complete(estudio_row, solicitud_row)     ← 422 on missing
  ├─ EstudioUpdateRequest(status='completo', ...)           ← triggers Pydantic validators
  ├─ db.execute(UPDATE estudios ... SET status='completo', finalizado_at=NOW())
  ├─ SolicitudUpdateRequest(status='completo', ...)         ← triggers Pydantic validators
  ├─ db.execute(UPDATE solicitudes ... SET status='completo', finalizado_at=NOW())
  ├─ COMMIT
  └─ return {estudio_id, solicitud_id, status: 'completo', finalizado_at}
        │
        ▼
  Frontend
  showSuccessToast("El registro ha sido finalizado y guardado con éxito.")
  localStorage.removeItem("estudio_id")
  localStorage.removeItem("solicitud_id")
  localStorage.removeItem("beneficiario_id")
  window.location.href = "perfil-capturista.html"
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routers/finalizar.py` | Create | New router with `POST /api/finalizar-registro` |
| `backend/main.py` | Modify | Add `from routers import ..., finalizar` + `app.include_router(finalizar.router)` |
| `backend/validators.py` | Modify | Add `validate_completeness_check()` helper function |
| `front/Capturista-view/gestion.html` | Modify | Add "Finalizar Registro" button + `finalizarRegistro()` JS function |
| `front/Capturista-view/perfil-capturista.html` | Modify | Gate edit pencil on `status !== 'completo'` for capturista |
| `backend/tests/test_finalizar.py` | Create | Unit + integration tests for finalize endpoint |
| `migrations/` | Create | Add `finalizado_at` columns to both tables |

---

## Interfaces / Contracts

### `POST /api/finalizar-registro`

**Request body**:
```json
{
  "estudio_id": 123,
  "solicitud_id": 456
}
```

**Success (200)**:
```json
{
  "estudio_id": 123,
  "solicitud_id": 456,
  "status": "completo",
  "finalizado_at": "2026-06-09T12:00:00Z"
}
```

**Already complete (200 — idempotent)**:
```json
{
  "estudio_id": 123,
  "solicitud_id": 456,
  "status": "completo",
  "finalizado_at": "2026-06-08T10:00:00Z",
  "already_completed": true
}
```

**Validation error (422)**:
```json
{
  "detail": {
    "type": "completeness_error",
    "message": "Faltan campos obligatorios",
    "missing": [
      {"form": "estudio", "field": "fecha_estudio"},
      {"form": "solicitud", "field": "peso_kg"}
    ]
  }
}
```

**Forbidden (403)**:
```json
{"detail": "No tiene permisos para este recurso"}
```

---

## Frontend State Management

### `gestion.html` — Finalizar Registro button

**Placement**: Below the existing "Guardar datos de gestión" button (line ~667), alongside "Guardar Borrador" which will be added.

**Button structure** (capturista/organizacion only):
```html
<button type="button" id="btn-finalizar" 
  class="... bg-primary hover:bg-primary-dark ...">
  Finalizar Registro
</button>
```

**`finalizarRegistro()` function**:
1. Pre-check: call `get('/api/estudios/{estudio_id}')` and `get('/api/solicitudes/{solicitud_id}')` to know which fields are already populated — don't trust localStorage alone
2. Run `SR_Validations.validateAllForms()` across socioeconomico (fetched), tecnica (fetched), gestion (DOM) forms
3. If missing: show error toast "No es posible finalizar el registro. Completa todos los campos requeridos."
4. If complete: `POST /api/finalizar-registro` with `{estudio_id, solicitud_id}`
5. On 200: `showSuccessToast(...)` + clear localStorage + redirect to `perfil-capturista.html`
6. On 422: parse `detail.missing[]` and highlight each field with `SR_Validations.showFieldError()`
7. On network error: show error toast "Ocurrió un error al finalizar el registro. Intenta nuevamente más tarde."

**Note**: The existing `submitGestion("completo")` flow (parallel PATCHes) is replaced by `finalizarRegistro()` for the Finalizar button. The "Guardar Borrador" button (status="borrador") still calls `submitGestion("borrador")` which uses the parallel PATCH approach (acceptable for drafts since atomicity is not required).

### `perfil-capturista.html` — Edit pencil gate

Current code (line 370):
```javascript
<a href="${_esc(c.edit_url)}" ...>edit</a>
```

Change to:
```javascript
${c.status !== 'completo' 
  ? `<a href="${_esc(c.edit_url)}" ...>edit</a>` 
  : `<span class="w-8 h-8 flex items-center justify-center text-slate-300 cursor-not-allowed" title="Registro completado — no editable">edit</span>`
}
```

Status badge (line 373) already shows amber "Borrador" / green "Completo" — no change needed.

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (backend) | `validate_completeness()` returns correct missing list | Mock DB rows with specific fields missing; assert error message |
| Unit (backend) | `assert_resource_owner` blocks non-owner | Test with `row_user_id !== user.usuario_id` and non-admin rol |
| Integration (backend) | Full success path | Create estudio + solicitud as borrador, call endpoint, assert both status='completo' and `finalizado_at` is set |
| Integration (backend) | Atomicity rollback | Use `pytest.mark.xfail` or a test that deliberately fails one UPDATE; verify both records unchanged |
| Integration (backend) | Already-completed idempotency | Finalize once, finalize again, assert second call returns 200 with `already_completed=true` |
| Integration (backend) | Role gate — tecnico denied | Call as tecnico user, assert 403 |
| Integration (backend) | Non-owner capturista denied | Create estudio owned by user A, call endpoint as user B, assert 403 |
| E2E (frontend) | Happy path finalization | Playwright: complete all 3 forms, click Finalizar, assert toast + redirect |
| E2E (frontend) | Validation error shows field highlights | Leave required field empty, click Finalizar, assert red error |
| E2E (frontend) | Edit pencil hidden for completo record | Assert `a[title=Editar]` does not exist in DOM for status=completo |

---

## Migration / Rollout

**No destructive changes.** Add nullable `finalizado_at` columns with default NULL. Existing records remain valid.

```sql
ALTER TABLE estudios_socioeconomicos ADD COLUMN finalizado_at TIMESTAMPTZ NULL;
ALTER TABLE solicitudes_tecnicas ADD COLUMN finalizado_at TIMESTAMPTZ NULL;
```

No feature flags needed — the endpoint only responds to explicit POST calls from the new frontend button.

---

## Open Questions

- [ ] Should `finalizado_at` be set only on the estudio, or also on the solicitud? The proposal implies both are finalized together. Use same timestamp from Python's `datetime.now(timezone.utc)` for both.
- [ ] Does `gestion.html` currently have a "Guardar Borrador" button? The PRD says it should be added. Confirm the exact placement — the existing `submitGestion("completo")` is triggered by the form submit, so "Guardar Borrador" may be a separate button calling `submitGestion("borrador")` directly.
- [ ] Should the frontend also validate socioeconomico and tecnica forms via `GET /api/estudios/{id}` and `GET /api/solicitudes/{id}` before calling `finalizar-registro`? Yes, pre-check (Step 1 in `finalizarRegistro()`) is the approach — this avoids a server-side rollback for easily-detected client-side missing fields. But confirm this doesn't cause unnecessary API calls on every click.