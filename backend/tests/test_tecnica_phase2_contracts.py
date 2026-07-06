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


def test_listar_beneficiarios_returns_indicators():
    from routers.tecnica import listar_beneficiarios_tecnica

    rows = [
        {
            "beneficiario_id": 10,
            "nombre": "Ana",
            "folio": "MX-LON-2026-001",
            "pais_nombre": "México",
            "region_nombre": "Guanajuato",
            "ciudad": "León",
            "sede": "León",
            "peso_kg": None,
            "altura_total_in": None,
            "unidad_captura": None,
            "foto_url": None,
            "solicitud_status": "completo",
            "total_count": 1,
        }
    ]
    db = _FakeDB([rows])
    out = listar_beneficiarios_tecnica(db=db, _usuario=_tec_user(), q="Ana", sede=None)
    assert out["total"] == 1
    assert out["items"][0]["pais_nombre"] == "México"
    assert out["items"][0]["region_nombre"] == "Guanajuato"


def test_detalle_consolidado_readonly_permissions():
    from routers.tecnica import obtener_detalle_tecnico

    # _build_snapshot queries, in order: beneficiario, tutores, estudio, solicitud.
    # The manufactura process (procesos_tecnicos) is no longer part of the snapshot.
    db = _FakeDB([
        {"id": 10, "nombre": "Ana", "folio": "F-1"},
        [{"numero_tutor": 1, "nombre": "Tutor"}],
        {"id": 100, "status": "completo"},
        {"id": 200, "status": "borrador"},
    ])
    out = obtener_detalle_tecnico(beneficiario_id=10, request=None, db=db, usuario=_tec_user())
    assert out["beneficiario"]["id"] == 10
    assert out["permisos"]["readonly_base"] is True
    assert "proceso_tecnico" not in out
    assert "participantes" not in out
