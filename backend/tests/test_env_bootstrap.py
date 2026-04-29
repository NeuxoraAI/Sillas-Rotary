import os
from pathlib import Path

from env_bootstrap import load_root_env_if_needed


def test_load_root_env_if_needed_loads_project_root_dotenv(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    backend_dir = project_root / "backend"
    backend_dir.mkdir(parents=True)
    env_file = project_root / ".env"
    env_file.write_text("JWT_SECRET=test-secret-xxxxxxxxxxxxxxxxxxxxxxxx\nDB_HOST=localhost\n")

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)

    loaded = load_root_env_if_needed(backend_dir / "main.py")

    assert loaded is True
    assert os.environ["JWT_SECRET"] == "test-secret-xxxxxxxxxxxxxxxxxxxxxxxx"
    assert os.environ["DB_HOST"] == "localhost"


def test_load_root_env_if_needed_keeps_existing_env_values(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    backend_dir = project_root / "backend"
    backend_dir.mkdir(parents=True)
    env_file = project_root / ".env"
    env_file.write_text("JWT_SECRET=from-file-should-not-override\n")

    monkeypatch.setenv("JWT_SECRET", "already-set")

    loaded = load_root_env_if_needed(Path(backend_dir / "main.py"))

    assert loaded is True
    assert os.environ["JWT_SECRET"] == "already-set"
