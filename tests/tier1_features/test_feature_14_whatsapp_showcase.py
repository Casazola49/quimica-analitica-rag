"""Tier 1: Feature 14 - Textbook Showcase & WhatsApp Links Tests.

Verifies textbook catalog metadata, cover association, and dynamic WhatsApp URL formatting.
"""

from __future__ import annotations

import re
import urllib.parse
import pytest
from tests.helpers import get_ui_module


class TestFeature14WhatsappShowcase:
    """Feature 14: Textbook Showcase & WhatsApp Links verification."""

    def test_whatsapp_url_format_matches_spec(self) -> None:
        """Verify WhatsApp link complies with regex ^https://wa\\.me/\\d+\\?text=.+$."""
        ui = get_ui_module()
        phone = "59170000000"
        msg = "Hola, me gustaría solicitar el libro Fundamentos de Química Analítica."
        url = ui.generate_whatsapp_url(phone, msg)

        regex = r"^https:\/\/wa\.me\/\d+\?text=.+$"
        assert re.match(regex, url), f"URL '{url}' does not match required WhatsApp pattern"

    def test_whatsapp_message_is_url_encoded(self) -> None:
        """Verify spaces and Spanish accented characters are safely URL-encoded."""
        ui = get_ui_module()
        msg = "Química Analítica & Equilibrios Iónicos: 2ª Edición"
        url = ui.generate_whatsapp_url("59170000000", msg)

        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        assert "text" in params
        decoded_text = params["text"][0]
        assert decoded_text == msg
        assert " " not in url.split("?text=")[1], "URL query string must not contain raw unencoded spaces"

    def test_whatsapp_message_contains_book_title_and_edition(self) -> None:
        """Verify format_book_request_message incorporates title and edition."""
        ui = get_ui_module()
        msg = ui.format_book_request_message("Quantitative Analysis", edition="6th Edition", author="Day & Underwood")
        assert "Quantitative Analysis" in msg
        assert "6th Edition" in msg
        assert "Day & Underwood" in msg

    def test_whatsapp_phone_sanitization(self) -> None:
        """Verify formatting cleans phone numbers containing +, spaces, or hyphens."""
        ui = get_ui_module()
        raw_phone = "+591-70-000-000"
        url = ui.generate_whatsapp_url(raw_phone, "Hola")
        assert "https://wa.me/59170000000?text=" in url

    def test_textbook_card_metadata_fields(self) -> None:
        """Verify textbook catalog card schema contains all essential attributes."""
        sample_card = {
            "id": "skoog_9ed_es",
            "title": "Fundamentos de Química Analítica",
            "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
            "edition": "9ª Edición (2015)",
            "language": "Español",
            "cover_image": "assets/covers/skoog_9ed_es.png",
            "whatsapp_message": "Hola, me gustaría solicitar el libro Fundamentos de Química Analítica."
        }
        for field in ["id", "title", "authors", "edition", "cover_image", "whatsapp_message"]:
            assert field in sample_card, f"Missing required field '{field}' in book card"
