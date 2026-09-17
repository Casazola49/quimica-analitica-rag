"""Tier 1: Feature 9 - Dynamic Exam Simulator Engine Tests.

Verifies dynamic question generation, multiple choice rubric validation, and automated grading with citations.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_exam_module


class TestFeature09ExamSimulator:
    """Feature 9: Dynamic Exam Simulator Engine verification."""

    def test_generate_exam_questions_count(self, valid_api_key: str) -> None:
        """Verify exam engine generates requested number of questions."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U3", count=3, difficulty="media", api_key=valid_api_key)
        assert isinstance(questions, list)
        assert len(questions) == 3, f"Expected 3 questions, got {len(questions)}"

    def test_generate_exam_questions_schema_fields(self, valid_api_key: str) -> None:
        """Verify each question contains required rubric fields and citation."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U6", count=1, difficulty="media", api_key=valid_api_key)
        assert len(questions) >= 1
        q = questions[0]
        assert "id" in q
        assert "question" in q
        assert "options" in q
        assert isinstance(q["options"], list)
        assert len(q["options"]) >= 2
        assert "correct_answer" in q
        assert "explanation" in q
        assert "citation" in q
        assert "book_title" in q["citation"]

    def test_evaluate_exam_submission_perfect_score(self, valid_api_key: str) -> None:
        """Verify submitting all correct answers evaluates to 100.0% score."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U3", count=2, difficulty="media", api_key=valid_api_key)
        correct_answers = [q["correct_answer"] for q in questions]

        result = exam.evaluate_exam_submission(questions, correct_answers, api_key=valid_api_key)
        assert "score" in result
        assert result["score"] == 100.0
        assert result["correct_answers"] == len(questions)

    def test_evaluate_exam_submission_feedback_and_citations(self, valid_api_key: str) -> None:
        """Verify evaluation returns structured per-question feedback and bibliographic citations."""
        exam = get_exam_module()
        questions = [
            {
                "id": 1,
                "question": "¿Cuál es el precipitado rojo en el método de Mohr?",
                "options": ["A) AgCl", "B) Ag2CrO4", "C) BaSO4", "D) Fe(SCN)2+"],
                "correct_answer": "B",
                "explanation": "El cromato de plata Ag2CrO4 es el indicador de punto final.",
                "citation": {
                    "book_title": "Fundamentos de Química Analítica",
                    "author": "Skoog et al.",
                    "edition": "9ª Edición",
                    "chapter": "Capítulo 17",
                    "page_num": 412
                }
            }
        ]
        student_answers = ["B"]
        evaluation = exam.evaluate_exam_submission(questions, student_answers, api_key=valid_api_key)
        assert "feedback" in evaluation
        assert len(evaluation["feedback"]) == 1
        fb = evaluation["feedback"][0]
        assert fb["is_correct"] is True
        assert "citations" in evaluation
        assert len(evaluation["citations"]) >= 1

    def test_evaluate_exam_empty_questions_graceful(self, valid_api_key: str) -> None:
        """Verify evaluation of empty question set returns zero score gracefully."""
        exam = get_exam_module()
        result = exam.evaluate_exam_submission([], [], api_key=valid_api_key)
        assert result["score"] == 0.0
        assert result["feedback"] == []
