# Delta for perfil-capturista

## MODIFIED Requirements

### Requirement: Edit Pencil Visibility by Status

The system SHALL display the edit pencil icon (lápiz) for beneficiary records based on status. For records with `status='borrador'`, the pencil SHALL be visible and functional. For records with `status='completo'`, the pencil SHALL be hidden or disabled for capturista and organizacion roles. Admin users MAY continue to see the pencil for all statuses via `admin-beneficiarios.html`.

(Previously: Edit pencil was always visible for all records regardless of status.)

#### Scenario: Borrador record — pencil visible and functional

- GIVEN a beneficiary record with `status='borrador'` in the capturista's list
- AND the current user has role `capturista`
- WHEN the beneficiary list is rendered
- THEN the edit pencil icon SHALL be visible
- AND clicking it SHALL open the capture flow with pre-loaded draft data

#### Scenario: Completo record — pencil hidden for capturista

- GIVEN a beneficiary record with `status='completo'` in the capturista's list
- AND the current user has role `capturista`
- WHEN the beneficiary list is rendered
- THEN the edit pencil icon SHALL NOT be visible or SHALL be disabled
- AND the capturista SHALL NOT be able to open the record for editing

#### Scenario: Status display — amber for borrador, green for completo

- GIVEN a beneficiary record with `status='borrador'`
- WHEN the beneficiary list is rendered
- THEN the status badge SHALL display "En borrador" with amber styling

- GIVEN a beneficiary record with `status='completo'`
- WHEN the beneficiary list is rendered
- THEN the status badge SHALL display "Completo" with green styling
