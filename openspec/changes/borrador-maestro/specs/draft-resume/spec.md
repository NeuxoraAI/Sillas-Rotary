# draft-resume Spec

## Purpose
Endpoint and frontend flow to load a complete draft (all 3 forms) for re-editing from the capturista profile.

## Requirements

### Requirement: GET /api/borrador/{estudio_id}
The system SHALL return beneficiario + estudio_socioeconomico + solicitud_tecnica + tutores as a single JSON payload for the given estudio_id. Only the owner capturista MAY access this endpoint (HTTP 403 for non-owners). The system MUST return HTTP 404 if the estudio is not found or its status is not "borrador". The response SHALL include all fields needed to pre-fill the 3 forms.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| Owner access | Capturista A owns estudio 42, status=borrador | GET /api/borrador/42 | 200 with beneficiario + estudio + solicitud + tutores |
| Non-owner access | Capturista B requests estudio 42 owned by A | GET /api/borrador/42 | 403 |
| Not found | estudio_id=999 does not exist | GET /api/borrador/999 | 404 |
| Completed study | estudio 42 has status=completo | GET /api/borrador/42 | 404 |
| Partial draft | Draft has only beneficiario data, no solicitud | GET /api/borrador/42 | 200, solicitud fields null |
| Unauthenticated | No JWT token | GET /api/borrador/42 | 401 |

### Requirement: Frontend Draft Resumption Flow
When a capturista clicks the pencil button on an "En borrador" record in perfil-capturista.html, the system SHALL: (1) store estudio_id in localStorage, (2) navigate to socioeconomico.html. On page load, socioeconomico.html MUST: (3) detect estudio_id from URL params or localStorage, (4) fetch `GET /api/borrador/{id}`, (5) populate ALL forms' data into localStorage (beneficiario, estudio, solicitud, tutores), (6) fill current page DOM fields from the stored data. When the user navigates to tecnica.html or gestion.html, those pages SHALL read their respective data from localStorage.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| Resume from profile | Capturista has borrador estudio 42 | Clicks pencil on perfil-capturista | Redirects to socioeconomico.html?estudio_id=42, all beneficiary fields pre-filled |
| Cross-tab navigation | Resume completed on socioeconomico, then navigate to tecnica | Clicks "Siguiente" or tab link | tecnica.html reads localStorage, pre-fills medidas + postura fields |
| Gestion tab after resume | Draft has entidad_solicitante="CLUB ROTARIO" | Navigate to gestion.html | entidad_solicitante field pre-filled with "CLUB ROTARIO" |
| Resume with no solicitud data | Draft has estudio but no solicitud_tecnica created yet | Navigate to tecnica.html | Form loads empty (no crash), ready for fresh input |
| 404 on resume | estudio_id in localStorage was deleted | socioeconomico.html loads | Shows error toast, redirects to perfil-capturista |
| 403 on resume | Another user's estudio_id somehow in localStorage | socioeconomico.html loads | Shows error toast "No tienes acceso a este borrador", redirects to perfil-capturista |
