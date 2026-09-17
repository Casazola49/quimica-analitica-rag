"""Tier 2: Feature 14 - Textbook Showcase & WhatsApp Links Boundary Tests.

Verifies edge cases: formatted phone numbers, empty messages, 500-char book titles, chemical formulas in URLs.
"""

from __future__ import annotations

import re
import urllib.parse
import pytest
from tests.helpers import get_ui_module


class TestBoundary14Whatsapp:
    """Boundary & Corner Case tests for Feature 14."""

    def test_whatsapp_phone_with_complex_formatting(self) -> None:
        """Verify phone with international plus, parentheses, and dashes is cleaned to digits."""
        ui = get_ui_module()
        dirty_phone = "+591 (4) 425-6789 ext 10"
        url = ui.generate_whatsapp_url(dirty_phone, "Hola")
        # Should strip non-digit characters
        clean_match = re.search(r"https:\/\/wa\.me\/(\d+)", url)
        assert clean_match is not None
        assert clean_match.group(1).isdigit()

    def test_whatsapp_empty_message_produces_valid_link(self) -> None:
        """Verify empty message generates a valid redirect URL without query crash."""
        ui = get_ui_module()
        url = ui.generate_whatsapp_url("59170000000", "")
        assert url.startswith("https://wa.me/59170000000?text=")

    def test_whatsapp_very_long_book_title(self) -> None:
        """Verify extremely long book title (500 chars) is safely encoded."""
        ui = get_ui_module()
        long_title = "Tratado Exhaustivo de Métodos Analíticos Cuantitativos y Electroquímica Avanzada " * 10
        msg = ui.format_book_request_message(long_title)
        url = ui.generate_whatsapp_url("59170000000", msg)

        # Parse back and assert integrity
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        assert long_title in params["text"][0]

    def test_whatsapp_chemical_subscripts_and_formulas_in_url(self) -> None:
        """Verify chemical formulas (H2SO4, BaSO4, KMnO4) encode cleanly into URL query string."""
        ui = get_ui_module()
        msg = "Solicitud de guía para determinación de SO4(2-) como BaSO4 con H2SO4 y KMnO4."
        url = ui.generate_whatsapp_url("59170000000", msg)
        assert "%20" in url or "+" in url
        assert "SO4" in url

    def test_whatsapp_newline_characters_encoded_as_percent_0a(self) -> None:
        """Verify multiline message formats newlines as %0A for WhatsApp formatting."""
        ui = get_ui_module()
        multiline_msg = "Línea 1\nLínea 2\nLínea 3"
        url = ui.generate_whatsapp_url("59170000000", multiline_msg)
        assert "%0A" in url
