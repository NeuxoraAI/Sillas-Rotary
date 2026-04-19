"""
Unit tests for the format_folio pure function.
No database, no network — pure logic only.

TDD: These tests were written BEFORE the implementation.
"""

import pytest
from utils.folio import format_folio


class TestFormatFolio:
    """Tests for the format_folio() pure function."""

    def test_first_beneficiario_formats_with_three_digit_padding(self):
        """num=1 → 001 — standard registration folio."""
        result = format_folio("MX", "LON", 2026, 1)
        assert result == "MX-LON-2026-001"

    def test_two_digit_number_padded(self):
        """num=25 → 025."""
        result = format_folio("US", "PRL", 2026, 25)
        assert result == "US-PRL-2026-025"

    def test_three_digit_number_no_padding(self):
        """num=100 → 100 (no extra leading zero needed)."""
        result = format_folio("MX", "IRA", 2026, 100)
        assert result == "MX-IRA-2026-100"

    def test_four_digit_number_no_truncation(self):
        """num=1000 → 1000 (padding spec is 3-digit minimum, no truncation)."""
        result = format_folio("MX", "LON", 2026, 1000)
        assert result == "MX-LON-2026-1000"

    def test_different_year(self):
        """Year is included correctly in folio."""
        result = format_folio("MX", "LON", 2027, 1)
        assert result == "MX-LON-2027-001"

    def test_format_is_hyphen_separated(self):
        """All four parts are joined with hyphens."""
        result = format_folio("CO", "BOG", 2026, 5)
        parts = result.split("-")
        assert len(parts) == 4
        assert parts[0] == "CO"
        assert parts[1] == "BOG"
        assert parts[2] == "2026"
        assert parts[3] == "005"

    def test_us_region(self):
        """USA format works correctly."""
        result = format_folio("US", "HOU", 2026, 3)
        assert result == "US-HOU-2026-003"
