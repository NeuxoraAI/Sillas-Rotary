"""
Mirror test: verify that regex constants in validations.js match those in validators.py.

This test ensures the frontend and backend stay synchronized. If you change a regex
in validators.py, you MUST update validations.js and this test will pass.
"""

import re
import ast
import pathlib


PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
VALIDATORS_PY = PROJECT_ROOT / "backend" / "validators.py"
VALIDATIONS_JS = PROJECT_ROOT / "front" / "assets" / "js" / "validations.js"


def _extract_python_regex(filepath):
    """Parse a Python file and extract re.compile() string arguments."""
    content = filepath.read_text(encoding="utf-8")
    tree = ast.parse(content)
    regexes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and (
                    target.id.endswith("_RE") or target.id.endswith("_REGEX")
                ):
                    if isinstance(node.value, ast.Call):
                        # re.compile(r"...")
                        if node.value.args and isinstance(node.value.args[0], ast.Constant):
                            regexes[target.id] = node.value.args[0].value
                        elif node.value.args and isinstance(node.value.args[0], ast.JoinedStr):
                            # Handle f-strings if any
                            pass
    return regexes


def _extract_js_regex(filepath):
    """Extract regex literals from a JS file (naive but sufficient for our constants)."""
    content = filepath.read_text(encoding="utf-8")
    regexes = {}
    # Match: const NAME = /.../;
    for match in re.finditer(r"const\s+([A-Z_]+_RE)\s+=\s+(/.*?/);", content):
        name = match.group(1)
        pattern = match.group(2)
        # Remove leading/trailing slashes and any flags
        pattern = pattern[1:]  # Remove leading /
        if pattern.endswith("/"):
            pattern = pattern[:-1]
        else:
            # Has flags, remove them
            idx = pattern.rfind("/")
            if idx > 0:
                pattern = pattern[:idx]
        regexes[name] = pattern
    return regexes


class TestRegexMirror:
    """Verify frontend regexes match backend regexes."""

    # Backend names whose JS mirror has a different name
    _JS_NAME_OVERRIDES = {"_MEASURE_REGEX": "MEASURE_FINAL_RE"}
    # Charsets that intentionally differ (JS allows a-z; backend canonicalizes)
    _NO_MIRROR = {"_NUM_DOMICILIO_RE"}

    def test_all_backend_regexes_have_js_mirror(self):
        """Every regex constant in validators.py must exist in validations.js."""
        py_regexes = _extract_python_regex(VALIDATORS_PY)
        js_regexes = _extract_js_regex(VALIDATIONS_JS)

        for name in py_regexes:
            if name in self._NO_MIRROR:
                continue
            js_name = self._JS_NAME_OVERRIDES.get(name, name.lstrip("_"))
            assert js_name in js_regexes, f"Missing JS mirror for {name} ({js_name})"

    def test_obs_whitelist_matches(self):
        """OBS_WHITELIST_RE must be identical in both files."""
        py_regexes = _extract_python_regex(VALIDATORS_PY)
        js_regexes = _extract_js_regex(VALIDATIONS_JS)
        assert py_regexes["_OBS_WHITELIST_RE"] == js_regexes["OBS_WHITELIST_RE"]

    def test_entidad_whitelist_matches(self):
        """ENTIDAD_WHITELIST_RE must be identical in both files."""
        py_regexes = _extract_python_regex(VALIDATORS_PY)
        js_regexes = _extract_js_regex(VALIDATIONS_JS)
        assert py_regexes["_ENTIDAD_WHITELIST_RE"] == js_regexes["ENTIDAD_WHITELIST_RE"]

    def test_measure_regex_matches(self):
        """MEASURE_REGEX must be identical in both files."""
        py_regexes = _extract_python_regex(VALIDATORS_PY)
        js_regexes = _extract_js_regex(VALIDATIONS_JS)
        assert py_regexes["_MEASURE_REGEX"] == js_regexes["MEASURE_FINAL_RE"]


class TestRegexBehavioralMirror:
    """Behavioral checks for charsets that differ only in ordering between
    front and back (exact string comparison is not possible)."""

    def test_diagnostico_allows_dollar_sign(self):
        """Frontend DIAGNOSTICO_RE accepts '$' (income descriptions);
        the backend must accept it too or consolidation 422s."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from validators import validate_diagnostico, validate_otras_fuentes_ingreso

        assert validate_diagnostico("GASTO $500 MENSUAL") == "GASTO $500 MENSUAL"
        assert validate_otras_fuentes_ingreso("VENTAS $200") == "VENTAS $200"

    def test_numero_domicilio_canonicalizes_lowercase(self):
        """Frontend allows lowercase letters in num_ext; backend uppercases
        instead of rejecting (legacy drafts carry values like '12a')."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from validators import validate_numero_domicilio

        assert validate_numero_domicilio("12a") == "12A"
        assert validate_numero_domicilio("S/N") == "S/N"
