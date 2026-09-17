"""Tier 2: Feature 3 - Curriculum Parser & Schema Boundary Tests.

Verifies edge cases: unknown unit IDs, empty queries, special characters, fallback spec.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_syllabus_module


class TestBoundary03Curriculum:
    """Boundary & Corner Case tests for Feature 3."""

    def test_curriculum_unknown_unit_id_returns_none(self) -> None:
        """Verify querying non-existent unit returns None instead of raising Exception."""
        syllabus = get_syllabus_module()
        assert syllabus.get_unit_by_id("U999") is None
        assert syllabus.get_unit_by_id("NONEXISTENT_UNIT") is None
        assert syllabus.get_unit_by_id("") is None

    def test_curriculum_empty_topic_query_returns_empty_list(self) -> None:
        """Verify matching empty string returns empty list."""
        syllabus = get_syllabus_module()
        assert syllabus.match_topics_to_curriculum("") == []
        assert syllabus.match_topics_to_curriculum("    ") == []

    def test_curriculum_special_characters_query(self) -> None:
        """Verify queries with punctuation and symbols do not break matcher."""
        syllabus = get_syllabus_module()
        query = "¡¿Cómo determinar SO4(2-) con BaCl2 en crisol?! #$%&/()="
        matches = syllabus.match_topics_to_curriculum(query)
        assert isinstance(matches, list)
        assert "U3" in matches

    def test_curriculum_case_insensitive_and_whitespace_tolerant(self) -> None:
        """Verify unit retrieval handles arbitrary casing and leading/trailing whitespace."""
        syllabus = get_syllabus_module()
        u1_upper = syllabus.get_unit_by_id("U1")
        u1_lower = syllabus.get_unit_by_id("  u1  ")
        assert u1_upper is not None
        assert u1_lower is not None
        assert u1_upper["id"] == u1_lower["id"]

    def test_curriculum_missing_spec_file_fallback(self) -> None:
        """Verify load_curriculum falls back to built-in schema if file does not exist."""
        syllabus = get_syllabus_module()
        spec = syllabus.load_curriculum("/invalid/path/nonexistent_spec.json")
        assert spec is not None
        assert "theory_units" in spec or "courses" in spec
