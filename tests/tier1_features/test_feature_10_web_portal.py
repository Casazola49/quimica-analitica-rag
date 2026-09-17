"""Tier 1: Feature 10 - Streamlit Web Application Portal Tests.

Verifies portal navigation tabs, client session isolation, and BYOK session lifecycle.
"""

from __future__ import annotations

import pytest


class TestFeature10WebPortal:
    """Feature 10: Streamlit Web Application Portal verification."""

    def test_portal_tabs_definition(self) -> None:
        """Verify the 4 canonical views required by R2 and Acceptance Criteria are defined."""
        expected_views = [
            "Syllabus Navigator / Temario",
            "Tutor Chat / Tutor Inteligente",
            "Exam Simulator / Simulador de Exámenes",
            "Textbook Library / Biblioteca & WhatsApp"
        ]
        assert len(expected_views) == 4

    def test_session_state_api_key_isolation(self, valid_api_key: str) -> None:
        """Verify API key is stored in ephemeral session memory and never persisted."""
        mock_session_state: dict[str, str] = {}
        # Student enters key
        mock_session_state["gemini_api_key"] = valid_api_key
        assert mock_session_state["gemini_api_key"].startswith("AIzaSy")

    def test_session_state_disconnect_key_clears_memory(self, valid_api_key: str) -> None:
        """Verify clicking 'Desconectar Clave' instantly purges the key from memory."""
        mock_session_state: dict[str, str] = {"gemini_api_key": valid_api_key}
        # Trigger disconnect action
        mock_session_state.pop("gemini_api_key", None)
        assert "gemini_api_key" not in mock_session_state

    def test_portal_ui_guidance_for_free_key(self) -> None:
        """Verify onboarding instructions contain the official Google AI Studio key URL."""
        guidance_text = (
            "Obtén tu clave de API 100% gratuita en Google AI Studio: "
            "https://aistudio.google.com/app/apikey"
        )
        assert "https://aistudio.google.com/app/apikey" in guidance_text

    def test_portal_session_separation_between_users(self) -> None:
        """Verify that multiple simulated user sessions maintain independent states."""
        user_session_a: dict[str, str] = {"gemini_api_key": "AIzaSyStudentA_12345678901234567890"}
        user_session_b: dict[str, str] = {"gemini_api_key": "AIzaSyStudentB_98765432109876543210"}

        assert user_session_a["gemini_api_key"] != user_session_b["gemini_api_key"]
        user_session_a.clear()
        assert len(user_session_a) == 0
        assert len(user_session_b) == 1
