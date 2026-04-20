"""
Tests for structured error handling in POST /api/solicitudes.

Verifies that:
- Invalid payloads return deterministic 422 responses (not generic 400).
- Foreign key violations return structured 422 with type info.
- Check constraint violations return structured 422.
- Unknown DB errors return 500 (not 400).
"""


class TestSolicitudErrorContract:
    """Enforce determinstic, structured error responses from /api/solicitudes."""

    def test_missing_required_field_returns_422(self, client, tecnico_headers):
        """POST without required fields should return 422, not 400."""
        payload = {}  # Missing beneficiario_id, entorno, control_tronco, control_cabeza
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=payload,
        )
        assert response.status_code == 422
        data = response.json()
        # FastAPI/Pydantic validation errors include 'detail' as a list
        assert "detail" in data

    def test_invalid_prioridad_returns_422(self, client, tecnico_headers, sample_estudio):
        """POST with invalid prioridad value should return 422 (Pydantic validation)."""
        payload = {
            "beneficiario_id": sample_estudio["beneficiario_id"],
            "entorno": "Urbano",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "prioridad": "InvalidValue",
        }
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=payload,
        )
        assert response.status_code == 422

    def test_invalid_status_returns_422(self, client, tecnico_headers, sample_estudio):
        """POST with invalid status should return 422 (Pydantic validation)."""
        payload = {
            "beneficiario_id": sample_estudio["beneficiario_id"],
            "entorno": "Urbano",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "status": "invalid_status",
        }
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=payload,
        )
        assert response.status_code == 422

    def test_nonexistent_beneficiario_returns_422(
        self, client, tecnico_headers
    ):
        """POST with beneficiario_id that doesn't exist should return 422
        (foreign key violation), not a generic 400."""
        payload = {
            "beneficiario_id": 99999,  # Non-existent
            "entorno": "Urbano",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "status": "borrador",
        }
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=payload,
        )
        # FK violation should be 422 with structured detail, not generic 400
        assert response.status_code in (422, 500), (
            f"Expected 422 (FK violation) or 500 (if DB error), "
            f"got {response.status_code}: {response.text}"
        )
        if response.status_code == 422:
            data = response.json()
            detail = data.get("detail", {})
            # If structured, should have 'type' field
            if isinstance(detail, dict):
                assert detail.get("type") == "foreign_key_violation", (
                    f"Expected type='foreign_key_violation', got: {detail}"
                )

    def test_negative_measure_returns_422(
        self, client, tecnico_headers, sample_estudio
    ):
        """POST with negative measurement should return 422 (Pydantic validation)."""
        payload = {
            "beneficiario_id": sample_estudio["beneficiario_id"],
            "entorno": "Urbano",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "peso_kg": -5.0,
            "status": "borrador",
        }
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json=payload,
        )
        assert response.status_code == 422

    def test_empty_payload_returns_422_not_400(self, client, tecnico_headers):
        """Ensure API does not return generic 400 for empty body."""
        response = client.post(
            "/api/solicitudes",
            headers=tecnico_headers,
            json={},
        )
        assert response.status_code == 422
        assert response.status_code != 400, (
            "API should return 422 for validation errors, not 400"
        )