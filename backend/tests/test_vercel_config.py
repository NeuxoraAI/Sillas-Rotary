"""Regression tests for production hardening in vercel.json."""

import json
from pathlib import Path


def _load_vercel_config() -> dict:
    root = Path(__file__).resolve().parents[2]
    config_path = root / "vercel.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def test_vercel_defines_security_headers() -> None:
    config = _load_vercel_config()

    headers = config.get("headers", [])
    assert headers, "vercel.json must define security headers"

    source_to_headers = {
        entry["source"]: {h["key"].lower(): h["value"] for h in entry.get("headers", [])}
        for entry in headers
    }

    assert "/(.*)" in source_to_headers
    assert source_to_headers["/(.*)"].get("x-content-type-options") == "nosniff"
    assert source_to_headers["/(.*)"].get("x-frame-options") == "DENY"


def test_vercel_blocks_internal_paths_before_rewrite() -> None:
    config = _load_vercel_config()
    routes = config.get("routes", [])

    assert any(route.get("status") == 404 for route in routes), (
        "vercel.json must block internal paths using 404 routes"
    )

    blocked_patterns = [route.get("src", "") for route in routes if route.get("status") == 404]
    assert any("backend" in pattern for pattern in blocked_patterns)
    assert any("\\.sql" in pattern for pattern in blocked_patterns)


def test_vercel_defines_python_build_with_frontend_includes() -> None:
    config = _load_vercel_config()

    builds = config.get("builds", [])
    assert builds, "vercel.json must define a Python build"

    python_builds = [b for b in builds if b.get("use") == "@vercel/python"]
    assert python_builds, "vercel.json must include a @vercel/python build"

    build = python_builds[0]
    assert build.get("src") == "api/index.py"
    assert build.get("config", {}).get("includeFiles") == "front/**"


def test_root_requirements_include_runtime_dependencies() -> None:
    root = Path(__file__).resolve().parents[2]
    requirements_path = root / "requirements.txt"
    requirements = requirements_path.read_text(encoding="utf-8")

    assert requirements_path.exists(), "Vercel Python runtime expects dependencies at project root"
    assert "openpyxl>=3.1.0" in requirements
    assert "fastapi==0.115.0" in requirements
