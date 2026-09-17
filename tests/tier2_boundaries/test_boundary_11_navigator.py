"""Tier 2: Feature 11 - Syllabus Topic Navigator UI Boundary Tests.

Verifies edge cases: invalid unit lookups, empty topic lists, practice out of bounds, accented queries.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_syllabus_module


class TestBoundary11Navigator:
    """Boundary & Corner Case tests for Feature 11."""

    def test_navigator_invalid_unit_lookup_returns_none(self) -> None:
        """Verify invalid unit code returns None without error."""
        syllabus = get_syllabus_module()
        assert syllabus.get_unit_by_id("INVALID_UNIT_XYZ") is None

    def test_navigator_all_units_have_valid_titles(self) -> None:
        """Verify none of the 9 theory units have empty or whitespace-only titles."""
        syllabus = get_syllabus_module()
        theory_units = syllabus.get_theory_units()
        for u in theory_units:
            assert "title" in u
            assert len(u["title"].strip()) > 3

    def test_navigator_lab_practices_have_valid_numbers(self) -> None:
        """Verify all laboratory practices have positive integer practice numbers <= 13."""
        syllabus = get_syllabus_module()
        lab_units = syllabus.get_lab_units()
        for u in lab_units:
            for p in u.get("practices", []):
                assert 1 <= p["practice_num"] <= 13

    def test_navigator_accented_and_special_character_search(self) -> None:
        """Verify topic search handles accented characters and punctuation without error."""
        syllabus = get_syllabus_module()
        matches = syllabus.match_topics_to_curriculum("óxido-reducción, curvas de valoración redox y celdas galvánicas.")
        assert "U8" in matches

    def test_navigator_whitespace_padded_unit_lookup(self) -> None:
        """Verify lookup of unit IDs with surrounding whitespace succeeds."""
        syllabus = get_syllabus_module()
        u4 = syllabus.get_unit_by_id("   u4   ")
        assert u4 is not None
        assert u4["id"].upper() == "U4"
