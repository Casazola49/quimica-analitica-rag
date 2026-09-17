"""Tier 1: Feature 8 - Syllabus-Guided Tutor Engine Tests.

Verifies interactive progressive tutoring, conversation history handling, and next topic suggestions.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_tutor_module, get_syllabus_module


class TestFeature08TutorEngine:
    """Feature 8: Syllabus-Guided Tutor Engine verification."""

    def test_get_tutor_response_generates_guidance(self, valid_api_key: str) -> None:
        """Verify tutor returns domain-specific pedagogical explanation for current unit."""
        tutor = get_tutor_module()
        msg = "Tengo dudas sobre cómo se calcula el RSS de Von Weimarn."
        response = tutor.get_tutor_response(msg, history=[], current_unit_id="U3", api_key=valid_api_key)
        assert isinstance(response, str)
        assert len(response) > 50
        assert "Weimarn" in response or "sobresaturación" in response.lower() or "precipita" in response.lower()

    def test_get_tutor_response_with_conversation_history(self, valid_api_key: str) -> None:
        """Verify tutor accepts multi-turn history list and continues context."""
        tutor = get_tutor_module()
        history = [
            {"role": "user", "content": "¿Qué es la coprecipitación?"},
            {"role": "assistant", "content": "Es la precipitación de una sustancia normalmente soluble junto con el precipitado principal."},
        ]
        msg = "¿Cuáles son los cuatro tipos de coprecipitación?"
        response = tutor.get_tutor_response(msg, history=history, current_unit_id="U3", api_key=valid_api_key)
        assert isinstance(response, str)
        assert len(response) > 30

    def test_suggest_next_topic_progresses_through_syllabus(self) -> None:
        """Verify tutor suggests the next uncompleted topic in the active unit."""
        tutor = get_tutor_module()
        completed = ["Definiciones", "Etapas del análisis"]
        suggestion = tutor.suggest_next_topic(current_unit_id="U1", completed_topics=completed)
        assert "next_topic" in suggestion
        assert suggestion["next_topic"] not in completed
        assert suggestion["unit_id"] == "U1"

    def test_suggest_next_topic_all_completed_suggests_evaluation(self) -> None:
        """Verify tutor suggests unit evaluation when all topics are marked completed."""
        tutor = get_tutor_module()
        syllabus = get_syllabus_module()
        unit_u1 = syllabus.get_unit_by_id("U1")
        all_u1_topics = unit_u1["topics"] if unit_u1 else ["Tema 1", "Tema 2"]
        suggestion = tutor.suggest_next_topic(current_unit_id="U1", completed_topics=all_u1_topics)
        assert "next_topic" in suggestion
        assert "evalua" in suggestion["next_topic"].lower() or "examen" in suggestion["next_topic"].lower()

    def test_get_tutor_response_empty_message_prompts_user(self, valid_api_key: str) -> None:
        """Verify tutor prompts user if an empty query is submitted."""
        tutor = get_tutor_module()
        response = tutor.get_tutor_response("", history=[], current_unit_id="U1", api_key=valid_api_key)
        assert "duda" in response.lower() or "pregunta" in response.lower() or "ingresa" in response.lower()
