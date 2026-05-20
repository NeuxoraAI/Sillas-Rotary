"""
Unit tests for backend/validators.py — pure function tests, no DB required.

Tests for:
- validate_observaciones_posturales: whitelist regex, maxlength 500, returns string
- validate_medida_tecnica: digits+single-dot, max 4 integer digits, max 3 decimal
  digits, normalizes to Decimal with 3 decimal places
- validate_entidad_solicitante: whitelist regex, maxlength 64
- validate_justificacion: whitelist regex, maxlength 500
- validate_nombre: letters+spaces+dots, min 2 max 60
- validate_apellido: letters+spaces+dots, min 2 max 40
- validate_diagnostico: letters+numbers+symbols, min 3 max 160
- validate_calle: letters+numbers+symbols, min 3 max 120
- validate_telefono: exactly 10 digits
- validate_catalog: frozenset membership
- validate_entorno, validate_control_tronco, validate_control_cabeza: catalog validators
"""

import pytest
from decimal import Decimal


class TestValidateObservacionesPosturales:
    """Tests for the observaciones_posturales whitelist validator."""

    def test_pasa_texto_valido_basico(self):
        """Valid text with letters, numbers, spaces, and allowed punctuation passes."""
        from validators import validate_observaciones_posturales

       !result = validate_observaciones_posturales("Paciente con escoliosis leve.")
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
        """Text longer than 64 characters raises ValueError."""
        from validators import validate_entidad_solicitante

        with pytest.raises(ValueError, match="entidad_solicitante"):
            validate_entidad_solicitante("Hospital Civil de León Gto. México - Sede Principal Norte")

    def test_pasa_exactamente_64_chars(self):
        """Text of exactly 64 characters passes validation."""
        from validators import validate_entidad_solicitante

        text = "a" * 64
        result = validate_entidad_solicitante(text)
        assert len(result) == 64

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


class TestValidateNombre:
    """Tests for validate_nombre and validate_apellido."""

    def test_pasa_nombre_valido(self):
        from validators import validate_nombre
        result = validate_nombre("JUAN")
        assert result == "JUAN"

    def test_rechaza_nombre_corto(self):
        from validators import validate_nombre
        with pytest.raises(ValueError, match="nombres"):
            validate_nombre("J")

    def test_rechaza_nombre_largo(self):
        from validators import validate_nombre
        with pytest.raises(ValueError, match="nombres"):
            validate_nombre("A" * 61)

    def test_rechaza_nombre_con_numeros(self):
        from validators import validate_nombre
        with pytest.raises(ValueError, match="nombres"):
            validate_nombre("JUAN123")

    def test_pasa_apellido_valido(self):
        from validators import validate_apellido
        result = validate_apellido("PEREZ", "apellido_paterno")
        assert result == "PEREZ"

    def test_rechaza_apellido_corto(self):
        from validators import validate_apellido
        with pytest.raises(ValueError, match="apellido_paterno"):
            validate_apellido("P", "apellido_paterno")


class TestValidateDiagnostico:
    """Tests for validate_diagnostico."""

    def test_pasa_diagnostico_valido(self):
        from validators import validate_diagnostico
        result = validate_diagnostico("Escoliosis leve (grado 1)")
        assert result == "Escoliosis leve (grado 1)"

    def test_rechaja_diagnostico_corto(self):
        from validators import validate_diagnostico
        with pytest.raises(ValueError, match="diagnostico"):
            validate_diagnostico("AB")

    def test_rechaza_diagnostico_largo(self):
        from validators import validate_diagnostico
        with pytest.raises(ValueError, match="diagnostico"):
            validate_diagnostico("D" * 161)

    def test_rechaza_diagnostico_con_chars_invalidos(self):
        from validators import validate_diagnostico
        with pytest.raises(ValueError, match="diagnostico"):
            validate_diagnostico("Escoliosis @ leve")


class TestValidateTelefono:
    """Tests for validate_telefono."""

    def test_pasa_telefono_valido(self):
        from validators import validate_telefono
        result = validate_telefono("1234567890")
        assert result == "1234567890"

    def test_pasa_telefono_con_guiones(self):
        from validators import validate_telefono
        result = validate_telefono("123-456-7890")
        assert result == "1234567890"

    def test_rechaza_telefono_corto(self):
        from validators import validate_telefono
        with pytest.raises(ValueError, match="teléfono"):
            validate_telefono("123456789")

    def test_rechaza_telefono_con_letras(self):
        from validators import validate_telefono
        with pytest.raises(ValueError, match="teléfono"):
            validate_telefono("123456789A")

    def test_rechaza_vacio(self):
        from validators import validate_telefono
        with pytest.raises(ValueError, match="teléfono"):
            validate_telefono("")


class TestValidateCatalog:
    """Tests for validate_catalog and specific catalog validators."""

    def test_pasa_valor_en_catalogo(self):
        from validators import validate_catalog
        result = validate_catalog("SOLTERO", frozenset({"SOLTERO", "CASADO"}), "estado_civil")
        assert result == "SOLTERO"

    def test_rechaza_valor_fuera_de_catalogo(self):
        from validators import validate_catalog
        with pytest.raises(ValueError, match="fuera de catálogo"):
            validate_catalog("DIVORCIADO", frozenset({"SOLTERO", "CASADO"}), "estado_civil")

    def test_validate_entorno_valido(self):
        from validators import validate_entorno
        result = validate_entorno("Urbano / Interiores")
        assert result == "Urbano / Interiores"

    def test_validate_entorno_invalido(self):
        from validators import validate_entorno
        with pytest.raises(ValueError, match="entorno"):
            validate_entorno("Invalido")

    def test_validate_control_tronco_valido(self):
        from validators import validate_control_tronco
        result = validate_control_tronco("Completo")
        assert result == "Completo"

    def test_validate_control_tronco_invalido(self):
        from validators import validate_control_tronco
        with pytest.raises(ValueError, match="control_tronco"):
            validate_control_tronco("Ninguno")

    def test_validate_control_cabeza_valido(self):
        from validators import validate_control_cabeza
        result = validate_control_cabeza("Independiente")
        assert result == "Independiente"

    def test_validate_control_cabeza_invalido(self):
        from validators import validate_control_cabeza
        with pytest.raises(ValueError, match="control_cabeza"):
            validate_control_cabeza("Mal")


class TestValidateFechaNacimiento:
    """Tests for validate_fecha_nacimiento."""

    def test_pasa_fecha_valida(self):
        from validators import validate_fecha_nacimiento
        result = validate_fecha_nacimiento("1990-05-15")
        assert result == "1990-05-15"

    def test_rechaza_formato_invalido(self):
        from validators import validate_fecha_nacimiento
        with pytest.raises(ValueError, match="fecha_nacimiento"):
            validate_fecha_nacimiento("15/05/1990")

    def test_rechaza_texto_arbitrario(self):
        from validators import validate_fecha_nacimiento
        with pytest.raises(ValueError, match="fecha_nacimiento"):
            validate_fecha_nacimiento("no-es-una-fecha")


class TestValidateNumericLimits:
    """Tests for numeric range validators."""

    def test_ingreso_mensual_en_rango(self):
        from validators import validate_ingreso_mensual
        result = validate_ingreso_mensual(5000000)
        assert result == 5000000

    def test_ingreso_mensual_fuera_de_rango(self):
        from validators import validate_ingreso_mensual
        with pytest.raises(ValueError, match="ingreso_mensual"):
            validate_ingreso_mensual(10000000)

    def test_num_hijos_en_rango(self):
        from validators import validate_num_hijos
        result = validate_num_hijos(5)
        assert result == 5

    def test_num_hijos_maximo_30(self):
        from validators import validate_num_hijos
        result = validate_num_hijos(30)
        assert result == 30

    def test_num_hijos_fuera_de_rango(self):
        from validators import validate_num_hijos
        with pytest.raises(ValueError, match="num_hijos"):
            validate_num_hijos(31)

    def test_edad_en_rango(self):
        from validators import validate_edad
        result = validate_edad(25)
        assert result == 25

    def test_edad_negativa(self):
        from validators import validate_edad
        with pytest.raises(ValueError, match="edad"):
            validate_edad(-1)

    def test_monto_otras_fuentes_en_rango(self):
        from validators import validate_monto_otras_fuentes
        result = validate_monto_otras_fuentes(500000.50)
        assert result == 500000.50

    def test_monto_otras_fuentes_fuera_de_rango(self):
        from validators import validate_monto_otras_fuentes
        with pytest.raises(ValueError, match="monto_otras_fuentes"):
            validate_monto_otras_fuentes(1000000)
