from routers.auth import CurrentUser


class _FakeDB:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []
        self._last = None

    def execute(self, sql: str, params: tuple = ()):  # noqa: ANN001
        self.calls.append((sql, params))
        self._last = self.rows.pop(0) if self.rows else None
        return self

    def fetchone(self):
        return self._last

    def fetchall(self):
        return self._last or []


def _tec_user() -> CurrentUser:
    return CurrentUser(usuario_id=7, nombre="Tec", email="tec@test.mx", rol="tecnico")


def _admin_user() -> CurrentUser:
    return CurrentUser(usuario_id=1, nombre="Admin", email="admin@test.mx", rol="admin")


def test_build_list_where_clause_filters_and_estado_validation():
    from fastapi import HTTPException
    from routers.tecnica import _build_list_where_clause

    where, params = _build_list_where_clause(
        q="ana",
        sede="León",
        estado="en_proceso",
        revision_pendiente=True,
    )
    assert "b.nombre ILIKE" in where
    assert "COALESCE(e.sede, '') = %s" in where
    assert "COALESCE(pt.estado, 'sin_iniciar') = %s" in where
    assert params[-2:] == ["en_proceso", True]

    try:
        _build_list_where_clause(q=None, sede=None, estado="estado_raro", revision_pendiente=None)
        assert False, "Debe validar estado"
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["type"] == "invalid_filter"


def test_listar_beneficiarios_returns_indicators():
    from routers.tecnica import listar_beneficiarios_tecnica

    rows = [
        {
            "beneficiario_id": 10,
            "nombre": "Ana",
            "folio": "MX-LON-2026-001",
            "sede": "León",
            "estado": "en_proceso",
            "revision_pendiente": False,
            "proceso_id": 33,
        }
    ]
    db = _FakeDB([rows])
    out = listar_beneficiarios_tecnica(db=db, _usuario=_tec_user(), q="Ana", sede=None, estado=None, revision_pendiente=None)
    assert out["total"] == 1
    assert out["items"][0]["estado"] == "en_proceso"


def test_detalle_consolidado_readonly_permissions():
    from routers.tecnica import obtener_detalle_tecnico

    db = _FakeDB([
        {"id": 10, "nombre": "Ana", "folio": "F-1"},
        [{"numero_tutor": 1, "nombre": "Tutor"}],
        {"id": 100, "status": "completo"},
        {"id": 200, "status": "borrador"},
        {"id": 300, "beneficiario_id": 10, "estado": "en_proceso"},
        [{"usuario_id": 7, "nombre": "Tec", "accion": "inicio"}],
    ])
    out = obtener_detalle_tecnico(beneficiario_id=10, db=db, usuario=_tec_user())
    assert out["beneficiario"]["id"] == 10
    assert out["permisos"]["readonly_base"] is True
    assert out["permisos"]["can_operate"] is True


def test_iniciar_creates_process_and_participant():
    from routers.tecnica import iniciar_proceso_tecnico

    db = _FakeDB([
        None,
        {"id": 77, "beneficiario_id": 10, "estado": "en_proceso"},
        None,
    ])
    out = iniciar_proceso_tecnico(beneficiario_id=10, db=db, usuario=_tec_user())
    assert out["proceso"]["id"] == 77
    assert out["event"] == "inicio"


def test_continuar_finalizar_solicitar_revision_update_state_and_participants():
    from routers.tecnica import continuar_proceso_tecnico, finalizar_proceso_tecnico, solicitar_revision_tecnica

    db_continue = _FakeDB([
        {"id": 11, "estado": "en_proceso", "beneficiario_id": 10},
        None,
        None,
    ])
    out_continue = continuar_proceso_tecnico(proceso_id=11, db=db_continue, usuario=_tec_user())
    assert out_continue["estado"] == "en_proceso"

    db_finalize = _FakeDB([
        {"id": 11, "estado": "en_proceso", "beneficiario_id": 10},
        None,
        None,
    ])
    out_finalize = finalizar_proceso_tecnico(proceso_id=11, db=db_finalize, usuario=_tec_user())
    assert out_finalize["estado"] == "finalizado"

    db_review = _FakeDB([
        {"id": 11, "estado": "en_proceso", "beneficiario_id": 10},
        None,
        None,
    ])
    out_review = solicitar_revision_tecnica(proceso_id=11, db=db_review, usuario=_tec_user())
    assert out_review["estado"] == "revision_pendiente"
    assert out_review["revision_pendiente"] is True


def test_pdf_base_and_admin_pending_list_contracts():
    from routers.tecnica import exportar_pdf_base, listar_revisiones_pendientes_admin

    db_pdf = _FakeDB([
        {"id": 15, "beneficiario_id": 10, "estado": "en_proceso"},
        {"id": 10, "nombre": "Ana", "folio": "F-1"},
        [],
        None,
        None,
        {"id": 15, "beneficiario_id": 10, "estado": "en_proceso"},
        [],
        None,
    ])
    pdf = exportar_pdf_base(proceso_id=15, db=db_pdf, _usuario=_tec_user())
    assert pdf["pdf"]["status"] == "base_ready"
    assert pdf["pdf"]["snapshot_included"] is True

    pending_rows = [{"proceso_id": 15, "beneficiario_id": 10, "estado": "revision_pendiente"}]
    db_admin = _FakeDB([pending_rows])
    pending = listar_revisiones_pendientes_admin(db=db_admin, _usuario=_admin_user())
    assert pending["total"] == 1
    assert pending["items"][0]["estado"] == "revision_pendiente"
