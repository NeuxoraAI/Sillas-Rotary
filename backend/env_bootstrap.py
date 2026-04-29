import os
from pathlib import Path


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def load_root_env_if_needed(main_file_path: str | Path) -> bool:
    """
    Load ../.env relative to backend/main.py when present.

    Keeps already-defined environment values intact to avoid overriding
    explicit shell or process configuration.
    """
    backend_dir = Path(main_file_path).resolve().parent
    env_path = backend_dir.parent / ".env"
    if not env_path.exists():
        return False

    with env_path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)

    return True
