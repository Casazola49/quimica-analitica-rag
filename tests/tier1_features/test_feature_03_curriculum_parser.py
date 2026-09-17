"""Tier 1: Feature 3 - Curriculum Parser & Schema Tests.

Verifies parser for Theory (9 units) and Laboratory (8 units / 13 practices) syllabi.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_syllabus_module


class TestFeature03CurriculumParser:
    """Feature 3: Curriculum Parser & Schema verification."""

    def test_load_curriculum_returns_valid_structure(self) -> None:
        """Verify load_curriculum loads dictionary with required schema elements."""
        syllabus = get_syllabus_module()
        spec = syllabus.load_curriculum()
        assert isinstance(spec, dict)
        assert "theory_units" in spec, "Curriculum must contain 'theory_units'"
        assert "lab_units" in spec, "Curriculum must contain 'lab_units'"

    def test_theory_units_count_and_ids(self) -> None:
        """Verify exactly 9 Theory Units exist with canonical IDs U1 to U9."""
        syllabus = get_syllabus_module()
        theory_units = syllabus.get_theory_units()
        assert len(theory_units) == 9, f"Expected 9 theory units, found {len(theory_units)}"

        unit_ids = [u["id"].upper() for u in theory_units]
        expected_ids = [f"U{i}" for i in range(1, 10)]
        assert unit_ids == expected_ids, f"Expected unit IDs {expected_ids}, got {unit_ids}"

    def test_lab_units_and_13_practices_count(self) -> None:
        """Verify 8 Lab Units containing a total of 13 experimental practices."""
        syllabus = get_syllabus_module()
        lab_units = syllabus.get_lab_units()
        assert len(lab_units) == 8, f"Expected 8 lab units, found {len(lab_units)}"

        total_practices = 0
        practice_numbers = []
        for unit in lab_units:
            assert "practices" in unit, f"Unit {unit.get('id')} must contain 'practices' list"
            for p in unit["practices"]:
                total_practices += 1
                practice_numbers.append(p["practice_num"])

        assert total_practices == 13, f"Expected 13 practical experiments, got {total_practices}"
        assert sorted(practice_numbers) == list(range(1, 14)), "Practices must cover numbers 1 to 13 consecutively"

    def test_get_unit_by_id_retrieves_target(self) -> None:
        """Verify retrieving specific unit by ID (case-insensitive)."""
        syllabus = get_syllabus_module()
        unit_u3 = syllabus.get_unit_by_id("U3")
        assert unit_u3 is not None
        title_u3 = unit_u3["title"].lower()
        assert "gravimétr" in title_u3 or "gravimetr" in title_u3

        unit_u6_lower = syllabus.get_unit_by_id("u6")
        assert unit_u6_lower is not None
        title_u6 = unit_u6_lower["title"].lower()
        assert "neutraliz" in title_u6 or "ácido" in title_u6 or "acido" in title_u6

    def test_match_topics_to_curriculum_domain_mapping(self) -> None:
        """Verify keyword heuristic maps domain terminology to correct syllabus units."""
        syllabus = get_syllabus_module()

        # U3: Gravimetry / Sulfate
        matches_u3 = syllabus.match_topics_to_curriculum("Precipitación de sulfatos como BaSO4")
        assert "U3" in matches_u3, f"Expected 'U3' in matches for sulfate gravimetry, got {matches_u3}"

        # U5: Argentometry / Mohr
        matches_u5 = syllabus.match_topics_to_curriculum("Titulación de cloruros por el método de Mohr")
        assert "U5" in matches_u5, f"Expected 'U5' in matches for Mohr method, got {matches_u5}"

        # U7: Complexometry / EDTA
        matches_u7 = syllabus.match_topics_to_curriculum("Dureza total del agua con EDTA y Negro de Eriocromo T")
        assert "U7" in matches_u7, f"Expected 'U7' in matches for EDTA, got {matches_u7}"
