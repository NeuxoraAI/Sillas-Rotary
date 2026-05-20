"""Minimal test environment for vista_tecnicos unit tests."""

import os

# Guarantee a deterministic JWT secret BEFORE any module import
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-" + ("x" * 32),
)
