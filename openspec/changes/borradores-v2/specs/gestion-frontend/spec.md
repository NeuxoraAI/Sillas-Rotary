# Delta for gestion-frontend

## ADDED Requirements

### Requirement: Finalizar Registro Button

The sistema SHALL display a "Finalizar Registro" button in `gestion.html` alongside the existing "Guardar datos de gestión" button. This button MUST be visible only for roles `capturista` and `organizacion`.

#### Scenario: Capturista clicks Finalizar with all forms complete — success

- GIVEN the capturista is on the gestion page with valid estudio_id and solicitud_id
- AND all required fields across socioeconomico, tecnica, and gestion pass frontend validation
- WHEN the capturista clicks "Finalizar Registro"
- THEN the system SHALL POST to `/api/finalizar-registro` with `{estudio_id, solicitud_id}`
- AND on HTTP 200, display a green success toast: "El registro ha sido finalizado y guardado con éxito."
- AND clear `estudio_id`, `solicitud_id`, `beneficiario_id` from localStorage
- AND redirect to `perfil-capturista.html`

#### Scenario: Capturista clicks Finalizar with incomplete fields — error

- GIVEN the capturista clicks "Finalizar Registro"
- AND frontend validation detects missing required fields or invalid formats
- WHEN validation fails
- THEN the system SHALL display a red error toast: "No es posible finalizar el registro. Completa todos los campos requeridos."
- AND highlight each field with a validation error
- AND SHALL NOT call the backend endpoint

#### Scenario: Backend returns validation error

- GIVEN frontend validation passes but backend returns HTTP 422
- WHEN "Finalizar Registro" is clicked
- THEN the system SHALL display a red error toast with backend field-level error details
- AND SHALL NOT clear localStorage
- AND SHALL NOT redirect

#### Scenario: Server connection error

- GIVEN the backend is unreachable
- WHEN "Finalizar Registro" is clicked
- THEN the system SHALL display a red error toast: "Ocurrió un error al finalizar el registro. Intenta nuevamente más tarde."

#### Scenario: Non-capturista user — button hidden

- GIVEN a user with role `tecnico` or `admin`
- WHEN the gestion page is viewed
- THEN the "Finalizar Registro" button SHALL NOT be visible

### Requirement: Multi-Form Validation Before Finalization

Before calling the backend, the system SHALL validate completeness of ALL three forms (socioeconomico, tecnica, gestion) client-side, not just the currently visible gestion form.

#### Scenario: Cross-form validation catches missing fields

- GIVEN the gestion form fields are complete
- BUT a required field in the socioeconomico form (e.g., `nombres`) is empty
- WHEN "Finalizar Registro" is clicked
- THEN the system SHALL reject with an error indicating which form and field requires completion
