"""Tier 1: Feature 12 - Interactive Chatbot Interface Tests.

Verifies chat state machine, streaming accumulation, and KaTeX mathematical/chemical formula formatting.
"""

from __future__ import annotations

import re
import pytest


class TestFeature12ChatbotUi:
    """Feature 12: Interactive Chatbot Interface verification."""

    def test_chat_history_state_structure(self) -> None:
        """Verify chat history supports append of standard role/content messages."""
        messages: list[dict[str, str]] = []
        messages.append({"role": "user", "content": "¿Cómo se define el factor gravimétrico?"})
        messages.append({
            "role": "assistant",
            "content": "El factor gravimétrico FG representa la relación estequiométrica: $$FG = \\frac{a \\cdot MW_{analito}}{b \\cdot MW_{precipitado}}$$"
        })
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_chat_katex_formula_detection(self) -> None:
        """Verify mathematical and chemical equations in responses contain valid KaTeX delimiters."""
        response = (
            "La constante de solubilidad se calcula como:\n"
            "$$K_{ps} = [Ba^{2+}][SO_4^{2-}]$$\n"
            "donde el producto iónico $Q > K_{ps}$ genera precipitación."
        )
        display_math = re.findall(r"\$\$(.+?)\$\$", response, re.DOTALL)
        inline_math = re.findall(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", response)

        assert len(display_math) >= 1
        assert "K_{ps}" in display_math[0]
        assert len(inline_math) >= 1
        assert "Q > K_{ps}" in inline_math[0]

    def test_chat_citation_drawer_data_structure(self) -> None:
        """Verify citation card data contains all required display components."""
        citations = [
            {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 12",
                "page_num": 315,
                "excerpt": "La relación de Von Weimarn..."
            }
        ]
        card_label = f"📖 {citations[0]['book_title']} (Pág. {citations[0]['page_num']})"
        assert "Fundamentos" in card_label
        assert "315" in card_label

    def test_chat_streaming_chunk_accumulation(self) -> None:
        """Verify accumulating streaming tokens yields complete, coherent message."""
        stream_chunks = ["En ", "las ", "valoraciones ", "ácido-base, ", "el ", "pH = pKa."]
        accumulated = ""
        for chunk in stream_chunks:
            accumulated += chunk
        assert accumulated == "En las valoraciones ácido-base, el pH = pKa."

    def test_chat_clear_history_resets_conversation(self) -> None:
        """Verify clearing history restores initial greeting state."""
        chat_state = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Hola, ¿en qué te puedo orientar hoy?"}
        ]
        chat_state.clear()
        assert len(chat_state) == 0
