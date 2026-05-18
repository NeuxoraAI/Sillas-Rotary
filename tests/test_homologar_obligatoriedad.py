"""
Tests for PRD "Homologar obligatoriedad tecnica y gestion" — backend validators.

Strict TDD: These tests are written BEFORE implementation.
They reference model_validators that do NOT exist yet (RED phase).

Tests T1-T3 (Phase 1 — Backend):
  T1: SolicitudCreateRequest model_validator for medidas + entidad + prioridad
  T2: SolicitudUpdateRequest model_validator (same rules)
  T3: EstudioUpdateRequest extended model_validator
"""

import os

# Inject a test JWT secret BEFORE importing production modules.
# Production code fails fast if JWT_SECRET is missing or weak.
os.environ.setdefault("JWT_SECRET", "test-secret-" + ("x" * 32))

import pytest
from pydantic import ValidationError


# =============================================================================
# T1 — SolicitudCreateRequest model_validator
# =============================================================================

class TestSolicitudCreateCompletoValidator:
    """Unit tests for the new model_validator on SolicitudCreateRequest."""

    @staticmethod
    def _base_payload(**overrides):
        """Minimal valid payload for SolicitudCreateRequest."""
        data = {
            "beneficiario_id": 1,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
        }
        data.update(overrides)
        return data

    # --- T1a: status="completo" requires all medidas ---

    def test_completo_sin_medidas_retorna_error(self):
        """status=completo without medidas should raise ValidationError."""
        from backend.routers.tecnica import SolicitudCreateRequest

        with pytest.raises(ValidationError) as exc_info:
            SolicitudCreateRequest(**self._base_payload(status="completo"))

        # At least one error from the model_validator
        errors = exc_info.value.errors()
        assert len(errors) >= 1

    # --- T1b: status="completo" with all fields → success ---

    def test_completo_con_todos_los_campos_ok(self):
        """status=completo with all required fields should succeed."""
        from backend.routers.tecnica import SolicitudCreateRequest

        solicitud = SolicitudCreateRequest(**self._base_payload(
            status="completo",
            altura_total_in=40,
            peso_kg=70,
            medida_cabeza_asiento=10,
            medida_hombro_asiento=12,
            medida_prof_asiento=14,
            medida_rodilla_talon=16,
            medida_ancho_cadera=18,
            entidad_solicitante="DIF Municipal",
            prioridad="Media",
        ))
        assert solicitud.status == "completo"
        assert solicitud.altura_total_in is not None
        assert solicitud.entidad_solicitante == "DIF Municipal"
        assert solicitud.prioridad == "Media"

    # --- T1c: status="borrador" → validator skipped ---

    def test_borrador_sin_medidas_ok(self):
        """status=borrador without medidas should succeed."""
        from backend.routers.tecnica import SolicitudCreateRequest

        solicitud = SolicitudCreateRequest(**self._base_payload(status="borrador"))
        assert solicitud.status == "borrador"
        assert solicitud.altura_total_in is None
        assert solicitud.entidad_solicitante is None

    def test_borrador_con_medidas_parciales_ok(self):
        """status=borrador with only some measures filled should succeed."""
        from backend.routers.tecnica import SolicitudCreateRequest

        solicitud = SolicitudCreateRequest(**self._base_payload(
            status="borrador",
            altura_total_in=40,
            peso_kg=70,
        ))
        assert solicitud.status == "borrador"
        assert solicitud.altura_total_in is not None
        assert solicitud.medida_cabeza_asiento is None


# =============================================================================
# T2 — SolicitudUpdateRequest model_validator
# =============================================================================

class TestSolicitudUpdateCompletoValidator:
    """Unit tests for the new model_validator on SolicitudUpdateRequest."""

    # --- T2a: status="completo" validates ---

    def test_update_completo_sin_medidas_retorna_error(self):
        """PATCH status=completo without medidas should fail."""
        from backend.routers.tecnica import SolicitudUpdateRequest

        with pytest.raises(ValidationError) as exc_info:
            SolicitudUpdateRequest(status="completo")

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_update_completo_medidas_parciales_retorna_error(self):
        """PATCH status=completo with only one measure filled should fail."""
        from backend.routers.tecnica import SolicitudUpdateRequest

        with pytest.raises(ValidationError) as exc_info:
            SolicitudUpdateRequest(
                status="completo",
                altura_total_in=40,
                # missing the other 6 medidas
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1

    def test_update_completo_con_todos_los_campos_ok(self):
        """PATCH status=completo with all fields should succeed."""
        from backend.routers.tecnica import SolicitudUpdateRequest

        solicitud = SolicitudUpdateRequest(
            status="completo",
            altura_total_in=40,
            peso_kg=70,
            medida_cabeza_asiento=10,
            medida_hombro_asiento=12,
            medida_prof_asiento=14,
            medida_rodilla_talon=16,
            medida_ancho_cadera=18,
            entidad_solicitante="DIF Municipal",
            prioridad="Media",
        )
        assert solicitud.status == "completo"
        assert solicitud.altura_total_in is not None

    # --- T2b: status=None / status="borrador" → validator skipped ---

    def test_update_sin_status_ok(self):
        """PATCH without status should succeed (validator skipped)."""
        from backend.routers.tecnica import SolicitudUpdateRequest

        solicitud = SolicitudUpdateRequest(
            entorno="Urbano / Interiores",
            altura_total_in=40,
        )
        assert solicitud.status is None

    def test_update_borrador_sin_medidas_ok(self):
        """PATCH status=borrador without medidas should succeed."""
        from backend.routers.tecnica import SolicitudUpdateRequest

        solicitud = SolicitudUpdateRequest(
            status="borrador",
            entorno="Urbano / Interiores",
        )
        assert solicitud.status == "borrador"
        assert solicitud.altura_total_in is None

    def test_update_borrador_con_medidas_parciales_ok(self):
        """PATCH status=borrador with some measures should succeed."""
        from backend.routers.tecnica import SolicitudUpdateRequest

        solicitud = SolicitudUpdateRequest(
            status="borrador",
            altura_total_in=40,
        )
        assert solicitud.status == "borrador"


# =============================================================================
# T3 — EstudioUpdateRequest extended model_validator
# =============================================================================

class TestEstudioUpdateCompletoValidator:
    """Unit tests for the extended model_validator on EstudioUpdateRequest."""

    # --- T3a: status="completo" requires tuvo_silla_previa ---

    def test_completo_sin_tuvo_silla_previa_retorna_error(self):
        """status=completo without tuvo_silla_previa should fail."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        with pytest.raises(ValidationError) as exc_info:
            EstudioUpdateRequest(
                status="completo",
                fecha_estudio="2026-05-17",
            )

        errors = exc_info.value.errors()
        assert any("tuvo_silla_previa" in str(e.get("msg", "")) for e in errors)

    # --- T3b: conditional como_obtuvo_silla ---

    def test_completo_tuvo_silla_true_sin_como_obtuvo_retorna_error(self):
        """status=completo, tuvo_silla_previa=True, como_obtuvo_silla=None."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        with pytest.raises(ValidationError) as exc_info:
            EstudioUpdateRequest(
                status="completo",
                fecha_estudio="2026-05-17",
                tuvo_silla_previa=True,
                # como_obtuvo_silla missing (None by default)
            )

        errors = exc_info.value.errors()
        assert any("como_obtuvo_silla" in str(e.get("msg", "")) for e in errors)

    def test_completo_tuvo_silla_true_como_obtuvo_vacio_retorna_error(self):
        """status=completo, tuvo_silla_previa=True, como_obtuvo_silla=""."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        with pytest.raises(ValidationError) as exc_info:
            EstudioUpdateRequest(
                status="completo",
                fecha_estudio="2026-05-17",
                tuvo_silla_previa=True,
                como_obtuvo_silla="",
            )

        errors = exc_info.value.errors()
        assert any("como_obtuvo_silla" in str(e.get("msg", "")) for e in errors)

    # --- T3c: tuvo_silla_previa=False → como_obtuvo_silla NOT required ---

    def test_completo_tuvo_silla_false_sin_como_obtuvo_ok(self):
        """status=completo, tuvo_silla_previa=False, sin como_obtuvo_silla."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        estudio = EstudioUpdateRequest(
            status="completo",
            fecha_estudio="2026-05-17",
            tuvo_silla_previa=False,
            # como_obtuvo_silla can be None
        )
        assert estudio.status == "completo"
        assert estudio.tuvo_silla_previa is False

    def test_completo_tuvo_silla_false_con_como_obtuvo_ok(self):
        """status=completo, tuvo_silla_previa=False, como_obtuvo_silla non-empty is ok."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        estudio = EstudioUpdateRequest(
            status="completo",
            fecha_estudio="2026-05-17",
            tuvo_silla_previa=False,
            como_obtuvo_silla="Donación",
        )
        assert estudio.status == "completo"

    # --- T3d: status="borrador" → validator skipped for new fields ---

    def test_borrador_sin_tuvo_silla_previa_ok(self):
        """status=borrador without tuvo_silla_previa should succeed."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        estudio = EstudioUpdateRequest(status="borrador")
        assert estudio.status == "borrador"
        assert estudio.tuvo_silla_previa is None

    # --- T3e: fecha_estudio still required for completo (existing behavior preserved) ---

    def test_completo_sin_fecha_estudio_retorna_error(self):
        """status=completo without fecha_estudio should still fail."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        with pytest.raises(ValidationError) as exc_info:
            EstudioUpdateRequest(
                status="completo",
                tuvo_silla_previa=False,
                # fecha_estudio missing
            )

        errors = exc_info.value.errors()
        assert any("fecha_estudio" in str(e.get("msg", "")) for e in errors)

    def test_completo_con_todos_los_campos_ok(self):
        """status=completo with all fields should succeed."""
        from backend.routers.socioeconomico import EstudioUpdateRequest

        estudio = EstudioUpdateRequest(
            status="completo",
            fecha_estudio="2026-05-17",
            tuvo_silla_previa=True,
            como_obtuvo_silla="Donación",
        )
        assert estudio.status == "completo"
        assert estudio.tuvo_silla_previa is True
