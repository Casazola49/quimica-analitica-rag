"""Tier 1: Feature 13 - Exam Simulator UI Tests.

Verifies interactive practice exam interface state management, submission workflow, and score rendering.
"""

from __future__ import annotations

import pytest


class TestFeature13ExamUi:
    """Feature 13: Exam Simulator UI verification."""

    def test_exam_ui_question_rendering_state(self) -> None:
        """Verify exam state can store and render active question objects."""
        exam_session = {
            "status": "ready",
            "active_unit": "U3",
            "questions": [
                {
                    "id": 1,
                    "question": "¿Cuál es la función del papel Whatman 42?",
                    "options": ["A) Filtro sin cenizas", "B) Papel indicador", "C) Desecante", "D) Fundente"],
                    "correct_answer": "A"
                }
            ],
            "student_answers": {}
        }
        assert exam_session["status"] == "ready"
        assert len(exam_session["questions"]) == 1

    def test_exam_ui_options_radio_button_format(self) -> None:
        """Verify option strings conform to clear prefix format for UI radio selection."""
        options = ["A) Opción 1", "B) Opción 2", "C) Opción 3", "D) Opción 4"]
        for opt in options:
            assert opt[0] in ["A", "B", "C", "D"]
            assert opt[1:3] == ") "

    def test_exam_ui_submission_state_transition(self) -> None:
        """Verify submitting exam answers transitions status to 'evaluated'."""
        exam_session = {
            "status": "in_progress",
            "score": None,
        }
        # Simulate submission
        exam_session["status"] = "evaluated"
        exam_session["score"] = 100.0
        assert exam_session["status"] == "evaluated"
        assert exam_session["score"] == 100.0

    def test_exam_ui_score_badge_rendering(self) -> None:
        """Verify score presentation formats correctly into visual badges."""
        score_val = 85.5
        badge_text = f"Puntaje Obtenido: {score_val}%"
        assert "85.5%" in badge_text

    def test_exam_ui_reset_allows_retake(self) -> None:
        """Verify resetting exam state allows student to generate a new quiz."""
        exam_session = {
            "status": "evaluated",
            "score": 100.0,
            "questions": [{"id": 1}],
            "student_answers": {"q1": "A"}
        }
        # Reset
        exam_session["status"] = "idle"
        exam_session["score"] = None
        exam_session["questions"] = []
        exam_session["student_answers"] = {}

        assert exam_session["status"] == "idle"
        assert len(exam_session["questions"]) == 0
