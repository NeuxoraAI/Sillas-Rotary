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
                     sede, ciudad_registro, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ben_id, capturista_user["id"],
                    0, None, "Capturista Test", "2026-06-01",
                    "León sede Forum", "LEON, GTO", "borrador",
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
                     medida_ancho_cadera, entidad_solicitante, prioridad, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ben_id, capturista_user["id"],
                    "Urbano / Interiores", "Completo", "Independiente", "Parcial",
                    72.0, 45.0, 10.0, 12.0, 14.0, 16.0, 18.0,
                    "Rotary Club León", "Alta", "borrador",
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
