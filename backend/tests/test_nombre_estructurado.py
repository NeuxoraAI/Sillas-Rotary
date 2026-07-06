"""
Unit tests for BeneficiarioIn structured name fields.

Tests the Pydantic model validators directly — no database required.
Follows strict TDD: tests written BEFORE implementation.
"""

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# RED PHASE — These tests import BeneficiarioIn which currently has
# a single "nombre" field.  After the model is refactored (GREEN), these
# tests will pass against the NEW model with nombres/apellido_paterno/
# apellido_materno.
#
# Until the model is refactored, tests that reference the new field names
# will FAIL because the current model does not have those fields.
# ---------------------------------------------------------------------------


class TestNombreEstructuradoValidacion:
    """Unit tests for BeneficiarioIn name field validators."""

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _make_input(nombres="JUAN", apellido_paterno="PEREZ", apellido_materno="LOPEZ", **overrides):
        """Build a payload that satisfies all non-name requirements."""
        base = {
            "nombres": nombres,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "fecha_nacimiento": "1990-05-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test",
            "num_ext": "12A",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "estado_nombre": "GUANAJUATO",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        base.update(overrides)
        return base

    # -- normalization ----------------------------------------------------

    @pytest.mark.parametrize("raw,expected", [
        ("José Ángel", "JOSE ANGEL"),
        ("María Fernanda", "MARIA FERNANDA"),
        ("juan", "JUAN"),
        ("GARCÍA", "GARCIA"),
        ("PÉREZ", "PEREZ"),
        ("  juan   carlos  ", "JUAN CARLOS"),
        ("Núñez", "NUNEZ"),
        ("Ángel Ü", "ANGEL U"),
    ])
    def test_nombres_normalization_removes_accents_and_uppercases(self, raw, expected):
        """Normalize_text should strip accents, uppercase, and compact spaces."""
        from routers.socioeconomico import BeneficiarioIn

        data = self._make_input(nombres=raw)
        obj = BeneficiarioIn(**data)
        assert obj.nombres == expected

    @pytest.mark.parametrize("raw,expected", [
        ("García", "GARCIA"),
        ("Pérez", "PEREZ"),
        ("de la Cruz", "DE LA CRUZ"),
    ])
    def test_apellido_paterno_normalization(self, raw, expected):
        """Apellido paterno normalization strips accents and uppercases."""
        from routers.socioeconomico import BeneficiarioIn

        obj = BeneficiarioIn(**self._make_input(apellido_paterno=raw))
        assert obj.apellido_paterno == expected

    def test_apellido_paterno_rechaza_apostrofo(self):
        """Política vigente de validación (`_NOMBRE_RE`): los nombres/apellidos NO
        permiten apóstrofo. Un apellido con `'` es rechazado (ValidationError)."""
        from pydantic import ValidationError
        from routers.socioeconomico import BeneficiarioIn

        with pytest.raises(ValidationError):
            BeneficiarioIn(**self._make_input(apellido_paterno="Mc'Donald"))

    @pytest.mark.parametrize("raw,expected", [
        ("López", "LOPEZ"),
        ("Gutiérrez", "GUTIERREZ"),
    ])
    def test_apellido_materno_normalization(self, raw, expected):
        """Apellido materno normalization strips accents and uppercases."""
        from routers.socioeconomico import BeneficiarioIn

        obj = BeneficiarioIn(**self._make_input(apellido_materno=raw))
        assert obj.apellido_materno == expected

    # -- length validation ------------------------------------------------

    @pytest.mark.parametrize("field,value", [
        ("nombres", "A"),               # too short (< 2)
        ("nombres", "A" * 61),          # too long (> 60)
        ("apellido_paterno", "A"),      # too short
        ("apellido_paterno", "A" * 41),  # too long (> 40)
        ("apellido_materno", "A"),      # too short
        ("apellido_materno", "A" * 41),  # too long (> 40)
        ("apellido_materno", ""),       # empty
    ])
    def test_invalid_length_rejected(self, field, value):
        """Fields outside their length range should raise ValidationError."""
        from routers.socioeconomico import BeneficiarioIn

        data = self._make_input(**{field: value})
        with pytest.raises(ValidationError) as exc_info:
            BeneficiarioIn(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == field for e in errors), \
            f"Expected error on {field}, got: {errors}"

    @pytest.mark.parametrize("field,value", [
        ("nombres", "AB"),                              # exactly 2
        ("nombres", "A" * 60),                          # exactly 60
        ("apellido_paterno", "AB"),                     # exactly 2
        ("apellido_paterno", "A" * 40),                 # exactly 40
        ("apellido_materno", "AB"),                     # exactly 2
        ("apellido_materno", "A" * 40),                 # exactly 40
    ])
    def test_boundary_lengths_accepted(self, field, value):
        """Boundary length values should be accepted."""
        from routers.socioeconomico import BeneficiarioIn

        data = self._make_input(**{field: value})
        obj = BeneficiarioIn(**data)
        assert getattr(obj, field) == value.upper() if value else value

    # -- character validation ---------------------------------------------

    @pytest.mark.parametrize("field,invalid_value", [
        ("nombres", "Juan123"),
        ("nombres", "O'Brien"),
        ("nombres", "García!"),
        ("nombres", "nombre@"),
        ("nombres", "Juan#Luis"),
        ("apellido_paterno", "García1"),
        ("apellido_paterno", "Pérez!"),
        ("apellido_paterno", "López$"),
        ("apellido_materno", "123"),
        ("apellido_materno", "R@mos"),
        ("apellido_materno", "López#"),
    ])
    def test_invalid_characters_rejected(self, field, invalid_value):
        """Digits and special characters should cause ValidationError."""
        from routers.socioeconomico import BeneficiarioIn

        data = self._make_input(**{field: invalid_value})
        with pytest.raises(ValidationError) as exc_info:
            BeneficiarioIn(**data)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == field for e in errors), \
            f"Expected error on {field}, got: {errors}"

    @pytest.mark.parametrize("field,valid_value", [
        ("nombres", "José Ángel"),
        ("nombres", "María"),
        ("apellido_paterno", "García López"),
        ("apellido_paterno", "De La Cruz"),
        ("apellido_materno", "Álvarez"),
        ("apellido_materno", "Gómez Santos"),
    ])
    def test_valid_characters_accepted(self, field, valid_value):
        """Valid Spanish names with accents and spaces should be accepted."""
        from routers.socioeconomico import BeneficiarioIn

        data = self._make_input(**{field: valid_value})
        obj = BeneficiarioIn(**data)
        assert getattr(obj, field) is not None

    # -- field presence ---------------------------------------------------

    def test_old_nombre_field_not_accepted(self):
        """The old 'nombre' field should no longer be in BeneficiarioIn."""
        from routers.socioeconomico import BeneficiarioIn

        # The new model should not have 'nombre' as a field
        data = self._make_input()
        data.pop("nombres")
        data["nombre"] = "JUAN PEREZ"
        with pytest.raises(ValidationError):
            BeneficiarioIn(**data)

    def test_structured_fields_required(self):
        """All three structured name fields are required."""
        from routers.socioeconomico import BeneficiarioIn

        data = self._make_input()
        del data["nombres"]
        with pytest.raises(ValidationError) as exc_info:
            BeneficiarioIn(**data)
        errors = exc_info.value.errors()
        assert any("nombres" in e["loc"] for e in errors), \
            f"Expected missing nombres error, got: {errors}"


class TestNormalizeTextUtilities:
    """Direct tests for normalize_text utility (already exists, behaviour preserved)."""

    def test_normalize_text_compacts_spaces(self):
        from utils.text import normalize_text
        assert normalize_text("  juan   carlos  ") == "JUAN CARLOS"

    def test_normalize_text_strips_accents(self):
        from utils.text import normalize_text
        assert normalize_text("José Ángel") == "JOSE ANGEL"
        assert normalize_text("García") == "GARCIA"

    def test_normalize_text_none_returns_none(self):
        from utils.text import normalize_text
        assert normalize_text(None) is None

    def test_normalize_text_empty_returns_none(self):
        from utils.text import normalize_text
        assert normalize_text("   ") is None
