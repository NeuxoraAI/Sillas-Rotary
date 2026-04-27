"""Contract tests for monetary formatting logic in front/socioeconomico.html."""

from pathlib import Path


def _load_socioeconomico_html() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / "front" / "socioeconomico.html").read_text(encoding="utf-8")


def test_declares_shared_monetary_field_ids_constant() -> None:
    html = _load_socioeconomico_html()

    assert "const MONETARY_FIELD_IDS" in html
    assert "tutor1_ingreso_mensual" in html
    assert "tutor2_ingreso_mensual" in html
    assert "monto_otras_fuentes" in html


def test_declares_monetary_sanitization_and_format_helpers() -> None:
    html = _load_socioeconomico_html()

    assert "function sanitizeMoneyInput(raw)" in html
    assert "function formatMoneyDisplay(raw)" in html
    assert "function toMoneyNumberOrNull(raw)" in html


def test_uses_monetary_helpers_across_post_patch_and_rehydration() -> None:
    html = _load_socioeconomico_html()

    # POST + PATCH canonical serialization
    assert html.count("toMoneyNumberOrNull(") >= 3

    # Draft load rehydration uses display formatter
    assert "formatMoneyDisplay(String(t.ingreso_mensual))" in html
    assert "formatMoneyDisplay(String(data.monto_otras_fuentes))" in html

    # Live UX formatting listener in input flow
    assert ".addEventListener('input'" in html
    assert "MONETARY_FIELD_IDS.forEach" in html
