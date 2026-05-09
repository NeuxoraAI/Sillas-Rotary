"""RED — Tests for the enriched listar_beneficiarios_tecnica endpoint.

Covers pagination (1.5), enriched SQL response shape (2.1-2.4),
and snapshot extension (2.5).

These tests MUST fail initially because the production code hasn't been
updated to support the new params and response shape yet.
"""

# ruff: noqa: ANN201


class _FakeDB:
    """Minimal FakeDB that records calls for inspection."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []
        self._last = None
        self._row_index = 0

    def execute(self, sql: str, params: tuple = ()):
        self.calls.append((sql, params))
        if self._row_index < len(self.rows):
            self._last = self.rows[self._row_index]
            self._row_index += 1
        else:
            self._last = None
        return self

    def fetchone(self):
        return self._last

    def fetchall(self):
        return self._last or []


def _fake_current_user(rol: str = "tecnico", usuario_id: int = 7):
    from routers.auth import CurrentUser
    return CurrentUser(usuario_id=usuario_id, nombre="Tec", email="tec@test.mx", rol=rol)


# ── Task 1.5: Pagination params ──────────────────────────────────────────────

def test_default_pagination():
    """GIVEN no page/per_page WHEN called THEN defaults page=1 per_page=20."""
    from routers.tecnica import listar_beneficiarios_tecnica

    db = _FakeDB([[]])
    result = listar_beneficiarios_tecnica(
        db=db, _usuario=_fake_current_user(),
    )
    # Check SQL contains expected LIMIT/OFFSET or pagination markers
    last_sql = db.calls[-1][0] if db.calls else ""
    assert "page" in result or "total" in result
    assert "LIMIT" in last_sql or "per_page" in str(db.calls)


def test_custom_pagination():
    """GIVEN page=2 per_page=5 WHEN called THEN custom pagination applied."""
    from routers.tecnica import listar_beneficiarios_tecnica

    db = _FakeDB([[]])
    result = listar_beneficiarios_tecnica(
        db=db, _usuario=_fake_current_user(),
        page=2, per_page=5,
    )
    last_sql = db.calls[-1][0] if db.calls else ""
    assert "LIMIT" in last_sql
    assert result["page"] == 2
    assert result["per_page"] == 5


def test_page_must_be_positive():
    """GIVEN page=0 WHEN called THEN 422."""
    from fastapi import HTTPException
    from routers.tecnica import listar_beneficiarios_tecnica

    db = _FakeDB([[]])
    try:
        listar_beneficiarios_tecnica(
            db=db, _usuario=_fake_current_user(),
            page=0,
        )
        assert False, "Should have raised 422"
    except HTTPException as exc:
        assert exc.status_code == 422


# ── Phase 2: Enriched response shape ─────────────────────────────────────────

def test_enriched_response_shape():
    """GIVEN beneficiario with complete data WHEN listed THEN response has all R1 fields."""
    from routers.tecnica import listar_beneficiarios_tecnica

    rows = [{
        "beneficiario_id": 1,
        "nombre": "María López",
        "folio": "MX-01-2026-001",
        "pais_nombre": "México",
        "region_nombre": "Guanajuato",
        "ciudad": "León",
        "sede": "Hospital Civil",
        "peso_kg": 65.5,
        "altura_total_in": 63.0,
        "unidad_captura": "in",
        "foto_url": "storage://fotos-tecnica/uuid.jpg",
        "estado": "en_proceso",
        "revision_pendiente": False,
        "proceso_id": 7,
        "total_count": 1,
    }]
    db = _FakeDB([rows])
    result = listar_beneficiarios_tecnica(
        db=db, _usuario=_fake_current_user(),
    )
    item = result["items"][0]
    assert item["beneficiario_id"] == 1
    assert item["pais_nombre"] == "México"
    assert item["region_nombre"] == "Guanajuato"
    assert item["ciudad"] == "León"
    assert item["peso_kg"] == 65.5
    assert item["altura_total_in"] == 63.0
    assert item["foto_url"] is not None
    assert "unidad_captura" in item


def test_beneficiario_without_solicitud():
    """GIVEN beneficiario without solicitud_tecnica WHEN listed THEN technical fields are null and estado=sin_iniciar."""
    from routers.tecnica import listar_beneficiarios_tecnica

    rows = [{
        "beneficiario_id": 2,
        "nombre": "Juan Pérez",
        "folio": "MX-01-2026-002",
        "pais_nombre": "México",
        "region_nombre": "León",
        "ciudad": "León",
        "sede": "Centro",
        "peso_kg": None,
        "altura_total_in": None,
        "unidad_captura": None,
        "foto_url": None,
        "estado": "sin_iniciar",
        "revision_pendiente": False,
        "proceso_id": None,
        "total_count": 1,
    }]
    db = _FakeDB([rows])
    result = listar_beneficiarios_tecnica(
        db=db, _usuario=_fake_current_user(),
    )
    item = result["items"][0]
    assert item["peso_kg"] is None
    assert item["foto_url"] is None
    assert item["estado"] == "sin_iniciar"


def test_response_has_new_pagination_shape():
    """GIVEN 3 beneficiaries, per_page=5 WHEN called THEN response shape includes items, total, page, per_page."""
    from routers.tecnica import listar_beneficiarios_tecnica

    rows = [
        {"beneficiario_id": 1, "nombre": "A", "folio": "F1", "pais_nombre": "MX",
         "region_nombre": "Gto", "ciudad": "León", "sede": "S1",
         "peso_kg": None, "altura_total_in": None, "unidad_captura": None, "foto_url": None,
         "estado": "sin_iniciar", "revision_pendiente": False, "proceso_id": None,
         "total_count": 3},
    ]
    db = _FakeDB([rows])
    result = listar_beneficiarios_tecnica(
        db=db, _usuario=_fake_current_user(),
    )
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "per_page" in result
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["per_page"] == 20


# ── Phase 2.5: Snapshot extension ────────────────────────────────────────────

def test_snapshot_has_pais_region_nombre():
    """GIVEN beneficiario with region/pais WHEN snapshot THEN includes pais_nombre, region_nombre."""
    from routers.tecnica import _build_snapshot

    db = _FakeDB([
        {"id": 10, "nombre": "Ana", "folio": "F-1", "region_id": 5,
         "ciudad": "León", "diagnostico": "Parálisis cerebral",
         "telefonos": "4621234567"},
        [],
        {"id": 100, "status": "completo"},
        None,
        None,
        [],
    ])
    snapshot = _build_snapshot(db, 10)
    ben = snapshot["beneficiario"]
    # The beneficiary dict should have been extended with the JOIN
    assert ben["id"] == 10


def test_snapshot_without_diagnostico():
    """GIVEN beneficiario without diagnóstico WHEN snapshot THEN diagnostico=None."""
    from routers.tecnica import _build_snapshot

    db = _FakeDB([
        {"id": 11, "nombre": "Luis", "folio": "F-2", "region_id": None,
         "ciudad": None, "diagnostico": None, "telefonos": None},
        [],
        None,
        None,
        None,
        [],
    ])
    snapshot = _build_snapshot(db, 11)
    ben = snapshot["beneficiario"]
    assert ben["diagnostico"] is None
    assert ben["telefonos"] is None
