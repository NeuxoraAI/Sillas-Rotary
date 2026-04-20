import pytest
from fastapi import HTTPException

from routers.auth import CurrentUser
from routers import tecnica


class _FakeDB:
    def __init__(self, row: dict | None):
        self._row = row
        self.last_sql = ""
        self.last_params = ()
        self.updates: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple = ()):
        self.last_sql = sql
        self.last_params = params
        if sql.strip().upper().startswith("UPDATE"):
            self.updates.append((sql, params))
        return self

    def fetchone(self):
        if "SELECT id, usuario_id, foto_path, foto_url" in self.last_sql:
            return self._row
        return None


class _FakeStorage:
    def __init__(self):
        self.calls: list[tuple[str, int]] = []

    def create_signed_url(self, path: str, expires_in: int):
        self.calls.append((path, expires_in))
        return {"signedURL": f"https://storage.local/sign/{path}?token=abc"}


def _user(*, usuario_id: int, rol: str) -> CurrentUser:
    return CurrentUser(
        usuario_id=usuario_id,
        nombre="Test",
        email="test@example.com",
        rol=rol,
    )


def test_extract_foto_path_from_legacy_public_url() -> None:
    legacy = "https://abc.supabase.co/storage/v1/object/public/fotos-tecnica/path/sub/foto.png"

    result = tecnica.extract_foto_path(legacy)

    assert result == "path/sub/foto.png"


def test_extract_foto_path_from_storage_scheme_url() -> None:
    legacy = "storage://fotos-tecnica/path/sub/foto.png"

    result = tecnica.extract_foto_path(legacy)

    assert result == "path/sub/foto.png"


def test_obtener_foto_rechaza_capturista_aunque_sea_owner(monkeypatch) -> None:
    db = _FakeDB(
        {
            "id": 12,
            "usuario_id": 77,
            "foto_path": "owner/foto.png",
            "foto_url": None,
        }
    )
    monkeypatch.setattr(tecnica, "_storage", lambda: _FakeStorage())

    with pytest.raises(HTTPException) as exc:
        tecnica.obtener_foto_solicitud(
            id=12,
            db=db,
            usuario=_user(usuario_id=77, rol="capturista"),
        )

    assert exc.value.status_code == 403


def test_obtener_foto_backfill_desde_foto_url_legacy(monkeypatch) -> None:
    db = _FakeDB(
        {
            "id": 99,
            "usuario_id": 9,
            "foto_path": None,
            "foto_url": "https://abc.supabase.co/storage/v1/object/public/fotos-tecnica/legacy/a.png",
        }
    )
    storage = _FakeStorage()
    monkeypatch.setattr(tecnica, "_storage", lambda: storage)

    response = tecnica.obtener_foto_solicitud(
        id=99,
        db=db,
        usuario=_user(usuario_id=9, rol="tecnico"),
    )

    assert response["foto_path"] == "legacy/a.png"
    assert response["expires_in"] == 60
    assert response["url"] == "https://storage.local/sign/legacy/a.png?token=abc"
    assert storage.calls == [("legacy/a.png", 60)]
    assert len(db.updates) == 1
    assert db.updates[0][1][0] == "legacy/a.png"
    assert db.updates[0][1][2] == 99
