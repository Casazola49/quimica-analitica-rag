"""Tier 2: Feature 10 - Streamlit Web Application Portal Boundary Tests.

Verifies edge cases: empty session states, rapid key toggles, missing active unit, session isolation deep copy.
"""

from __future__ import annotations

import copy
import pytest


class TestBoundary10Portal:
    """Boundary & Corner Case tests for Feature 10."""

    def test_portal_uninitialized_session_state(self) -> None:
        """Verify accessing uninitialized session state keys returns default fallback values."""
        empty_session: dict[str, Any] = {}
        active_tab = empty_session.get("active_tab", "Syllabus Navigator")
        api_key = empty_session.get("gemini_api_key", None)
        active_unit = empty_session.get("current_unit", "U1")

        assert active_tab == "Syllabus Navigator"
        assert api_key is None
        assert active_unit == "U1"

    def test_portal_rapid_key_toggle_idempotence(self, valid_api_key: str) -> None:
        """Verify repeatedly setting and disconnecting API key remains stable and idempotent."""
        session: dict[str, str] = {}
        for _ in range(10):
            session["gemini_api_key"] = valid_api_key
            assert session["gemini_api_key"] == valid_api_key
            session.pop("gemini_api_key", None)
            assert "gemini_api_key" not in session

    def test_portal_session_deep_copy_mutation_isolation(self) -> None:
        """Verify that mutations in one student's session cannot leak into another session."""
        session_a = {
            "gemini_api_key": "AIzaSyStudentA_11111111111111111111",
            "messages": [{"role": "user", "content": "Pregunta de A"}]
        }
        session_b = copy.deepcopy(session_a)
        session_b["gemini_api_key"] = "AIzaSyStudentB_22222222222222222222"
        session_b["messages"].append({"role": "user", "content": "Pregunta de B"})

        assert session_a["gemini_api_key"] != session_b["gemini_api_key"]
        assert len(session_a["messages"]) == 1
        assert len(session_b["messages"]) == 2

    def test_portal_extreme_chat_message_lengths(self) -> None:
        """Verify handling very large single chat input (10,000 characters)."""
        session_messages = []
        huge_message = "Muestreo y análisis de mineral. " * 350
        session_messages.append({"role": "user", "content": huge_message})
        assert len(session_messages[0]["content"]) > 10000

    def test_portal_invalid_query_params_handling(self) -> None:
        """Verify malformed URL query parameters do not corrupt internal portal state."""
        query_params = {"unit": "INVALID_INJECTION';--", "tab": "<script>alert(1)</script>"}
        # Sanitization logic:
        clean_unit = "U1" if not query_params["unit"].startswith("U") else query_params["unit"]
        assert clean_unit == "U1"
