# finalizar-registro Specification

## Purpose

Atomic endpoint that validates completeness of all three registration forms (socioeconomico, tecnica, gestion) and transitions both estudio and solicitud from `borrador` to `completo` in a single database transaction.

## Requirements

### Requirement: Atomic Finalization

The system SHALL provide a `POST /api/finalizar-registro` endpoint that validates all required fields across beneficiario, tutores, estudio, and solicitud, and atomically marks both records as `status='completo'` in a single database transaction.

#### Scenario: All forms complete — success

- GIVEN a valid JWT for a capturista user
- AND valid `estudio_id` and `solicitud_id` in request body
- AND all required fields per VALIDATION_RULES.md are present and valid
- WHEN `POST /api/finalizar-registro` is called
- THEN both estudio and solicitud SHALL be updated to `status='completo'`
- AND response SHALL return `{estudio_id, solicitud_id, status: 'completo', finalizado_at}` with HTTP 200

#### Scenario: Missing required fields — rejection

- GIVEN a valid JWT for a capturista user
- AND one or more required fields from VALIDATION_RULES.md are empty or invalid
- WHEN `POST /api/finalizar-registro` is called
- THEN response SHALL return HTTP 422
- AND response body SHALL include field-level error details identifying each missing/invalid field
- AND neither estudio nor solicitud SHALL change status

#### Scenario: Non-owner capturista — forbidden

- GIVEN a valid JWT for a capturista who did NOT create the estudio
- AND `estudio_id` belongs to a different capturista
- WHEN `POST /api/finalizar-registro` is called
- THEN response SHALL return HTTP 403
- AND neither record SHALL change status

#### Scenario: Tecnico or admin user — forbidden

- GIVEN a valid JWT for a role other than capturista, admin, or organizacion
- WHEN `POST /api/finalizar-registro` is called
- THEN response SHALL return HTTP 403

#### Scenario: Atomicity — rollback on partial failure

- GIVEN a valid request where one record updates but the other fails
- WHEN the database transaction encounters an error mid-process
- THEN BOTH records SHALL retain their original `status`
- AND no partial completion SHALL be persisted
- AND response SHALL return HTTP 422 or 500

#### Scenario: Already completed records — idempotent

- GIVEN `estudio_id` and `solicitud_id` are already `status='completo'`
- WHEN `POST /api/finalizar-registro` is called
- THEN response SHALL return HTTP 200 with existing completion data
- AND records SHALL NOT be modified

### Requirement: Input Validation Contract

The endpoint SHALL accept `{estudio_id, solicitud_id}` and SHALL validate against VALIDATION_RULES.md as the single source of truth for all field formats, lengths, and required-by-status rules.

#### Scenario: Invalid estudio_id format

- GIVEN a `estudio_id` that is not a valid integer
- WHEN `POST /api/finalizar-registro` is called
- THEN response SHALL return HTTP 422 with a message indicating invalid input format

### Requirement: Role Enforcement

Authorization SHALL be enforced via JWT. Roles permitted: `capturista`, `admin`, `organizacion`. All other roles SHALL receive HTTP 403.

#### Scenario: No JWT provided

- GIVEN no Authorization header
- WHEN `POST /api/finalizar-registro` is called
- THEN response SHALL return HTTP 401
