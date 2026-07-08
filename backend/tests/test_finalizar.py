"""
Tests for finalizar-registro endpoint — borradores-v2.
Strict TDD: RED → GREEN → TRIANGULATE → REFACTOR.
"""
import pytest


class TestValidateAllComplete:
    """Unit tests for _validate_all_complete() helper."""

    def test_all_complete_returns_empty_list(self):
        """TRIANGULATE: when all fields are complete, return empty list."""
        from routers.finalizar import _validate_all_complete

        estudio_row = {
            "id": 1,
            "fecha_estudio": "2026-06-01",
            "tuvo_silla_previa": 0,  # INTEGER in DB
            "como_obtuvo_silla": None,
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "elaboro_estudio": "Capturista Test",
            # Evidencia documental obligatoria (Issue #121)
            "credencial_url": "storage://documentos-estudio/1/credencial.jpg",
            "comprobante_domicilio_url": "storage://documentos-estudio/1/comprobante.jpg",
            "status": "borrador",
        }
        solicitud_row = {
            "id": 1,
            "altura_total_in": 72.0,
            "peso_kg": 45.0,
            "medida_cabeza_asiento": 10.0,
            "medida_hombro_asiento": 12.0,
            "medida_prof_asiento": 14.0,
            "medida_rodilla_talon": 16.0,
            "medida_ancho_cadera": 18.0,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            # Fotografía del paciente obligatoria (Issue #121)
            "foto_url": "storage://fotos-tecnica/1/foto.jpg",
            # Soporte de oxígeno respondido (Issue #162)
            "soporte_oxigeno": False,
            "status": "borrador",
        }
        beneficiario_row = {
            "id": 1,
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "curp_benef": "HEGG560427MVZRRL04",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        tutores_rows = [
            {
                "id": 1,
                "numero_tutor": 1,
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "tiene_imss": 1,
                "tiene_infonavit": 0,
                "sin_empleo": 0,
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "antiguedad_aplica": 1,
                "antiguedad_meses": 120,
                "otras_fuentes_aplica": 0,
                "otras_fuentes_ingreso": None,
                "monto_otras_fuentes": None,
            }
        ]

        missing = _validate_all_complete(
            estudio_row, solicitud_row, beneficiario_row, tutores_rows
        )

        assert missing == [], f"Expected empty list, got: {missing}"

    def test_returns_missing_when_solicitud_lacks_peso_kg(self):
        """TRIANGULATE: solicitud missing peso_kg is detected."""
        from routers.finalizar import _validate_all_complete

        estudio_row = {
            "id": 1,
            "fecha_estudio": "2026-06-01",
            "tuvo_silla_previa": 0,
            "como_obtuvo_silla": None,
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "elaboro_estudio": "Capturista Test",
            "status": "borrador",
        }
        solicitud_row = {
            "id": 1,
            "altura_total_in": 72.0,
            "peso_kg": None,  # MISSING
            "medida_cabeza_asiento": 10.0,
            "medida_hombro_asiento": 12.0,
            "medida_prof_asiento": 14.0,
            "medida_rodilla_talon": 16.0,
            "medida_ancho_cadera": 18.0,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            "status": "borrador",
        }
        beneficiario_row = {
            "id": 1,
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "curp_benef": "HEGG560427MVZRRL04",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        tutores_rows = [
            {
                "id": 1,
                "numero_tutor": 1,
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "tiene_imss": 1,
                "tiene_infonavit": 0,
                "sin_empleo": 0,
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "antiguedad_aplica": 1,
                "antiguedad_meses": 120,
                "otras_fuentes_aplica": 0,
                "otras_fuentes_ingreso": None,
                "monto_otras_fuentes": None,
            }
        ]

        missing = _validate_all_complete(
            estudio_row, solicitud_row, beneficiario_row, tutores_rows
        )

        peso_fields = [m for m in missing if m["field"] == "peso_kg"]
        assert len(peso_fields) == 1, f"Expected peso_kg in missing, got: {missing}"
        assert peso_fields[0]["form"] == "solicitud"
        # Issue #122: each missing field carries a user-facing label,
        # never the raw column name.
        assert peso_fields[0]["label"] == "Peso"

    def test_missing_fields_carry_friendly_labels(self):
        """Issue #122: every missing item exposes a label, never a raw column."""
        from routers.finalizar import _validate_all_complete
        from validators import FIELD_LABELS

        # Empty rows → maximal set of missing fields across all forms.
        missing = _validate_all_complete({}, {}, {}, [])

        assert missing, "Expected missing fields for empty rows"
        for item in missing:
            assert "label" in item, f"Missing label on {item}"
            assert item["label"], f"Empty label on {item}"
            # Label must differ from the raw column for catalogued fields.
            if item["field"] in FIELD_LABELS:
                assert item["label"] == FIELD_LABELS[item["field"]]

        # Spot-check the examples named in the issue.
        labels_by_field = {m["field"]: m["label"] for m in missing}
        assert labels_by_field.get("curp_benef") == "CURP"
        assert labels_by_field.get("estado_codigo") == "Estado"
        assert labels_by_field.get("telefonos") == "Teléfono"
        assert labels_by_field.get("fecha_nacimiento") == "Fecha de nacimiento"

    def test_returns_missing_when_beneficiario_lacks_nombres(self):
        """TRIANGULATE: beneficiario missing nombres is detected."""
        from routers.finalizar import _validate_all_complete

        estudio_row = {
            "id": 1,
            "fecha_estudio": "2026-06-01",
            "tuvo_silla_previa": 0,
            "como_obtuvo_silla": None,
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "elaboro_estudio": "Capturista Test",
            # Evidencia documental obligatoria (Issue #121)
            "credencial_url": "storage://documentos-estudio/1/credencial.jpg",
            "comprobante_domicilio_url": "storage://documentos-estudio/1/comprobante.jpg",
            "status": "borrador",
        }
        solicitud_row = {
            "id": 1,
            "altura_total_in": 72.0,
            "peso_kg": 45.0,
            "medida_cabeza_asiento": 10.0,
            "medida_hombro_asiento": 12.0,
            "medida_prof_asiento": 14.0,
            "medida_rodilla_talon": 16.0,
            "medida_ancho_cadera": 18.0,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            # Fotografía del paciente obligatoria (Issue #121)
            "foto_url": "storage://fotos-tecnica/1/foto.jpg",
            "status": "borrador",
        }
        beneficiario_row = {
            "id": 1,
            "nombres": "",  # MISSING — empty
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        tutores_rows = [
            {
                "id": 1,
                "numero_tutor": 1,
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "tiene_imss": 1,
                "tiene_infonavit": 0,
                "sin_empleo": 0,
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "antiguedad_aplica": 1,
                "antiguedad_meses": 120,
                "otras_fuentes_aplica": 0,
                "otras_fuentes_ingreso": None,
                "monto_otras_fuentes": None,
            }
        ]

        missing = _validate_all_complete(
            estudio_row, solicitud_row, beneficiario_row, tutores_rows
        )

        nombres_fields = [m for m in missing if m["field"] == "nombres"]
        assert len(nombres_fields) == 1, f"Expected nombres in missing, got: {missing}"
        assert nombres_fields[0]["form"] == "beneficiario"

    def test_returns_missing_when_tutor1_lacks_imss(self):
        """TRIANGULATE: tutor1 missing imss_estatus is detected."""
        from routers.finalizar import _validate_all_complete

        estudio_row = {
            "id": 1,
            "fecha_estudio": "2026-06-01",
            "tuvo_silla_previa": 0,
            "como_obtuvo_silla": None,
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "elaboro_estudio": "Capturista Test",
            # Evidencia documental obligatoria (Issue #121)
            "credencial_url": "storage://documentos-estudio/1/credencial.jpg",
            "comprobante_domicilio_url": "storage://documentos-estudio/1/comprobante.jpg",
            "status": "borrador",
        }
        solicitud_row = {
            "id": 1,
            "altura_total_in": 72.0,
            "peso_kg": 45.0,
            "medida_cabeza_asiento": 10.0,
            "medida_hombro_asiento": 12.0,
            "medida_prof_asiento": 14.0,
            "medida_rodilla_talon": 16.0,
            "medida_ancho_cadera": 18.0,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            # Fotografía del paciente obligatoria (Issue #121)
            "foto_url": "storage://fotos-tecnica/1/foto.jpg",
            # Soporte de oxígeno respondido (Issue #162)
            "soporte_oxigeno": False,
            "status": "borrador",
        }
        beneficiario_row = {
            "id": 1,
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "curp_benef": "HEGG560427MVZRRL04",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        tutores_rows = [
            {
                "id": 1,
                "numero_tutor": 1,
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "tiene_imss": None,  # MISSING
                "tiene_infonavit": 0,
                "sin_empleo": 0,
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "antiguedad_aplica": 1,
                "antiguedad_meses": 120,
                "otras_fuentes_aplica": 0,
                "otras_fuentes_ingreso": None,
                "monto_otras_fuentes": None,
            }
        ]

        missing = _validate_all_complete(
            estudio_row, solicitud_row, beneficiario_row, tutores_rows
        )

        imss_fields = [m for m in missing if m["field"] == "imss_estatus"]
        assert len(imss_fields) == 1, f"Expected imss_estatus in missing, got: {missing}"
        assert imss_fields[0]["form"] == "tutor1"

    def test_returns_missing_when_estudio_lacks_fecha_estudio(self):
        """RED phase — function doesn't exist yet, this WILL fail to import."""
        from routers.finalizar import _validate_all_complete

        estudio_row = {
            "id": 1,
            "fecha_estudio": None,  # MISSING
            "tuvo_silla_previa": False,
            "como_obtuvo_silla": None,
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "elaboro_estudio": "Capturista Test",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            "status": "borrador",
        }
        solicitud_row = {
            "id": 1,
            "altura_total_in": 72.0,
            "peso_kg": 45.0,
            "medida_cabeza_asiento": 10.0,
            "medida_hombro_asiento": 12.0,
            "medida_prof_asiento": 14.0,
            "medida_rodilla_talon": 16.0,
            "medida_ancho_cadera": 18.0,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            "status": "borrador",
        }
        beneficiario_row = {
            "id": 1,
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "curp_benef": "HEGG560427MVZRRL04",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        tutores_rows = [
            {
                "id": 1,
                "numero_tutor": 1,
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "tiene_imss": 1,
                "tiene_infonavit": 0,
                "sin_empleo": 0,
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "antiguedad_aplica": 1,
                "antiguedad_meses": 120,
                "otras_fuentes_aplica": 0,
                "otras_fuentes_ingreso": None,
                "monto_otras_fuentes": None,
            }
        ]

        missing = _validate_all_complete(
            estudio_row, solicitud_row, beneficiario_row, tutores_rows
        )

        # Assert the function returns a list of missing-field dicts
        assert isinstance(missing, list)
        assert len(missing) >= 1
        # fecha_estudio should be in the missing list
        fecha_fields = [m for m in missing if m["field"] == "fecha_estudio"]
        assert len(fecha_fields) == 1, f"Expected fecha_estudio in missing, got: {missing}"
        assert fecha_fields[0]["form"] == "estudio"

    # ── Issue #121: evidencia fotográfica y documental obligatoria ──────────
    @staticmethod
    def _complete_rows():
        """Return (estudio, solicitud, beneficiario, tutores) fully complete
        per VALIDATION_RULES.md, including the Issue #121 evidence refs."""
        estudio_row = {
            "id": 1,
            "fecha_estudio": "2026-06-01",
            "tuvo_silla_previa": 0,
            "como_obtuvo_silla": None,
            "sede": "León sede Forum",
            "ciudad_registro": "LEON, GTO",
            "elaboro_estudio": "Capturista Test",
            "credencial_url": "storage://documentos-estudio/1/credencial.jpg",
            "comprobante_domicilio_url": "storage://documentos-estudio/1/comprobante.jpg",
            "status": "borrador",
        }
        solicitud_row = {
            "id": 1,
            "altura_total_in": 72.0,
            "peso_kg": 45.0,
            "medida_cabeza_asiento": 10.0,
            "medida_hombro_asiento": 12.0,
            "medida_prof_asiento": 14.0,
            "medida_rodilla_talon": 16.0,
            "medida_ancho_cadera": 18.0,
            "entorno": "Urbano / Interiores",
            "control_tronco": "Completo",
            "control_cabeza": "Independiente",
            "control_de_piernas": "Parcial",
            "entidad_solicitante": "Rotary Club León",
            "prioridad": "Alta",
            "foto_url": "storage://fotos-tecnica/1/foto.jpg",
            "soporte_oxigeno": False,
            "status": "borrador",
        }
        beneficiario_row = {
            "id": 1,
            "nombres": "BENEFICIARIO",
            "apellido_paterno": "TEST",
            "apellido_materno": "MUESTRA",
            "curp_benef": "HEGG560427MVZRRL04",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "sexo": "M",
            "telefonos": "4621234567",
        }
        tutores_rows = [
            {
                "id": 1,
                "numero_tutor": 1,
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "tiene_imss": 1,
                "tiene_infonavit": 0,
                "sin_empleo": 0,
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "antiguedad_aplica": 1,
                "antiguedad_meses": 120,
                "otras_fuentes_aplica": 0,
                "otras_fuentes_ingreso": None,
                "monto_otras_fuentes": None,
            }
        ]
        return estudio_row, solicitud_row, beneficiario_row, tutores_rows

    def test_returns_missing_when_soporte_oxigeno_none(self):
        """Issue #162 + migración 0029: soporte_oxigeno NULL (sin responder)
        bloquea la finalización. Antes la columna era NOT NULL DEFAULT FALSE y
        el CREATE forzaba bool(None)→FALSE, así que este chequeo nunca disparaba."""
        from routers.finalizar import _validate_all_complete

        estudio, solicitud, ben, tutores = self._complete_rows()
        solicitud["soporte_oxigeno"] = None  # radio sin responder

        missing = _validate_all_complete(estudio, solicitud, ben, tutores)

        hits = [m for m in missing if m["field"] == "soporte_oxigeno"]
        assert len(hits) == 1, f"Expected soporte_oxigeno in missing, got: {missing}"
        assert hits[0]["form"] == "solicitud"

    def test_soporte_oxigeno_false_explicito_no_bloquea(self):
        """Un "No" explícito (FALSE) es respuesta válida y no bloquea finalizar."""
        from routers.finalizar import _validate_all_complete

        estudio, solicitud, ben, tutores = self._complete_rows()
        solicitud["soporte_oxigeno"] = False

        missing = _validate_all_complete(estudio, solicitud, ben, tutores)

        hits = [m for m in missing if m["field"] == "soporte_oxigeno"]
        assert hits == [], f"FALSE explícito no debe reportarse: {missing}"

    def test_returns_missing_when_credencial_absent(self):
        """Issue #121: missing credencial evidence blocks finalization."""
        from routers.finalizar import _validate_all_complete

        estudio, solicitud, ben, tutores = self._complete_rows()
        estudio["credencial_url"] = None  # MISSING

        missing = _validate_all_complete(estudio, solicitud, ben, tutores)

        hits = [m for m in missing if m["field"] == "credencial_url"]
        assert len(hits) == 1, f"Expected credencial_url in missing, got: {missing}"
        assert hits[0]["form"] == "estudio"
        assert hits[0]["label"] == "Credencial"

    def test_returns_missing_when_comprobante_domicilio_absent(self):
        """Issue #121: missing comprobante de domicilio blocks finalization."""
        from routers.finalizar import _validate_all_complete

        estudio, solicitud, ben, tutores = self._complete_rows()
        estudio["comprobante_domicilio_url"] = None  # MISSING

        missing = _validate_all_complete(estudio, solicitud, ben, tutores)

        hits = [m for m in missing if m["field"] == "comprobante_domicilio_url"]
        assert len(hits) == 1, f"Expected comprobante_domicilio_url, got: {missing}"
        assert hits[0]["form"] == "estudio"
        assert hits[0]["label"] == "Comprobante de domicilio"

    def test_returns_missing_when_foto_url_absent(self):
        """Issue #121: missing patient photo blocks finalization."""
        from routers.finalizar import _validate_all_complete

        estudio, solicitud, ben, tutores = self._complete_rows()
        solicitud["foto_url"] = None  # MISSING

        missing = _validate_all_complete(estudio, solicitud, ben, tutores)

        hits = [m for m in missing if m["field"] == "foto_url"]
        assert len(hits) == 1, f"Expected foto_url in missing, got: {missing}"
        assert hits[0]["form"] == "solicitud"
        assert hits[0]["label"] == "Fotografía del paciente"

    def test_estudio_clinico_is_not_required(self):
        """Issue #121: Estudio Clínico stays optional — never blocks finalize."""
        from routers.finalizar import _validate_all_complete

        # Fully complete rows WITHOUT any estudio_clinico reference.
        estudio, solicitud, ben, tutores = self._complete_rows()

        missing = _validate_all_complete(estudio, solicitud, ben, tutores)

        assert missing == [], f"Expected no missing fields, got: {missing}"
        assert not any("clinico" in m["field"] for m in missing)


# ---------------------------------------------------------------------------
# Integration tests for POST /api/finalizar-registro
# ---------------------------------------------------------------------------

class TestFinalizarRegistroEndpoint:
    """Integration tests that exercise the full endpoint."""

    @staticmethod
    def _seed_borrador_estudio(db_conn, region_lon, capturista_user) -> dict:
        """Create a beneficiario + estudio as borrador. Returns both IDs."""
        import psycopg2.extras
        with db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Beneficiario
            cur.execute(
                """
                INSERT INTO beneficiarios
                    (nombre, nombres, apellido_paterno, apellido_materno, curp_benef,
                     fecha_nacimiento, diagnostico, calle, colonia, ciudad,
                     estado_codigo, estado_nombre, sexo, telefonos, folio, region_id, sede)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    "BENEFICIARIO TEST MUESTRA",
                    "BENEFICIARIO", "TEST", "MUESTRA", "HEGG560427MVZRRL04",
                    "2000-01-15", "Parálisis cerebral",
                    "Calle Test 123", "Centro", "León",
                    "11", "GUANAJUATO", "M", "4621234567",
                    "MX-LON-2026-001", region_lon["id"], "León sede Forum",
                ),
            )
            ben_id = cur.fetchone()["id"]

            # Tutor 1
            cur.execute(
                """
                INSERT INTO tutores
                    (beneficiario_id, numero_tutor, nombre, edad, nivel_estudios,
                     estado_civil, num_hijos, vivienda, fuente_empleo,
                     ingreso_mensual, tiene_imss, tiene_infonavit,
                     antiguedad_meses, antiguedad_aplica, sin_empleo,
                     otras_fuentes_aplica, otras_fuentes_ingreso, monto_otras_fuentes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ben_id, 1, "Tutor Test Muestra",
                    45, "LICENCIATURA", "CASADO", 2, "PROPIA",
                    "Empleado", 12000,
                    1, 0, 120, 1, 0, 0, None, None,
                ),
            )
            cur.fetchone()["id"]

            # Estudio as borrador
            cur.execute(
                """
                INSERT INTO estudios_socioeconomicos
                    (beneficiario_id, usuario_id, tuvo_silla_previa,
                     como_obtuvo_silla, elaboro_estudio, fecha_estudio,
                     sede, ciudad_registro, credencial_url,
                     comprobante_domicilio_url, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ben_id, capturista_user["id"],
                    0, None, "Capturista Test", "2026-06-01",
                    "León sede Forum", "LEON, GTO",
                    "storage://documentos-estudio/1/credencial.jpg",
                    "storage://documentos-estudio/1/comprobante.jpg",
                    "borrador",
                ),
            )
            estudio_id = cur.fetchone()["id"]

            # Solicitud as borrador
            cur.execute(
                """
                INSERT INTO solicitudes_tecnicas
                    (beneficiario_id, usuario_id, entorno, control_tronco,
                     control_cabeza, control_de_piernas, altura_total_in,
                     peso_kg, medida_cabeza_asiento, medida_hombro_asiento,
                     medida_prof_asiento, medida_rodilla_talon,
                     medida_ancho_cadera, entidad_solicitante, prioridad,
                     foto_url, soporte_oxigeno, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ben_id, capturista_user["id"],
                    "Urbano / Interiores", "Completo", "Independiente", "Parcial",
                    72.0, 45.0, 10.0, 12.0, 14.0, 16.0, 18.0,
                    "Rotary Club León", "Alta",
                    # Migración 0029: sin DEFAULT FALSE, el seeder debe responder
                    # explícitamente para que el registro sea finalizable.
                    "storage://fotos-tecnica/1/foto.jpg", False, "borrador",
                ),
            )
            solicitud_id = cur.fetchone()["id"]
        db_conn.commit()
        return {"estudio_id": estudio_id, "solicitud_id": solicitud_id}

    def test_happy_path_returns_200_and_completo(self, client, capturista_headers, _test_db_conn, region_lon, capturista_user):
        """RED: happy path — endpoint doesn't exist yet."""
        ids = self._seed_borrador_estudio(_test_db_conn, region_lon, capturista_user)

        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=capturista_headers,
        )

        # When the endpoint exists: assert res.status_code == 200
        # For now, this will fail with 405 or 404
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    def test_missing_fields_returns_422(self, client, capturista_headers, _test_db_conn, region_lon, capturista_user):
        """RED: incomplete fields → 422 with missing[] detail."""
        import psycopg2.extras
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Create beneficiario WITHOUT telefonos (required field)
            cur.execute(
                """
                INSERT INTO beneficiarios
                    (nombre, nombres, apellido_paterno, apellido_materno,
                     fecha_nacimiento, diagnostico, calle, colonia, ciudad,
                     estado_codigo, estado_nombre, sexo, telefonos, folio, region_id, sede)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                ("B INC TEST M", "B INC", "TEST", "M", "2000-01-15",
                 "Diagnóstico", "Calle", "Colonia", "Ciudad", "11", "GUANAJUATO",
                 "M", "", "MX-LON-2026-002", region_lon["id"], "Sede"),  # telefonos empty
            )
            ben_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO tutores
                    (beneficiario_id, numero_tutor, nombre, edad, nivel_estudios,
                     estado_civil, num_hijos, vivienda, tiene_imss, tiene_infonavit,
                     sin_empleo, fuente_empleo, ingreso_mensual)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ben_id, 1, "Tutor Inc", 40, "LICENCIATURA", "CASADO", 1, "PROPIA",
                 1, 0, 0, "Empleado", 10000),
            )
            cur.fetchone()

            # Estudio — complete
            cur.execute(
                """
                INSERT INTO estudios_socioeconomicos
                    (beneficiario_id, usuario_id, tuvo_silla_previa,
                     elaboro_estudio, fecha_estudio, sede, ciudad_registro, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ben_id, capturista_user["id"], 0, "Capturista", "2026-06-01",
                 "Sede", "CIUDAD", "borrador"),
            )
            estudio_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO solicitudes_tecnicas
                    (beneficiario_id, usuario_id, entorno, control_tronco,
                     control_cabeza, control_de_piernas, altura_total_in,
                     peso_kg, medida_cabeza_asiento, medida_hombro_asiento,
                     medida_prof_asiento, medida_rodilla_talon,
                     medida_ancho_cadera, entidad_solicitante, prioridad, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ben_id, capturista_user["id"],
                 "Urbano / Interiores", "Completo", "Independiente", "Parcial",
                 72.0, 45.0, 10.0, 12.0, 14.0, 16.0, 18.0,
                 "Rotary Club León", "Alta", "borrador"),
            )
            solicitud_id = cur.fetchone()["id"]
        _test_db_conn.commit()

        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": estudio_id, "solicitud_id": solicitud_id},
            headers=capturista_headers,
        )

        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
        data = res.json()
        assert "detail" in data
        assert "missing" in data["detail"]

    def test_tecnico_role_returns_403(self, client, tecnico_headers, _test_db_conn, region_lon, capturista_user):
        """RED: tecnico role → 403 forbidden."""
        ids = TestFinalizarRegistroEndpoint._seed_borrador_estudio(
            _test_db_conn, region_lon, capturista_user
        )

        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=tecnico_headers,
        )

        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    def test_non_owner_capturista_returns_403(self, client, admin_headers, _test_db_conn, region_lon, capturista_user):
        """RED: different capturista (admin has admin role, which should pass owner check)."""
        ids = TestFinalizarRegistroEndpoint._seed_borrador_estudio(
            _test_db_conn, region_lon, capturista_user
        )

        # Create a second capturista
        import psycopg2.extras
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO usuarios (nombre, email, password_hash, rol)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                ("Capturista 2", "cap2@test.mx", pwd_ctx.hash("cap2pass123"), "capturista"),
            )
        _test_db_conn.commit()

        # Login as capturista 2
        login_res = client.post(
            "/api/auth/login",
            json={"email": "cap2@test.mx", "password": "cap2pass123"},
        )
        assert login_res.status_code == 200
        cap2_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=cap2_headers,
        )

        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    def test_org_leader_can_finalize_linked_registration(
        self, client, admin_headers, organizacion_user,
        capturista_user, capturista_headers, _test_db_conn, region_lon,
    ):
        """Regression #109: an org leader authorized for the estudio must also
        pass the solicitud ownership check when finalizing. Previously the
        solicitud check called assert_resource_owner without db/estudio_id, so
        the leader bypass never ran and the leader got 403 on the linked
        technical request."""
        # Estudio + solicitud owned by the organization account.
        ids = self._seed_borrador_estudio(_test_db_conn, region_lon, organizacion_user)

        # Link the org to the capturing account so org-owned records match the
        # leader-bypass query (organizaciones.usuario_id == row.usuario_id).
        org_response = client.post(
            "/api/organizaciones",
            headers=admin_headers,
            json={"nombre": "Rotary Finalizar Test", "usuario_id": organizacion_user["id"]},
        )
        assert org_response.status_code == 201, org_response.text
        org_id = org_response.json()["id"]

        # capturista_user is the leader of that organization (distinct from owner).
        leader_assign = client.post(
            f"/api/organizaciones/{org_id}/lider",
            headers=admin_headers,
            json={"lider_usuario_id": capturista_user["id"]},
        )
        assert leader_assign.status_code == 200, leader_assign.text

        # Leader finalizes the full registration (estudio + linked solicitud) → 200
        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=capturista_headers,
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        assert res.json()["status"] == "completo"

    def test_non_leader_non_owner_returns_403_on_finalize(
        self, client, organizacion_user, _test_db_conn, region_lon,
    ):
        """Boundary for #109: a user who is neither owner, nor org leader, nor
        admin still gets 403 — the leader bypass must not over-grant."""
        ids = self._seed_borrador_estudio(_test_db_conn, region_lon, organizacion_user)

        # Unrelated capturista: not the owner, not a leader, not admin.
        import psycopg2.extras
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        with _test_db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO usuarios (nombre, email, password_hash, rol)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                ("Outsider 109", "outsider109@test.mx",
                 pwd_ctx.hash("outsider109pass"), "capturista"),
            )
        _test_db_conn.commit()

        login_res = client.post(
            "/api/auth/login",
            json={"email": "outsider109@test.mx", "password": "outsider109pass"},
        )
        assert login_res.status_code == 200
        outsider_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=outsider_headers,
        )
        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    def test_already_completed_returns_200_idempotent(self, client, capturista_headers, _test_db_conn, region_lon, capturista_user):
        """TRIANGULATE: second call returns already_completed=true."""
        ids = self._seed_borrador_estudio(_test_db_conn, region_lon, capturista_user)

        # First call — should finalize
        res1 = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=capturista_headers,
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "completo"
        assert data1["already_completed"] is False
        assert data1["finalizado_at"] is not None

        # Second call — should be idempotent
        res2 = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": ids["estudio_id"], "solicitud_id": ids["solicitud_id"]},
            headers=capturista_headers,
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "completo"
        assert data2["already_completed"] is True

    def test_invalid_estudio_id_returns_422(self, client, capturista_headers):
        """TRIANGULATE: negative or zero estudio_id is rejected."""
        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": 0, "solicitud_id": 1},
            headers=capturista_headers,
        )
        assert res.status_code == 422

    def test_nonexistent_estudio_returns_404(self, client, capturista_headers):
        """TRIANGULATE: non-existent estudio_id returns 404."""
        res = client.post(
            "/api/finalizar-registro",
            json={"estudio_id": 999999, "solicitud_id": 1},
            headers=capturista_headers,
        )
        assert res.status_code == 404
