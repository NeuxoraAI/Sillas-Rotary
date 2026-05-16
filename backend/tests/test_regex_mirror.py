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
                if isinstance(target, ast.Name) and target.id.endswith("_RE"):
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

    def test_all_backend_regexes_have_js_mirror(self):
        """Every _RE constant in validators.py must exist in validations.js."""
        py_regexes = _extract_python_regex(VALIDATORS_PY)
        js_regexes = _extract_js_regex(VALIDATIONS_JS)

        for name in py_regexes:
            assert name in js_regexes, f"Missing JS mirror for {name}"

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
