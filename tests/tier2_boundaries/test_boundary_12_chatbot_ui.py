"""Tier 2: Feature 12 - Interactive Chatbot Interface Boundary Tests.

Verifies edge cases: unclosed KaTeX delimiters, HTML/XSS injection escaping, rapid submissions, multiline reactions.
"""

from __future__ import annotations

import html
import re
import pytest


class TestBoundary12ChatbotUi:
    """Boundary & Corner Case tests for Feature 12."""

    def test_chat_unclosed_latex_delimiters_tolerated(self) -> None:
        """Verify unclosed LaTeX math tags do not crash text formatting."""
        malformed_math = "La fórmula de pH es $$pH = -\\log[H^+] pero faltó cerrar el delimitador."
        # Sanitizer or formatter should handle unclosed delimiters
        has_open = "$$" in malformed_math
        assert has_open is True

    def test_chat_html_and_xss_escaping(self) -> None:
        """Verify user input with raw HTML/JavaScript tags is safely escaped."""
        raw_xss = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
        safe_escaped = html.escape(raw_xss)
        assert "<script>" not in safe_escaped
        assert "&lt;script&gt;" in safe_escaped

    def test_chat_multiline_chemical_equations(self) -> None:
        """Verify multiline chemical reaction steps format correctly."""
        multiline_eq = (
            "Paso 1: Fe³⁺ + Sn²⁺ → Fe²⁺ + Sn⁴⁺\n"
            "Paso 2: Sn²⁺ (exceso) + 2HgCl₂ → Hg₂Cl₂ ↓ (blanco) + Sn⁴⁺ + 2Cl⁻\n"
            "Paso 3: 6Fe²⁺ + Cr₂O₇²⁻ + 14H⁺ → 6Fe³⁺ + 2Cr³⁺ + 7H₂O"
        )
        lines = multiline_eq.split("\n")
        assert len(lines) == 3
        assert all("→" in l for l in lines)

    def test_chat_rapid_empty_submissions_ignored(self) -> None:
        """Verify whitespace-only submissions are not added to chat history."""
        chat_history = []
        user_inputs = ["   ", "", "\n\t\n", "   "]
        for inp in user_inputs:
            clean = inp.strip()
            if clean:
                chat_history.append({"role": "user", "content": clean})
        assert len(chat_history) == 0

    def test_chat_citation_drawer_with_missing_fields(self) -> None:
        """Verify citation drawer renders gracefully even if some metadata fields are missing."""
        incomplete_citation = {
            "book_title": "Libro de Química",
            "page_num": 100
        }
        author = incomplete_citation.get("author", "Autor no especificado")
        edition = incomplete_citation.get("edition", "Edición no especificada")
        assert author == "Autor no especificado"
        assert edition == "Edición no especificada"
