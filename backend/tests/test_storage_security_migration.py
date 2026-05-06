from pathlib import Path

import init_db


def test_incremental_migration_adds_foto_path_and_backfill() -> None:
    migration_file = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0002_add_foto_path_to_solicitudes_tecnicas.sql"
    )
    content = migration_file.read_text(encoding="utf-8").lower()

    assert "add column if not exists foto_path" in content
    assert "update solicitudes_tecnicas" in content
    assert "foto_path is null" in content


def test_incremental_migration_adds_document_refs_to_estudios() -> None:
    migration_file = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0004_add_documento_refs_to_estudios_socioeconomicos.sql"
    )
    content = migration_file.read_text(encoding="utf-8").lower()

    assert "alter table public.estudios_socioeconomicos" in content
    assert "credencial_path" in content
    assert "comprobante_domicilio_path" in content


def test_init_storage_hardens_existing_bucket_to_private(monkeypatch) -> None:
    calls: list[tuple[str, dict]] = []

    class _FakeStorage:
        def get_bucket(self, name: str):
            assert name in {"fotos-tecnica", "documentos-estudio"}
            return {"name": name, "public": True}

        def update_bucket(self, name: str, options: dict):
            calls.append((name, options))

        def create_bucket(self, name: str, options: dict):
            raise AssertionError("create_bucket no debe llamarse cuando el bucket ya existe")

    class _FakeClient:
        storage = _FakeStorage()

    monkeypatch.setattr(init_db, "create_client", lambda *_args, **_kwargs: _FakeClient())
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")

    init_db._init_storage()

    assert calls
    by_bucket = {name: options for name, options in calls}
    assert by_bucket["fotos-tecnica"]["public"] is False
    assert "image/jpeg" in by_bucket["fotos-tecnica"]["allowed_mime_types"]
    assert "image/png" in by_bucket["fotos-tecnica"]["allowed_mime_types"]
    assert by_bucket["fotos-tecnica"]["file_size_limit"] == 10 * 1024 * 1024
    assert "application/pdf" in by_bucket["documentos-estudio"]["allowed_mime_types"]


def test_init_storage_creates_private_bucket_when_missing(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []

    class _FakeStorage:
        def get_bucket(self, _name: str):
            raise RuntimeError("bucket no existe")

        def update_bucket(self, _name: str, _options: dict):
            raise AssertionError("update_bucket no debe llamarse cuando no existe")

        def create_bucket(self, name: str, options: dict):
            created.append((name, options))

    class _FakeClient:
        storage = _FakeStorage()

    monkeypatch.setattr(init_db, "create_client", lambda *_args, **_kwargs: _FakeClient())
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")

    init_db._init_storage()

    assert created
    by_bucket = {name: options for name, options in created}
    assert by_bucket["fotos-tecnica"]["public"] is False
    assert by_bucket["documentos-estudio"]["public"] is False
    assert "application/pdf" in by_bucket["documentos-estudio"]["allowed_mime_types"]
