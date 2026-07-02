# Design: borrador-maestro (Master Draft Save)

## Technical Approach

A single atomic `POST /api/guardar-borrador` endpoint that persists all three forms (socioeconomico, tecnica, gestion) in one DB transaction with format-only validation. Drafts use `status='borrador'` (already supported in schema). A companion `GET /api/borrador/{estudio_id}` loads a complete draft for resumption. Frontend adds "Guardar Borrador" button to all three form pages.

## Architecture Decisions

### Decision: Pydantic model with all Optional fields

**Choice**: `GuardarBorradorRequest` with every field as `Optional` with default `None`
**Alternatives considered**: Separate models per form, or `Union` types for create/update
**Rationale**: Single model covers both CREATE and UPDATE modes. Existing `validate_*` functions in `validators.py` already handle `None` gracefully for most fields — we wrap them with nil-checks.

### Decision: Format-only validation (skip None/"") in draft mode

**Choice**: Each field validator wrapped: `if v is None or v == "": return v` before calling existing validator
**Alternatives considered**: Create parallel set of lenient validators, or disable validators entirely
**Rationale**: Reuses existing `validators.py` code exactly as-is — only adds a guard clause. No validator duplication.

### Decision: Atomic transaction (BEGIN → INSERT/UPDATE all → COMMIT)

**Choice**: Explicit `db.execute("BEGIN")` / `db.execute("COMMIT")` with try/except rollback
**Alternatives considered**: Supabase client-side upsert, or separate endpoint calls with补偿
**Rationale**: Matches the pattern used in `finalizar.py` (lines 267-287). Guarantees no partial records if any insert fails.

### Decision: Frontend merges localStorage drafts before POST

**Choice**: On "Guardar Borrador" click, collect current form DOM data + merge `localStorage.getItem('draft_*')` for other forms
**Alternatives considered**: Each page saves its own draft independently, or backend fetches other forms
**Rationale**: Already the established pattern — `gestion.html` lines 668-674 show this merge pattern. No backend change needed.

### Decision: Draft resumption via GET + localStorage populate

**Choice**: `GET /api/borrador/{id}` returns full payload; frontend stores in `localStorage` and pre-fills forms
**Alternatives considered**: Return full payload and pre-fill current page only, or use a session cookie
**Rationale**: Matches existing `localStorage` draft pattern. Enables cross-page navigation without re-fetching.

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend (any form page)                                            │
│  "Guardar Borrador" click                                            │
│    ├─ Collect DOM data for current form                              │
│    ├─ Merge localStorage drafts for other 2 forms                    │
│    └─ POST /api/guardar-borrador { ...all fields... }                │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  backend/routers/guardar_borrador.py                                  │
│  POST /api/guardar-borrador                                          │
│    ├─ Validate token (require_auth)                                   │
│    ├─ Parse GuardarBorradorRequest (all Optional fields)              │
│    ├─ Format validation (skip None/"") via wrapped validators          │
│    ├─ If estudio_id: UPDATE beneficiario + estudio + solicitud         │
│    └─ If no estudio_id: CREATE all 3 records atomically               │
│         BEGIN → INSERT beneficiario → INSERT estudio → INSERT solicitud │
│         COMMIT                                                         │
│    └─ Return {estudio_id, solicitud_id, beneficiario_id, folio, status}│
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend (perfil-capturista)                                        │
│  Pencil click on borrador record                                     │
│    ├─ localStorage.setItem('estudio_id', id)                          │
│    └─ window.location = 'socioeconomico.html?estudio_id=' + id       │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend (socioeconomico.html load with estudio_id)                 │
│    ├─ GET /api/borrador/{id}                                          │
│    ├─ Store all data in localStorage (beneficiario, estudio, solicitud, tutores)│
│    └─ Pre-fill current page DOM                                       │
│                                                                      │
│  Navigate to tecnica.html / gestion.html                             │
│    └─ Read from localStorage (no re-fetch needed)                    │
└──────────────────────────────────────────────────────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/routers/guardar_borrador.py` | Create | New router with POST /api/guardar-borrador and GET /api/borrador/{id} |
| `backend/main.py` | Modify | Add `app.include_router(guardar_borrador.router, prefix="/api")` |
| `backend/validators.py` | Modify | Add `def validate_optional(wrapped_validator, value)` helper — wraps any validator to skip None/"" |
| `front/Capturista-view/socioeconomico.html` | Modify | Add "Guardar Borrador" button next to CONTINUAR; implement draft save/resume logic |
| `front/Capturista-view/tecnica.html` | Modify | Add "Guardar Borrador" button; load draft from localStorage on page load |
| `front/Capturista-view/gestion.html` | Modify | Add "Guardar Borrador" button; existing localStorage merge already present, extend it |
| `front/Capturista-view/perfil-capturista.html` | Modify | Amber badge for `status='borrador'`; pencil activates draft-resume flow |

## Interfaces / Contracts

### POST /api/guardar-borrador

**Request body** (`GuardarBorradorRequest`):
```python
class GuardarBorradorRequest(BaseModel):
    # IDs for UPDATE mode (optional — omitted means CREATE)
    estudio_id: Optional[int] = None
    solicitud_id: Optional[int] = None
    beneficiario_id: Optional[int] = None

    # region_ctx (required even in draft — for folio generation)
    region_id: int
    sede: str
    ciudad_registro: str

    # Beneficiario fields (all Optional)
    nombres: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    diagnostico: Optional[str] = None
    calle: Optional[str] = None
    num_ext: Optional[str] = None
    num_int: Optional[str] = None
    colonia: Optional[str] = None
    ciudad: Optional[str] = None
    estado_codigo: Optional[str] = None
    estado_nombre: Optional[str] = None
    sexo: Optional[str] = None
    telefonos: Optional[str] = None
    email: Optional[str] = None

    # Estudio fields (all Optional)
    fecha_estudio: Optional[str] = None
    tuvo_silla_previa: Optional[bool] = None
    como_obtuvo_silla: Optional[str] = None
    elaboro_estudio: Optional[str] = None

    # Tutor 1 fields (all Optional)
    tutor1_nombres: Optional[str] = None
    tutor1_apellido_paterno: Optional[str] = None
    tutor1_apellido_materno: Optional[str] = None
    tutor1_email: Optional[str] = None
    tutor1_edad: Optional[int] = None
    tutor1_nivel_estudios: Optional[str] = None
    tutor1_estado_civil: Optional[str] = None
    tutor1_num_hijos: Optional[int] = None
    tutor1_vivienda: Optional[str] = None
    tutor1_fuente_empleo: Optional[str] = None
    tutor1_ingreso_mensual: Optional[int] = None
    tutor1_antiguedad_anios: Optional[int] = None
    tutor1_antiguedad_meses_extra: Optional[int] = None
    tutor1_imss_estatus: Optional[str] = None
    tutor1_infonavit_estatus: Optional[str] = None
    tutor1_sin_empleo: Optional[bool] = None

    # Tecnica/Gestion fields (all Optional)
    entorno: Optional[str] = None
    control_tronco: Optional[str] = None
    control_cabeza: Optional[str] = None
    control_de_piernas: Optional[str] = None
    observaciones_posturales: Optional[str] = None
    unidad_medida: Optional[str] = "in"
    altura_total_in: Optional[Decimal] = None
    peso_kg: Optional[Decimal] = None
    unidad_peso_captura: Optional[str] = "kg"
    medida_cabeza_asiento: Optional[Decimal] = None
    medida_hombro_asiento: Optional[Decimal] = None
    medida_prof_asiento: Optional[Decimal] = None
    medida_rodilla_talon: Optional[Decimal] = None
    medida_ancho_cadera: Optional[Decimal] = None
    foto_url: Optional[str] = None
    entidad_solicitante: Optional[str] = None
    prioridad: Optional[str] = None
    justificacion: Optional[str] = None
```

**Response** (201):
```json
{
  "estudio_id": 42,
  "solicitud_id": 17,
  "beneficiario_id": 99,
  "folio": "MX-GTO-2026-001",
  "status": "borrador"
}
```

**Error** (422):
```json
{
  "detail": [
    {"loc": ["body", "telefonos"], "msg": "El teléfono debe contener exactamente 10 dígitos numéricos"}
  ]
}
```

### GET /api/borrador/{estudio_id}

**Response** (200):
```json
{
  "estudio_id": 42,
  "solicitud_id": 17,
  "beneficiario_id": 99,
  "folio": "MX-GTO-2026-001",
  "status": "borrador",
  "beneficiario": { ...all fields... },
  "estudio": { ...all fields... },
  "solicitud": { ...all fields... },
  "tutores": [ {tutor1...}, {tutor2...} ]
}
```

**Errors**: 403 (not owner), 404 (not found or not borrador)

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `GuardarBorradorRequest` parsing with mixed Optional fields | Python pytest — test each field as None, "", valid value |
| Unit | `validate_optional` wrapper skips None/"" correctly | Mock validator that raises, assert no call for None |
| Unit | Ownership check rejects non-owner | Patch `assert_resource_owner` to raise, assert HTTP 403 |
| Integration | CREATE mode: all null → 201, folio generated | `client.post("/api/guardar-borrador", json={...all null...})` |
| Integration | CREATE mode: partial data → 201 | Only beneficiario fields populated |
| Integration | UPDATE mode: existing estudio → PATCHes all 3 records | Seed borrador, POST with estudio_id |
| Integration | DB error mid-transaction → 500, rollback | Mock db.execute to fail on 2nd insert |
| Integration | GET borrador: owner gets 200 with full payload | Auth as owner |
| Integration | GET borrador: non-owner gets 403 | Auth as different capturista |
| E2E | Guardar Borrador button visible on socioeconomico.html | Selenium check |
| E2E | Save from socioeconomico → resume from tecnica → data matches | Selenium full flow |

## Migration / Rollout

No migration required. Existing `status='borrador'` column already exists. The change is purely additive:
- New endpoint (`guardar_borrador`) 
- New frontend button
- Amber badge display in profile

Rollout is low-risk — drafts created via the new endpoint are indistinguishable from drafts created via existing individual endpoints.

## Open Questions

- [ ] Should the `region_id` / `sede` / `ciudad_registro` be editable in UPDATE mode, or locked after first save? (Currently treating them as editable)
- [ ] Does the capturista need to see a list of their borrador studies on the profile page alongside completo studies, or only the pencil icon to resume?