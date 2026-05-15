"""
Unit tests for backend/validators.py — pure function tests, no DB required.

Tests for:
- validate_observaciones_posturales: whitelist regex, maxlength 500, returns string
- validate_medida_tecnica: digits+single-dot, max 4 integer digits, max 3 decimal
  digits, normalizes to Decimal with 3 decimal places
"""

import pytest
from decimal import Decimal


class TestValidateObservacionesPosturales:
    """Tests for the observaciones_posturales whitelist validator."""

    def test_pasa_texto_valido_basico(self):
        """Valid text with letters, numbers, spaces, and allowed punctuation passes."""
        from validators import validate_observaciones_posturales

        result = validate_observaciones_posturales("Paciente con escoliosis leve.")
        assert result == "Paciente con escoliosis leve."

    def test_pasa_con_tildes_y_enie(self):
        """Spanish accented characters and ñ are in the whitelist."""
        from validators import validate_observaciones_posturales

        result = validate_observaciones_posturales("Áéíóú ñÑ üÜ - diagnóstico: cifosis.")
        assert result == "Áéíóú ñÑ üÜ - diagnóstico: cifosis."

    def test_pasa_con_numeros_y_simbolos_permitidos(self):
        """Numbers and allowed symbols () / - . , : ; pass through."""
        from validators import validate_observaciones_posturales

        result = validate_observaciones_posturales(
            "Paciente 2 (3/4): mide 1.50 m, peso: 45; angulo 30."
        )
        assert "Paciente 2" in result
        assert "1.50" in result
        assert "45" in result

    def test_rechaza_caracteres_no_permitidos(self):
        """Characters outside the whitelist (@, #, $, <, >, etc.) raise ValueError."""
        from validators import validate_observaciones_posturales

        with pytest.raises(ValueError, match="observaciones_posturales"):
            validate_observaciones_posturales("email@dominio.com")

        with pytest.raises(ValueError, match="observaciones_posturales"):
            validate_observaciones_posturales("precio: $100")

        with pytest.raises(ValueError, match="observaciones_posturales"):
            validate_observaciones_posturales("<script>alert(1)</script>")

    def test_rechaza_excede_maxlength(self):
        """Text longer than 500 characters raises ValueError."""
        from validators import validate_observaciones_posturales

        long_text = "x" * 501
        with pytest.raises(ValueError, match="observaciones_posturales"):
            validate_observaciones_posturales(long_text)

    def test_pasa_exactamente_500_chars(self):
        """Text of exactly 500 characters passes validation."""
        from validators import validate_observaciones_posturales

        text = "a" * 500  # All within whitelist
        result = validate_observaciones_posturales(text)
        assert len(result) == 500

    def test_pasa_string_vacio(self):
        """Empty string passes (will be treated as None/optional by Pydantic)."""
        from validators import validate_observaciones_posturales

        result = validate_observaciones_posturales("")
        assert result == ""


class TestValidateMedidaTecnica:
    """Tests for the medida técnica validator — digit+dots, normalization to Decimal."""

    def test_pasa_entero_simple(self):
        """Simple integer string is normalized to Decimal with 3 decimal places."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("2", "altura_total_in")
        assert result == Decimal("2.000")

    def test_pasa_entero_con_leading_zeros(self):
        """Leading zeros are stripped during normalization."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("002", "altura_total_in")
        assert result == Decimal("2.000")

    def test_pasa_decimal_tres_digitos(self):
        """Decimal with 3 decimal places is preserved."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("2.100", "altura_total_in")
        assert result == Decimal("2.100")

    def test_pasa_decimal_un_digito(self):
        """Decimal with 1 decimal place is normalized to 3."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("2.1", "peso_kg")
        assert result == Decimal("2.100")

    def test_pasa_valor_grande_dentro_limite(self):
        """Value of 1000.320 (4 integer, 3 decimal) passes."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("1000.320", "altura_total_in")
        assert result == Decimal("1000.320")

    def test_pasa_valor_maximo(self):
        """Value of 9999.999 (max allowed) passes."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("9999.999", "altura_total_in")
        assert result == Decimal("9999.999")

    def test_pasa_valor_minimo_cero(self):
        """Value of 0 passes."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("0", "peso_kg")
        assert result == Decimal("0.000")

    def test_pasa_cero_punto_algo(self):
        """Value of 0.5 passes."""
        from validators import validate_medida_tecnica

        result = validate_medida_tecnica("0.5", "peso_kg")
        assert result == Decimal("0.500")

    def test_rechaza_mas_de_4_enteros(self):
        """5 integer digits raise ValueError with field name in message."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="altura_total_in"):
            validate_medida_tecnica("12345", "altura_total_in")

    def test_rechaza_mas_de_3_decimales(self):
        """4 decimal places raise ValueError."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="medida_cabeza_asiento"):
            validate_medida_tecnica("2.1234", "medida_cabeza_asiento")

    def test_rechaza_dos_puntos(self):
        """Two decimal points raise ValueError."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="altura_total_in"):
            validate_medida_tecnica("1..2", "altura_total_in")

    def test_rechaza_coma_como_separador(self):
        """Comma as decimal separator raises ValueError."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="peso_kg"):
            validate_medida_tecnica("12,3", "peso_kg")

    def test_rechaza_letras(self):
        """Alphabetic characters raise ValueError."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="altura_total_in"):
            validate_medida_tecnica("abc", "altura_total_in")

    def test_rechaza_numero_negativo(self):
        """Negative sign raises ValueError."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="peso_kg"):
            validate_medida_tecnica("-2", "peso_kg")

    def test_rechaza_solo_punto(self):
        """A single dot without digits raises ValueError."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="altura_total_in"):
            validate_medida_tecnica(".", "altura_total_in")

    def test_pasa_decimal_point_leading(self):
        """Value like .5 should be rejected (no leading digit)."""
        from validators import validate_medida_tecnica

        with pytest.raises(ValueError, match="altura_total_in"):
            validate_medida_tecnica(".5", "altura_total_in")


class TestValidateEntidadSolicitante:
    """Tests for the entidad_solicitante whitelist validator."""

    def test_pasa_texto_valido_basico(self):
        """Valid text with letters, numbers, spaces, and allowed punctuation passes."""
        from validators import validate_entidad_solicitante

        result = validate_entidad_solicitante("Hospital Civil")
        assert result == "Hospital Civil"

    def test_pasa_con_tildes_y_enie(self):
        """Spanish accented characters and ñ are in the whitelist."""
        from validators import validate_entidad_solicitante

        result = validate_entidad_solicitante("Clínica Médica")
        assert result == "Clínica Médica"

    def test_pasa_con_numeros_y_simbolos_permitidos(self):
        """Numbers and allowed symbols () / - . , pass through."""
        from validators import validate_entidad_solicitante

        result = validate_entidad_solicitante("DIF (Sede 1-A)")
        assert result == "DIF (Sede 1-A)"

    def test_rechaza_caracteres_no_permitidos(self):
        """Characters outside the whitelist (@, #, $, <, >, etc.) raise ValueError."""
        from validators import validate_entidad_solicitante

        with pytest.raises(ValueError, match="entidad_solicitante"):
            validate_entidad_solicitante("email@dominio.com")

        with pytest.raises(ValueError, match="entidad_solicitante"):
            validate_entidad_solicitante("precio: $100")

        with pytest.raises(ValueError, match="entidad_solicitante"):
            validate_entidad_solicitante("<script>alert(1)</script>")

    def test_rechaza_excede_maxlength(self):
        """Text longer than 12 characters raises ValueError."""
        from validators import validate_entidad_solicitante

        with pytest.raises(ValueError, match="entidad_solicitante"):
            validate_entidad_solicitante("Hospital Civil de León")

    def test_pasa_exactamente_12_chars(self):
        """Text of exactly 12 characters passes validation."""
        from validators import validate_entidad_solicitante

        text = "a" * 12
        result = validate_entidad_solicitante(text)
        assert len(result) == 12

    def test_pasa_string_vacio(self):
        """Empty string passes (will be treated as None/optional by Pydantic)."""
        from validators import validate_entidad_solicitante

        result = validate_entidad_solicitante("")
        assert result == ""


class TestValidateJustificacion:
    """Tests for the justificacion whitelist validator."""

    def test_pasa_texto_valido_basico(self):
        """Valid text with letters, numbers, spaces, and allowed punctuation passes."""
        from validators import validate_justificacion

        result = validate_justificacion("Paciente requiere silla urgente.")
        assert result == "Paciente requiere silla urgente."

    def test_pasa_con_tildes_y_enie(self):
        """Spanish accented characters and ñ are in the whitelist."""
        from validators import validate_justificacion

        result = validate_justificacion("Áéíóú ñÑ üÜ - diagnóstico: cifosis.")
        assert result == "Áéíóú ñÑ üÜ - diagnóstico: cifosis."

    def test_pasa_con_numeros_y_simbolos_permitidos(self):
        """Numbers and allowed symbols () / - . , : ; pass through."""
        from validators import validate_justificacion

        result = validate_justificacion(
            "Paciente 2 (3/4): mide 1.50 m, peso: 45; angulo 30."
        )
        assert "Paciente 2" in result
        assert "1.50" in result
        assert "45" in result

    def test_rechaza_caracteres_no_permitidos(self):
        """Characters outside the whitelist (@, #, $, <, >, etc.) raise ValueError."""
        from validators import validate_justificacion

        with pytest.raises(ValueError, match="justificacion"):
            validate_justificacion("email@dominio.com")

        with pytest.raises(ValueError, match="justificacion"):
            validate_justificacion("precio: $100")

        with pytest.raises(ValueError, match="justificacion"):
            validate_justificacion("<script>alert(1)</script>")

    def test_rechaza_excede_maxlength(self):
        """Text longer than 500 characters raises ValueError."""
        from validators import validate_justificacion

        long_text = "x" * 501
        with pytest.raises(ValueError, match="justificacion"):
            validate_justificacion(long_text)

    def test_pasa_exactamente_500_chars(self):
        """Text of exactly 500 characters passes validation."""
        from validators import validate_justificacion

        text = "a" * 500
        result = validate_justificacion(text)
        assert len(result) == 500

    def test_pasa_string_vacio(self):
        """Empty string passes (will be treated as None/optional by Pydantic)."""
        from validators import validate_justificacion

        result = validate_justificacion("")
        assert result == ""
