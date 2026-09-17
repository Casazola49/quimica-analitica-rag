"""Tier 2: Feature 9 - Dynamic Exam Simulator Engine Boundary Tests.

Verifies edge cases: count 0, count 100, invalid difficulty strings, answer length mismatches, empty answers.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_exam_module


class TestBoundary09Exam:
    """Boundary & Corner Case tests for Feature 9."""

    def test_exam_generate_count_zero_clamped(self, valid_api_key: str) -> None:
        """Verify requesting 0 questions clamps safely to at least 1 question."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U3", count=0, api_key=valid_api_key)
        assert len(questions) >= 1

    def test_exam_generate_extreme_count_clamped(self, valid_api_key: str) -> None:
        """Verify requesting 100 questions clamps safely to a bounded maximum (<= 10)."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U3", count=100, api_key=valid_api_key)
        assert len(questions) <= 10

    def test_exam_invalid_difficulty_defaults_gracefully(self, valid_api_key: str) -> None:
        """Verify passing non-standard difficulty string does not raise error."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U6", count=2, difficulty="EXTREMA_IMPOSIBLE", api_key=valid_api_key)
        assert len(questions) >= 1

    def test_exam_evaluate_answers_length_mismatch(self, valid_api_key: str) -> None:
        """Verify submitting fewer answers than questions evaluates remaining as unanswered without crashing."""
        exam = get_exam_module()
        questions = [
            {"id": 1, "question": "Q1", "options": ["A", "B"], "correct_answer": "A"},
            {"id": 2, "question": "Q2", "options": ["A", "B"], "correct_answer": "B"},
            {"id": 3, "question": "Q3", "options": ["A", "B"], "correct_answer": "A"}
        ]
        student_answers = ["A"]  # Only answered Q1

        result = exam.evaluate_exam_submission(questions, student_answers, api_key=valid_api_key)
        assert result["total_questions"] == 3
        assert result["correct_answers"] == 1
        assert result["score"] == pytest.approx(33.3, 0.1)

    def test_exam_evaluate_all_empty_answers(self, valid_api_key: str) -> None:
        """Verify submitting all empty strings results in 0.0% score cleanly."""
        exam = get_exam_module()
        questions = [
            {"id": 1, "question": "Q1", "options": ["A", "B"], "correct_answer": "A"},
            {"id": 2, "question": "Q2", "options": ["A", "B"], "correct_answer": "B"}
        ]
        student_answers = ["", ""]
        result = exam.evaluate_exam_submission(questions, student_answers, api_key=valid_api_key)
        assert result["score"] == 0.0
        assert result["correct_answers"] == 0
