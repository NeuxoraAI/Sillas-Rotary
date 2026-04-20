"""
Tests for structured error handling in POST /api/estudios.

Verifies that:
- Invalid payloads return deterministic 422 responses (not generic 400).
- Missing required fields return structured 422 with detail.
- Invalid enums (status) return 422.
- Empty payload returns 422, not 400.
"""


class TestEstudioErrorContract:
    """Enforce deterministic, structured error responses from /api/estudios."""

    def test_empty_payload_returns_422(self, client, capturista_headers):
        """POST with empty body should return 422, not 400."""
        response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json={},
        )
        assert response.status_code == 422
        assert response.status_code != 400, (
            "API should return 422 for validation errors, not 400"
        )

    def test_missing_beneficiario_returns_422(self, client, capturista_headers, region_lon):
        """POST without beneficiario should return 422."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "estudio": {
                "tuvo_silla_previa": False,
                "elaboro_estudio": "Capturista Test",
                "fecha_estudio": "2026-04-19",
                "status": "borrador",
            },
        }
        response = client.post(
            "/api/estudios",
            json=payload,
            headers=capturista_headers,
        )
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_invalid_status_returns_422(self, client, capturista_headers, region_lon):
        """POST with invalid status should return 422 (Pydantic validation)."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "beneficiario": {
                "nombre": "Bene Test",
                "fecha_nacimiento": "2000-01-15",
                "diagnostico": "Diagnóstico",
                "calle": "Calle Test",
                "colonia": "Centro",
                "ciudad": "León",
                "telefonos": "4621234567",
            },
            "tutores": [],
            "estudio": {
                "tuvo_silla_previa": False,
                "elaboro_estudio": "Capturista Test",
                "fecha_estudio": "2026-04-19",
                "status": "invalid_status_xyz",
            },
        }
        response = client.post(
            "/api/estudios",
            json=payload,
            headers=capturista_headers,
        )
        assert response.status_code == 422

    def test_missing_required_beneficiario_fields_returns_422(
        self, client, capturista_headers, region_lon
    ):
        """POST with incomplete beneficiario should return 422."""
        payload = {
            "region_id": region_lon["id"],
            "sede": "León sede Forum",
            "beneficiario": {
                "nombre": "Bene Test",
                # Missing fecha_nacimiento, diagnostico, etc.
            },
            "tutores": [],
            "estudio": {
                "tuvo_silla_previa": False,
                "elaboro_estudio": "Capturista Test",
                "fecha_estudio": "2026-04-19",
                "status": "borrador",
            },
        }
        response = client.post(
            "/api/estudios",
            json=payload,
            headers=capturista_headers,
        )
        assert response.status_code == 422

    def test_no_generic_400_on_validation_error(self, client, capturista_headers):
        """Ensure validation errors never return generic 400."""
        response = client.post(
            "/api/estudios",
            headers=capturista_headers,
            json={"garbage": True},
        )
        assert response.status_code != 400, (
            "Validation errors must return 422, not 400"
        )
        assert response.status_code in (422, 403), (
            f"Expected 422 (validation) or 403 (role), got {response.status_code}"
        )
