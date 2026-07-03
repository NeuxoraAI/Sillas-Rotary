"""Audit trail tests for sensitive backend operations."""

from audit import sanitize_audit_metadata


def _create_beneficiario_with_solicitud(client, capturista_headers, capturista_user, region_lon, _test_db_conn) -> dict:
    payload = {
        "region_id": region_lon["id"],
        "sede": "León sede Forum",
        "ciudad_registro": "LEON, GTO",
        "beneficiario": {
            "nombres": "AUDITORIA",
            "apellido_paterno": "EVENTO",
            "apellido_materno": "TEST",
            "fecha_nacimiento": "2000-01-15",
            "diagnostico": "Parálisis cerebral",
            "calle": "Calle Test 123",
            "num_ext": "12A",
            "colonia": "Centro",
            "ciudad": "León",
            "estado_codigo": "11",
            "estado_nombre": "GUANAJUATO",
            "sexo": "M",
            "telefonos": "4621234567",
        },
        "tutores": [
            {
                "numero_tutor": 1,
                "nombres": "TUTOR",
                "apellido_paterno": "AUDIT",
                "apellido_materno": "TEST",
                "edad": 45,
                "nivel_estudios": "LICENCIATURA",
                "estado_civil": "CASADO",
                "num_hijos": 2,
                "vivienda": "PROPIA",
                "fuente_empleo": "Empleado",
                "ingreso_mensual": 12000,
                "imss_estatus": "SI",
                "infonavit_estatus": "NO",
            }
        ],
        "estudio": {
            "tuvo_silla_previa": False,
            "elaboro_estudio": "Capturista Test",
            "fecha_estudio": "2026-04-18",
            "status": "completo",
        },
    }
    res = client.post("/api/estudios", json=payload, headers=capturista_headers)
    assert res.status_code == 201, res.text
    data = res.json()

    with _test_db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO solicitudes_tecnicas (beneficiario_id, usuario_id, status, foto_path, foto_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["beneficiario_id"],
                capturista_user["id"],
                "borrador",
                "audit-test.jpg",
                "storage://fotos-tecnica/audit-test.jpg",
            ),
        )
        solicitud_id = cur.fetchone()[0]
    _test_db_conn.commit()
    return {"beneficiario_id": data["beneficiario_id"], "solicitud_id": solicitud_id}


def _audit_events(_test_db_conn, accion: str) -> list[dict]:
    with _test_db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT actor_usuario_id, actor_rol, accion, recurso_tipo, recurso_id, metadata::text
            FROM auditoria_eventos
            WHERE accion = %s
            ORDER BY id
            """,
            (accion,),
        )
        return [
            {
                "actor_usuario_id": row[0],
                "actor_rol": row[1],
                "accion": row[2],
                "recurso_tipo": row[3],
                "recurso_id": row[4],
                "metadata": row[5],
            }
            for row in cur.fetchall()
        ]


def test_sanitize_audit_metadata_redacts_urls_and_tokens() -> None:
    metadata = sanitize_audit_metadata(
        {
            "signed_url": "https://example.supabase.co/signed/path?token=secret",
            "authorization": "Bearer abc.def.ghi",
            "nested": {"safe": "ok", "token_hash": "secret"},
        }
    )

    assert metadata["signed_url"] == "[REDACTED]"
    assert metadata["authorization"] == "[REDACTED]"
    assert metadata["nested"]["safe"] == "ok"
    assert metadata["nested"]["token_hash"] == "[REDACTED]"


def test_admin_export_records_audit_event(client, admin_headers, capturista_headers, capturista_user, region_lon, _test_db_conn) -> None:
    _create_beneficiario_with_solicitud(client, capturista_headers, capturista_user, region_lon, _test_db_conn)

    res = client.get("/api/admin/beneficiarios/export", headers=admin_headers)

    assert res.status_code == 200
    events = _audit_events(_test_db_conn, "export.generate")
    assert len(events) == 1
    assert events[0]["recurso_tipo"] == "admin_beneficiarios"
    assert "row_count" in events[0]["metadata"]


def test_admin_patch_records_field_names_without_values(client, admin_headers, capturista_headers, capturista_user, region_lon, _test_db_conn) -> None:
    created = _create_beneficiario_with_solicitud(client, capturista_headers, capturista_user, region_lon, _test_db_conn)

    res = client.patch(
        f"/api/admin/beneficiarios/{created['beneficiario_id']}",
        json={"nombres": "VALOR SENSIBLE"},
        headers=admin_headers,
    )

    assert res.status_code == 200
    events = _audit_events(_test_db_conn, "admin.patch")
    assert len(events) == 1
    assert events[0]["recurso_tipo"] == "beneficiario"
    assert "nombres" in events[0]["metadata"]
    assert "VALOR SENSIBLE" not in events[0]["metadata"]


def test_signed_photo_url_records_audit_event_without_url(client, admin_headers, capturista_headers, capturista_user, region_lon, _test_db_conn, monkeypatch) -> None:
    created = _create_beneficiario_with_solicitud(client, capturista_headers, capturista_user, region_lon, _test_db_conn)

    class _FakeStorage:
        def create_signed_url(self, path, ttl):
            return {"signedURL": f"https://example.supabase.co/{path}?token=SUPERSECRET"}

    from routers import tecnica

    monkeypatch.setattr(tecnica, "_storage", lambda bucket=tecnica._BUCKET: _FakeStorage())

    res = client.get(f"/api/solicitudes/{created['solicitud_id']}/foto", headers=admin_headers)

    assert res.status_code == 200
    assert "SUPERSECRET" in res.json()["url"]
    events = _audit_events(_test_db_conn, "signed_url.generate")
    assert len(events) == 1
    assert events[0]["recurso_tipo"] == "solicitud_foto"
    assert events[0]["recurso_id"] == str(created["solicitud_id"])
    assert "SUPERSECRET" not in events[0]["metadata"]
    assert "https://example.supabase.co" not in events[0]["metadata"]
