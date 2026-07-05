from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "JWT_STORAGE_SECURITY.md"
README = ROOT / "README.md"


def test_jwt_storage_security_decision_is_documented() -> None:
    content = DOC.read_text(encoding="utf-8")

    assert "Keep `localStorage['session']" in content
    assert "accepted short-term risk" in content
    assert "httpOnly" in content, "Cookie migration target must be documented"
    assert "CSRF" in content


def test_jwt_storage_doc_lists_required_xss_mitigations() -> None:
    content = DOC.read_text(encoding="utf-8")

    for required in (
        "Content-Security-Policy",
        "script-src",
        "No new third-party scripts",
        "strict sanitization",
        "JWT_EXPIRE_HOURS",
        "cdn.tailwindcss.com",
    ):
        assert required in content


def test_readme_links_jwt_storage_security_decision() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "docs/JWT_STORAGE_SECURITY.md" in readme
