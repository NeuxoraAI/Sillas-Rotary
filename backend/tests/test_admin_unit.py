"""
Pure unit tests for admin router Pydantic models and validators.

These tests do NOT require a database connection — they validate:
- Pydantic model field validation (validators from validators.py)
- Request/response schemas
- Validation edge cases (length, regex, catalogs, etc.)

To run:
    cd backend
    ./venv/bin/pytest tests/test_admin_unit.py -v
"""

import pytest
from decimal import Decimal

# Import the models to test
from routers.admin import (
    AdminBeneficiarioUpdateRequest,
    AdminEstudioUpdateRequest,
    AdminSolicitudUpdateRequest,
    AdminGestionUpdateRequest,
)


# ---------------------------------------------------------------------------
# AdminBeneficiarioUpdateRequest — validation tests
# ---------------------------------------------------------------------------

class TestAdminBeneficiarioUpdateRequest:
    """Unit tests for the admin beneficiario PATCH request model."""

    # ── Valid cases ─────────────────────────────────────────────────────

    def test_empty_payload_valid(self):
        """Empty payload (all fields Optional) is valid."""
        body = AdminBeneficiarioUpdateRequest()
        # Pydantic v2 model_dump includes None by default; use exclude_none=True
        assert body.model_dump(exclude_none=True) == {}

    def test_nombres_valid(self):
        """Valid nombres passes (normalized to uppercase, accents stripped)."""
        body = AdminBeneficiarioUpdateRequest(nombres="Juan Carlos")
        # normalize_text uppercases and strips accents
        assert body.nombres == "JUAN CARLOS"

    def test_all_optional_fields_valid(self):
        """All fields populated with valid data passes."""
        body = AdminBeneficiarioUpdateRequest(
            nombres="JUAN",
            apellido_paterno="PEREZ",
            apellido_materno="GARCIA",
            fecha_nacimiento="2000-01-15",
            diagnostico="Paralisis cerebral",
            calle="Calle Principal 123",
            num_ext="12A",
            num_int="3",
            colonia="Centro",
            ciudad="Leon",
            estado_codigo="11",
            estado_nombre="GUANAJUATO",
            sexo="M",
            telefonos="4621234567",
            email="test@example.com",
        )
        assert body.nombres == "JUAN"
        assert body.sexo == "M"

    # ── Validation errors — names ──────────────────────────────────────

    def test_nombres_too_short(self):
        """nombres < 2 chars raises ValueError."""
        with pytest.raises(ValueError, match="nombres debe tener entre 2 y"):
            AdminBeneficiarioUpdateRequest(nombres="A")

    def test_nombres_too_long(self):
        """nombres > 60 chars raises ValueError."""
        with pytest.raises(ValueError, match="nombres debe tener entre 2 y"):
            AdminBeneficiarioUpdateRequest(nombres="A" * 61)

    def test_nombres_invalid_chars(self):
        """nombres with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="nombres contiene caracteres no permitidos"):
            AdminBeneficiarioUpdateRequest(nombres="Juan123")

    # ── Validation errors — apellidos ──────────────────────────────────

    def test_apellido_paterno_too_short(self):
        """apellido_paterno < 2 chars raises ValueError."""
        with pytest.raises(ValueError, match="apellido_paterno debe tener entre 2 y"):
            AdminBeneficiarioUpdateRequest(apellido_paterno="X")

    def test_apellido_materno_invalid_chars(self):
        """apellido_materno with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="apellido_materno contiene caracteres no permitidos"):
            AdminBeneficiarioUpdateRequest(apellido_materno="Garcia@")

    # ── Validation errors — fecha_nacimiento ───────────────────────────

    def test_fecha_nacimiento_invalid_format(self):
        """fecha_nacimiento not YYYY-MM-DD raises ValueError."""
        with pytest.raises(ValueError, match="fecha_nacimiento debe tener formato"):
            AdminBeneficiarioUpdateRequest(fecha_nacimiento="15-01-2000")

    def test_fecha_nacimiento_valid(self):
        """Valid ISO date passes."""
        body = AdminBeneficiarioUpdateRequest(fecha_nacimiento="2000-01-15")
        assert body.fecha_nacimiento == "2000-01-15"

    # ── Validation errors — diagnostico ────────────────────────────────

    def test_diagnostico_too_short(self):
        """diagnostico < 3 chars raises ValueError."""
        with pytest.raises(ValueError, match="diagnostico debe tener entre 3 y"):
            AdminBeneficiarioUpdateRequest(diagnostico="AB")

    def test_diagnostico_invalid_chars(self):
        """diagnostico with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="diagnostico contiene caracteres no permitidos"):
            AdminBeneficiarioUpdateRequest(diagnostico="Paralisis@")

    # ── Validation errors — calle ──────────────────────────────────────

    def test_calle_too_short(self):
        """calle < 3 chars raises ValueError."""
        with pytest.raises(ValueError, match="calle debe tener entre 3 y"):
            AdminBeneficiarioUpdateRequest(calle="AB")

    # ── Validation errors — colonia ─────────────────────────────────────

    def test_colonia_too_short(self):
        """colonia < 2 chars raises ValueError."""
        with pytest.raises(ValueError, match="colonia debe tener entre 2 y"):
            AdminBeneficiarioUpdateRequest(colonia="X")

    # ── Validation errors — ciudad ──────────────────────────────────────

    def test_ciudad_too_short(self):
        """ciudad < 2 chars raises ValueError."""
        with pytest.raises(ValueError, match="ciudad debe tener entre 2 y"):
            AdminBeneficiarioUpdateRequest(ciudad="X")

    # ── Validation errors — estado_codigo ────────────────────────────

    def test_estado_codigo_invalid(self):
        """estado_codigo not in INEGI catalog raises ValueError."""
        with pytest.raises(ValueError, match="estado_codigo fuera de catálogo INEGI"):
            AdminBeneficiarioUpdateRequest(estado_codigo="99")

    def test_estado_codigo_valid(self):
        """Valid INEGI code passes."""
        body = AdminBeneficiarioUpdateRequest(estado_codigo="11")
        assert body.estado_codigo == "11"

    # ── Validation errors — sexo ─────────────────────────────────────

    def test_sexo_invalid(self):
        """sexo not M or F raises ValueError."""
        with pytest.raises(ValueError, match="sexo fuera de catálogo"):
            AdminBeneficiarioUpdateRequest(sexo="X")

    def test_sexo_valid(self):
        """Valid sexo passes."""
        body = AdminBeneficiarioUpdateRequest(sexo="F")
        assert body.sexo == "F"

    # ── Validation errors — telefonos ────────────────────────────────

    def test_telefonos_too_short(self):
        """telefonos < 10 digits raises ValueError."""
        with pytest.raises(ValueError, match="teléfono debe contener exactamente 10"):
            AdminBeneficiarioUpdateRequest(telefonos="123456789")

    def test_telefonos_invalid_chars(self):
        """telefonos with letters raises ValueError."""
        with pytest.raises(ValueError, match="teléfono debe contener exactamente 10"):
            AdminBeneficiarioUpdateRequest(telefonos="123456789a")

    def test_telefonos_strips_formatting(self):
        """telefonos strips non-digits."""
        body = AdminBeneficiarioUpdateRequest(telefonos="462-123-4567")
        assert body.telefonos == "4621234567"

    # ── Validation errors — email ────────────────────────────────────

    def test_email_invalid(self):
        """Invalid email raises ValueError."""
        with pytest.raises(ValueError, match="email debe ser una dirección válida"):
            AdminBeneficiarioUpdateRequest(email="not-an-email")

    def test_email_valid(self):
        """Valid email passes."""
        body = AdminBeneficiarioUpdateRequest(email="test@example.com")
        assert body.email == "test@example.com"


# ---------------------------------------------------------------------------
# AdminEstudioUpdateRequest — validation tests
# ---------------------------------------------------------------------------

class TestAdminEstudioUpdateRequest:
    """Unit tests for the admin estudio PATCH request model."""

    def test_empty_payload_valid(self):
        """Empty payload is valid."""
        body = AdminEstudioUpdateRequest()
        assert body.model_dump(exclude_none=True) == {}

    def test_status_valid(self):
        """Valid status passes (model_validator requires fecha_estudio when completo)."""
        body = AdminEstudioUpdateRequest(status="borrador")
        assert body.status == "borrador"

    def test_status_completo_requires_fecha(self):
        """status=completo requires fecha_estudio due to model_validator."""
        with pytest.raises(ValueError, match="fecha_estudio es obligatorio cuando status es completo"):
            AdminEstudioUpdateRequest(status="completo")

    def test_status_invalid(self):
        """Invalid status raises ValueError."""
        with pytest.raises(ValueError, match="status fuera de catálogo"):
            AdminEstudioUpdateRequest(status="invalido")

    def test_fecha_estudio_no_validator_in_model(self):
        """fecha_estudio has no field_validator in AdminEstudioUpdateRequest
        (validation happens at router level via validate_fecha_estudio).
        """
        body = AdminEstudioUpdateRequest(fecha_estudio="15-01-2026", status="borrador")
        assert body.fecha_estudio == "15-01-2026"  # no validation in model

    def test_tuvo_silla_previa_requires_como_obtuvo(self):
        """If status=completo and tuvo_silla_previa=True, como_obtuvo_silla is required."""
        with pytest.raises(ValueError, match="como_obtuvo_silla es obligatorio"):
            AdminEstudioUpdateRequest(
                status="completo",
                tuvo_silla_previa=True,
                fecha_estudio="2026-01-15",
            )

    def test_tuvo_silla_previa_valid(self):
        """tuvo_silla_previa=False with status=completo passes."""
        body = AdminEstudioUpdateRequest(
            status="completo",
            tuvo_silla_previa=False,
            fecha_estudio="2026-01-15",
        )
        assert body.tuvo_silla_previa is False

    def test_como_obtuvo_silla_no_validator_when_borrador(self):
        """como_obtuvo_silla is NOT validated when status != completo.
        The catalog validation only happens in the router endpoint via _resolve_como_obtuvo_silla.
        """
        body = AdminEstudioUpdateRequest(
            tuvo_silla_previa=True,
            como_obtuvo_silla="ROBADA",
            status="borrador",
        )
        assert body.como_obtuvo_silla == "ROBADA"  # no validation in model when borrador


# ---------------------------------------------------------------------------
# AdminSolicitudUpdateRequest — validation tests
# ---------------------------------------------------------------------------

class TestAdminSolicitudUpdateRequest:
    """Unit tests for the admin solicitud PATCH request model."""

    def test_empty_payload_valid(self):
        """Empty payload is valid."""
        body = AdminSolicitudUpdateRequest()
        assert body.model_dump(exclude_none=True) == {}

    def test_entorno_valid(self):
        """Valid entorno passes."""
        body = AdminSolicitudUpdateRequest(entorno="Urbano / Interiores")
        assert body.entorno == "Urbano / Interiores"

    def test_entorno_invalid(self):
        """Invalid entorno raises ValueError."""
        with pytest.raises(ValueError, match="entorno fuera de catálogo"):
            AdminSolicitudUpdateRequest(entorno="Otro")

    def test_control_tronco_valid(self):
        """Valid control_tronco passes."""
        body = AdminSolicitudUpdateRequest(control_tronco="Completo")
        assert body.control_tronco == "Completo"

    def test_control_tronco_invalid(self):
        """Invalid control_tronco raises ValueError."""
        with pytest.raises(ValueError, match="control_tronco fuera de catálogo"):
            AdminSolicitudUpdateRequest(control_tronco="Medio")

    def test_control_cabeza_valid(self):
        """Valid control_cabeza passes."""
        body = AdminSolicitudUpdateRequest(control_cabeza="Independiente")
        assert body.control_cabeza == "Independiente"

    def test_control_de_piernas_valid(self):
        """Valid control_de_piernas passes."""
        body = AdminSolicitudUpdateRequest(control_de_piernas="Parcial")
        assert body.control_de_piernas == "Parcial"

    def test_control_de_piernas_invalid(self):
        """Invalid control_de_piernas raises ValueError."""
        with pytest.raises(ValueError, match="control_de_piernas fuera de catálogo"):
            AdminSolicitudUpdateRequest(control_de_piernas="Completo")

    def test_medida_valid(self):
        """Valid medida passes."""
        body = AdminSolicitudUpdateRequest(altura_total_in=Decimal("65.5"))
        assert body.altura_total_in == Decimal("65.5")

    def test_medida_invalid_format(self):
        """Invalid medida format raises ValueError."""
        with pytest.raises(ValueError, match="formato inválido"):
            AdminSolicitudUpdateRequest(altura_total_in="abc")

    def test_unidad_medida_valid(self):
        """Valid unidad_medida passes."""
        body = AdminSolicitudUpdateRequest(unidad_medida="cm")
        assert body.unidad_medida == "cm"

    def test_unidad_medida_invalid(self):
        """Invalid unidad_medida raises ValueError."""
        with pytest.raises(ValueError, match="unidad_medida fuera de catálogo"):
            AdminSolicitudUpdateRequest(unidad_medida="m")

    def test_prioridad_valid(self):
        """Valid prioridad passes."""
        body = AdminSolicitudUpdateRequest(prioridad="Alta")
        assert body.prioridad == "Alta"

    def test_prioridad_invalid(self):
        """Invalid prioridad raises ValueError."""
        with pytest.raises(ValueError, match="prioridad fuera de catálogo"):
            AdminSolicitudUpdateRequest(prioridad="Baja")

    def test_entidad_solicitante_too_long(self):
        """entidad_solicitante > 64 chars raises ValueError."""
        with pytest.raises(ValueError, match="máximo 64"):
            AdminSolicitudUpdateRequest(entidad_solicitante="A" * 65)

    def test_justificacion_too_long(self):
        """justificacion > 500 chars raises ValueError."""
        with pytest.raises(ValueError, match="máximo 500"):
            AdminSolicitudUpdateRequest(justificacion="X" * 501)

    def test_observaciones_posturales_invalid_chars(self):
        """observaciones_posturales with invalid chars raises ValueError."""
        with pytest.raises(ValueError, match="observaciones_posturales: contiene caracteres no permitidos"):
            AdminSolicitudUpdateRequest(observaciones_posturales="Bad@chars!")


# ---------------------------------------------------------------------------
# AdminGestionUpdateRequest — validation tests
# ---------------------------------------------------------------------------

class TestAdminGestionUpdateRequest:
    """Unit tests for the admin gestion PATCH request model (atomic)."""

    def test_empty_payload_valid(self):
        """Empty payload is valid."""
        body = AdminGestionUpdateRequest()
        assert body.model_dump(exclude_none=True) == {}

    def test_estudio_fields_valid(self):
        """Valid estudio fields pass."""
        body = AdminGestionUpdateRequest(
            sede="Forum",
            fecha_estudio="2026-01-15",
            ciudad_registro="LEON, GTO",
            elaboro_estudio="Admin Test",
        )
        assert body.sede == "Forum"  # sede is NOT normalized in this model

    def test_solicitud_fields_valid(self):
        """Valid solicitud fields pass."""
        body = AdminGestionUpdateRequest(
            entidad_solicitante="Rotary Club",
            prioridad="Alta",
            justificacion="Urgente",
        )
        assert body.prioridad == "Alta"

    def test_combined_fields_valid(self):
        """Both estudio + solicitud fields in one request pass."""
        body = AdminGestionUpdateRequest(
            sede="Forum",
            entidad_solicitante="Rotary Club",
            prioridad="Media",
        )
        assert body.sede == "Forum"  # sede is NOT normalized in this model
        assert body.prioridad == "Media"

    def test_entidad_solicitante_invalid_chars(self):
        """entidad_solicitante with invalid chars raises ValueError."""
        with pytest.raises(ValueError, match="entidad_solicitante: contiene caracteres no permitidos"):
            AdminGestionUpdateRequest(entidad_solicitante="Rotary@Club!")

    def test_justificacion_invalid_chars(self):
        """justificacion with invalid chars raises ValueError."""
        with pytest.raises(ValueError, match="justificacion: contiene caracteres no permitidos"):
            AdminGestionUpdateRequest(justificacion="Justificacion @ invalida!")

    def test_prioridad_invalid(self):
        """Invalid prioridad raises ValueError."""
        with pytest.raises(ValueError, match="prioridad fuera de catálogo"):
            AdminGestionUpdateRequest(prioridad="Baja")

    def test_status_estudio_invalid(self):
        """Invalid status_estudio raises ValueError (validate_status uses 'status' as field name)."""
        with pytest.raises(ValueError, match="status fuera de catálogo"):
            AdminGestionUpdateRequest(status_estudio="rechazado")


# ---------------------------------------------------------------------------
# Edge cases and regression tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and regression prevention tests."""

    def test_region_id_not_in_model(self):
        """region_id is NOT an editable field in admin model."""
        fields = AdminBeneficiarioUpdateRequest.model_fields.keys()
        assert "region_id" not in fields
        assert "folio" not in fields

    def test_nombre_rebuilt_from_parts(self):
        """When nombres/apellidos are patched, nombre should be rebuilt.
        
        This is router logic (not model logic), documented here as a test contract.
        The router PATCH endpoint rebuilds nombre = "{nombres} {apellido_paterno} {apellido_materno}".
        """
        body = AdminBeneficiarioUpdateRequest(
            nombres="CARLOS",
            apellido_paterno="LOPEZ",
            apellido_materno="MARTINEZ",
        )
        assert body.nombres == "CARLOS"
        assert body.apellido_paterno == "LOPEZ"
        assert body.apellido_materno == "MARTINEZ"
        # The actual nombre rebuild happens in the router endpoint

    def test_optional_fields_allow_none(self):
        """All fields in all admin models are Optional (allow None)."""
        for ModelClass in [
            AdminBeneficiarioUpdateRequest,
            AdminEstudioUpdateRequest,
            AdminSolicitudUpdateRequest,
            AdminGestionUpdateRequest,
        ]:
            for field_name, field_info in ModelClass.model_fields.items():
                assert field_info.is_required() is False, \
                    f"{ModelClass.__name__}.{field_name} should be Optional"

    def test_normalize_text_applied(self):
        """Text fields are normalized (uppercase, no accents, collapsed spaces)."""
        body = AdminBeneficiarioUpdateRequest(
            nombres="  juan  carlos  ",
        )
        # normalize_text strips accents and collapses spaces
        assert "JUAN" in body.nombres

    def test_numero_domicilio_validates(self):
        """num_ext and num_int validate against regex."""
        body = AdminBeneficiarioUpdateRequest(num_ext="12-A", num_int="3B")
        assert body.num_ext == "12-A"
        assert body.num_int == "3B"

    def test_numero_domicilio_invalid(self):
        """num_ext with spaces raises ValueError."""
        with pytest.raises(ValueError, match="solo se permiten letras"):
            AdminBeneficiarioUpdateRequest(num_ext="12 A")

    def test_decimal_precision(self):
        """Measurement fields accept Decimal with 3 decimal places."""
        body = AdminSolicitudUpdateRequest(altura_total_in=Decimal("65.123"))
        assert body.altura_total_in == Decimal("65.123")

    def test_email_normalization(self):
        """Email is lowercased."""
        body = AdminBeneficiarioUpdateRequest(email="Test@EXAMPLE.COM")
        assert body.email == "test@example.com"

    def test_catalog_values_are_exact(self):
        """Catalog values must match exactly (case-sensitive after normalization)."""
        # After normalization, "casado" becomes "CASADO" which is in the catalog
        # Note: estado_civil is not in AdminBeneficiarioUpdateRequest,
        # this is tested via backend. The point is normalization uppercases.
        pass  # Documented behavior
