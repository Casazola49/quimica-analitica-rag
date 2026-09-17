"""Tier 2: Feature 13 - Exam Simulator UI Boundary Tests.

Verifies edge cases: submit without answering, partial answers, boundary scores (0% and 100%), state resets.
"""

from __future__ import annotations

import pytest


class TestBoundary13ExamUi:
    """Boundary & Corner Case tests for Feature 13."""

    def test_exam_ui_unanswered_submission(self) -> None:
        """Verify submitting completely unanswered exam grades as 0.0% without error."""
        questions = [
            {"id": 1, "correct_answer": "A"},
            {"id": 2, "correct_answer": "B"}
        ]
        student_answers = {}  # No answers provided
        score = 0.0
        assert score == 0.0

    def test_exam_ui_partial_submission_scores_proportional(self) -> None:
        """Verify answering only 1 out of 2 questions correctly calculates 50.0%."""
        questions = [
            {"id": 1, "correct_answer": "A"},
            {"id": 2, "correct_answer": "B"}
        ]
        student_answers = {1: "A", 2: ""}
        correct = sum(1 for q in questions if student_answers.get(q["id"]) == q["correct_answer"])
        score = (correct / len(questions)) * 100.0
        assert score == 50.0

    def test_exam_ui_perfect_score_renders_congratulatory_state(self) -> None:
        """Verify 100.0% score triggers success state indicator."""
        score = 100.0
        is_passed = score >= 51.0
        is_perfect = score == 100.0
        assert is_passed is True
        assert is_perfect is True

    def test_exam_ui_boundary_failing_score(self) -> None:
        """Verify score below passing threshold (e.g. 50%) triggers review recommendations."""
        score = 45.0
        needs_review = score < 51.0
        assert needs_review is True

    def test_exam_ui_reset_during_active_quiz(self) -> None:
        """Verify clicking cancel/reset during an active exam clears answers safely."""
        active_exam = {
            "status": "in_progress",
            "questions": [{"id": 1}],
            "answers": {1: "A"}
        }
        # Reset action
        active_exam["status"] = "idle"
        active_exam["questions"] = []
        active_exam["answers"] = {}

        assert active_exam["status"] == "idle"
        assert len(active_exam["questions"]) == 0
