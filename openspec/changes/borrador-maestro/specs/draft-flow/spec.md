# draft-flow Delta Spec

## Purpose
Profile page integration: display borrador status with amber badge and enable edit pencil for draft resumption.

## ADDED Requirements

### Requirement: Borrador Status Badge in Profile
The profile page (perfil-capturista.html) SHALL display records with `status="borrador"` using an amber-colored badge labeled "En borrador". The edit pencil button (✏️) SHALL be active (enabled, clickable) for borrador records, triggering the draft-resume flow. Records with `status="completo"` SHALL continue displaying their existing green badge.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| Borrador record display | Capturista has estudio 42 with status=borrador | Views perfil-capturista.html | Row shows amber "En borrador" badge |
| Borrador pencil active | Estudio 42 status=borrador shown in table | Clicks pencil icon | Triggers draft-resume: stores estudio_id, navigates to socioeconomico |
| Completo record unchanged | Estudio 43 with status=completo | Views perfil-capturista | Green badge shown, no behavioral change |

## MODIFIED Requirements

None — this capability adds new display behavior without changing existing completo-record handling.
