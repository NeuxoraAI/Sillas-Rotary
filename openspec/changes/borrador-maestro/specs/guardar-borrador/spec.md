# guardar-borrador Spec

## Purpose
Atomic draft save endpoint + frontend button that persists all 3 forms (socioeconomico, tecnica, gestion) with format-only validation.

## Requirements

### Requirement: POST /api/guardar-borrador — Atomic Draft Save
The system MUST accept all fields from the 3 forms as optional in `BorradorMaestroRequest`. Non-empty fields SHALL be validated against VALIDATION_RULES.md (regex, length, range, catalog). Empty fields SHALL be accepted without validation. Invalid format on ANY non-empty field MUST reject with HTTP 422 and per-field error messages. On success, the endpoint MUST create or update beneficiario + estudio_ socioeconomico + solicitud_tecnica in one DB transaction and return 201 with `{estudio_id, solicitud_id, beneficiario_id, folio, status}`.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| New draft — all empty | No prior IDs, no form data filled | POST with all fields null/empty | 201, status="borrador", folio generated |
| New draft — partial data | Capturista filled only beneficiario fields | POST with valid partial data | 201, only non-empty fields inserted |
| Update existing draft | estudio_id=42 exists with status="borrador" | POST with estudio_id + updated fields | PATCHes beneficiario+estudio+solicitud atomically |
| Invalid format on one field | telefonos="ABC" (not 10 digits) | POST | 422 with detail including field name and error |
| Mixed valid + invalid | nombre="A" (too short), telefono="ABC" | POST | 422, errors for BOTH invalid fields |
| DB error mid-transaction | DB fails on solicitud INSERT after beneficiario+estudio succeed | POST | Rollback, 500, no partial records |

### Requirement: Format-Only Validation Mode
In draft mode (status="borrador"), the system MUST NOT enforce completeness — all fields are optional. Format validation MUST run only when a value is non-empty. The `BorradorMaestroRequest` Pydantic model SHALL use `Optional` types with `validate_on_not_none` semantics, delegating to the existing validators in `backend/validators.py`.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| Empty string skip | campo="" (empty) | Submitted in draft | Accepted, no validation error |
| None skip | campo=null | Submitted in draft | Accepted, no validation error |
| Non-empty validate | campo="valid value" | Submitted in draft | Runs format check |
| Regex fail | nombres="123" | Submitted in draft | 422, "nombres contiene caracteres no permitidos" |
| Catalog fail | sexo="X" | Submitted in draft | 422, "sexo fuera de catalogo" |
| Range fail | edad=150 | Submitted in draft | 422, "edad debe estar entre 0 y 99" |
| Length fail | ciudad with 100 chars | Submitted in draft | 422, "ciudad debe tener maximo 80 caracteres" |

### Requirement: Frontend "Guardar Borrador" Button
All 3 form pages (socioeconomico.html, tecnica.html, gestion.html) SHALL display a "Guardar Borrador" button visible only to capturista role. On click, it MUST: (1) collect all form data from current page DOM, (2) merge with localStorage data from other pages, (3) POST to `/api/guardar-borrador` with `Authorization: Bearer {token}`, (4) show a success toast with estudio_id or an error toast with field-level messages, (5) on success, save estudio_id and solicitud_id to localStorage.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| Save from socioeconomico | Capturista on socioecon tab with partial beneficiary data | Clicks Guardar Borrador | POST includes beneficiario+estudio fields; 201 toast shown |
| Save from tecnica | Capturista on tecnica tab; socioecon data in localStorage | Clicks Guardar Borrador | POST includes solicitud fields + merged localStorage socioecon data |
| Save from gestion | Capturista on gestion tab; other form data in localStorage | Clicks Guardar Borrador | POST merges all localStorage data + gestion fields |
| All 3 forms empty | No form ever filled | Clicks Guardar Borrador | 201, all nulls accepted, estudio_id saved |
| Network error | API unreachable | Clicks Guardar Borrador | Error toast "Error de conexion" |
| 422 response | Backend returns field errors | Clicks Guardar Borrador | Error toast with first field error message |
| Button hidden for tecnico | Tecnico role on socioeconomico.html | Page loads | Guardar Borrador button NOT visible |
