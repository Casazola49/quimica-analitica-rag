"""Tier 1: Feature 6 - BYOK Gemini Flash Client Tests.

Verifies API key format validation, client instantiation, and streaming/non-streaming generation.
"""

from __future__ import annotations

import types
import pytest
from tests.helpers import get_gemini_module


class TestFeature06GeminiClient:
    """Feature 6: BYOK Gemini Flash Client verification."""

    def test_validate_api_key_valid_format(self, valid_api_key: str) -> None:
        """Verify that a validly formatted AI Studio key passes validation."""
        gemini = get_gemini_module()
        is_valid, msg = gemini.validate_api_key(valid_api_key)
        assert is_valid is True
        assert "válida" in msg.lower() or "conexión" in msg.lower() or "ok" in msg.lower()

    def test_validate_api_key_invalid_prefix_fails(self, invalid_api_key: str) -> None:
        """Verify that a key without 'AIzaSy' prefix fails validation."""
        gemini = get_gemini_module()
        is_valid, msg = gemini.validate_api_key(invalid_api_key)
        assert is_valid is False
        assert "aizasy" in msg.lower()

    def test_validate_api_key_empty_or_whitespace_fails(self) -> None:
        """Verify that empty string or whitespace is rejected."""
        gemini = get_gemini_module()
        is_valid_empty, _ = gemini.validate_api_key("")
        assert is_valid_empty is False

        is_valid_none, _ = gemini.validate_api_key(None)
        assert is_valid_none is False

    def test_generate_response_returns_substantive_text(self, valid_api_key: str) -> None:
        """Verify generate_response produces non-empty chemical text."""
        gemini = get_gemini_module()
        prompt = "¿Cuál es el principio de la gravimetría de sulfatos como BaSO4?"
        response = gemini.generate_response(valid_api_key, prompt)
        assert isinstance(response, str)
        assert len(response.strip()) > 30
        assert "BaSO4" in response or "sulfato" in response.lower() or "gravimetr" in response.lower()

    def test_generate_response_streaming_mode(self, valid_api_key: str) -> None:
        """Verify stream=True yields chunks that reconstruct complete response."""
        gemini = get_gemini_module()
        prompt = "Explica el método de Mohr para cloruros."
        stream = gemini.generate_response(valid_api_key, prompt, stream=True)
        assert isinstance(stream, (types.GeneratorType, list, tuple)) or hasattr(stream, "__iter__")

        chunks = list(stream)
        assert len(chunks) >= 2, "Streaming should yield multiple successive chunks"
        full_text = "".join(chunks)
        assert "Mohr" in full_text or "cloruro" in full_text.lower()
