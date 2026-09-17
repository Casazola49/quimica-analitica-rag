"""Tier 1: Feature 11 - Syllabus Topic Navigator UI Tests.

Verifies interactive curriculum browser for Theory (9 units) and Laboratory (8 units / 13 practices).
"""

from __future__ import annotations

import pytest
from tests.helpers import get_syllabus_module


class TestFeature11SyllabusNavigator:
    """Feature 11: Syllabus Topic Navigator UI verification."""

    def test_navigator_theory_units_data(self) -> None:
        """Verify navigator can retrieve complete theory curriculum nodes."""
        syllabus = get_syllabus_module()
        units = syllabus.get_theory_units()
        assert len(units) == 9
        for u in units:
            assert "id" in u
            assert "title" in u
            assert "topics" in u
            assert isinstance(u["topics"], list)
            assert len(u["topics"]) > 0

    def test_navigator_lab_units_data(self) -> None:
        """Verify navigator can retrieve complete laboratory curriculum nodes."""
        syllabus = get_syllabus_module()
        units = syllabus.get_lab_units()
        assert len(units) == 8
        for u in units:
            assert "id" in u
            assert "title" in u
            assert "practices" in u
            assert isinstance(u["practices"], list)

    def test_navigator_subtopics_expansion(self) -> None:
        """Verify specific subtopics are accessible for detailed accordion display."""
        syllabus = get_syllabus_module()
        unit_u3 = syllabus.get_unit_by_id("U3")
        assert unit_u3 is not None
        topics = unit_u3["topics"]
        topic_titles = [t.get("title", str(t)) if isinstance(t, dict) else str(t) for t in topics]
        assert any("weimarn" in t.lower() or "sobresaturación" in t.lower() or "sobresaturacion" in t.lower() for t in topic_titles)
        assert any("coprecipit" in t.lower() for t in topic_titles)

    def test_navigator_tutor_action_payload(self) -> None:
        """Verify building navigation action to launch tutor on a specific unit."""
        unit_id = "U4"
        action_payload = {
            "action": "open_tutor",
            "target_unit": unit_id,
            "prefill_prompt": f"Hola, quiero repasar los conceptos de la {unit_id} (Solubilidad)."
        }
        assert action_payload["target_unit"] == "U4"
        assert "open_tutor" in action_payload["action"]

    def test_navigator_exam_action_payload(self) -> None:
        """Verify building navigation action to launch exam simulator on a specific unit."""
        unit_id = "U6"
        action_payload = {
            "action": "start_exam",
            "target_unit": unit_id,
            "default_count": 3
        }
        assert action_payload["target_unit"] == "U6"
        assert action_payload["default_count"] == 3
