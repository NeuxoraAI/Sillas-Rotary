"""Tests for app initialization and production docs exposure rules."""

from fastapi.testclient import TestClient

from main import create_app


def test_root_redirects_to_login() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code in (301, 302, 303, 307)
    assert "/login.html" in response.headers.get("location", "")


def test_docs_disabled_when_env_is_production(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "production")
    app = create_app()

    with TestClient(app) as client:
        docs = client.get("/docs")
        redoc = client.get("/redoc")
        openapi = client.get("/openapi.json")

    assert docs.status_code == 404
    assert redoc.status_code == 404
    assert openapi.status_code == 404


def test_docs_enabled_outside_production(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    app = create_app()

    with TestClient(app) as client:
        docs = client.get("/docs")
        openapi = client.get("/openapi.json")

    assert docs.status_code == 200
    assert "text/html" in docs.headers.get("content-type", "")
    assert openapi.status_code == 200


def test_api_health_endpoint_reports_ok() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_are_present_on_api_responses() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("cache-control") == "no-store"


def test_static_assets_have_short_public_cache() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/assets/logo_vida_ug.png")

    assert response.status_code == 200
    assert response.headers.get("cache-control") == "public, max-age=3600"
