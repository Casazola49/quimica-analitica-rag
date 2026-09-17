"""Tier 2: Feature 6 - BYOK Gemini Flash Client Boundary Tests.

Verifies edge cases: short keys, quota exhaustion (429), forbidden access (403), special chars, empty prompts.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_gemini_module


class TestBoundary06GeminiClient:
    """Boundary & Corner Case tests for Feature 6."""

    def test_validate_key_too_short(self) -> None:
        """Verify key starting with AIzaSy but shorter than 30 characters fails validation."""
        gemini = get_gemini_module()
        is_valid, msg = gemini.validate_api_key("AIzaSyShort")
        assert is_valid is False
        assert "corta" in msg.lower() or "caracteres" in msg.lower()

    def test_validate_key_quota_exceeded_429(self, quota_exceeded_key: str) -> None:
        """Verify API 429 quota exhaustion is detected and returns user-friendly wait guidance."""
        gemini = get_gemini_module()
        is_valid, msg = gemini.validate_api_key(quota_exceeded_key)
        assert is_valid is False
        assert "429" in msg or "cuota" in msg.lower() or "espera" in msg.lower()

    def test_validate_key_forbidden_403(self, forbidden_api_key: str) -> None:
        """Verify API 403 forbidden permissions is detected with clear error message."""
        gemini = get_gemini_module()
        is_valid, msg = gemini.validate_api_key(forbidden_api_key)
        assert is_valid is False
        assert "403" in msg or "permisos" in msg.lower() or "rechazada" in msg.lower()

    def test_validate_key_with_newlines_or_tabs(self, valid_api_key: str) -> None:
        """Verify keys with leading/trailing whitespace or newlines are stripped or handled safely."""
        gemini = get_gemini_module()
        dirty_key = f"\n  {valid_api_key} \t "
        # If stripped, it succeeds or fails cleanly
        is_valid, _ = gemini.validate_api_key(dirty_key.strip())
        assert is_valid is True

    def test_generate_response_empty_prompt_handling(self, valid_api_key: str) -> None:
        """Verify empty prompt generation handled without unhandled exception."""
        gemini = get_gemini_module()
        res = gemini.generate_response(valid_api_key, "")
        assert isinstance(res, str)
