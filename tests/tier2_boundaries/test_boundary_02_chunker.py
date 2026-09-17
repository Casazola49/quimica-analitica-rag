"""Tier 2: Feature 2 - Textbook Chunker & Metadata Boundary Tests.

Verifies edge cases: 0-char string, monolithic words, unicode formulas, negative/equal overlap.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_ingestion_module


class TestBoundary02Chunker:
    """Boundary & Corner Case tests for Feature 2."""

    def test_chunk_zero_char_string(self) -> None:
        """Verify 0-length string produces empty chunk list."""
        ingestion = get_ingestion_module()
        chunks = ingestion.chunk_text("", page_num=1)
        assert chunks == []

    def test_chunk_huge_single_word(self) -> None:
        """Verify massive unbroken string longer than chunk_size is split safely."""
        ingestion = get_ingestion_module()
        monolithic_word = "A" * 3500
        chunks = ingestion.chunk_text(monolithic_word, page_num=1, chunk_size=1000, overlap=100)
        assert len(chunks) >= 4
        # Reassembled length accounting for overlaps
        assert all(len(c["content"]) <= 1000 for c in chunks)

    def test_chunk_special_unicode_chemical_symbols(self) -> None:
        """Verify chunks preserve chemical arrows, subscripts, and Greek symbols without corruption."""
        ingestion = get_ingestion_module()
        chem_text = (
            "Equilibrio: SO₄²⁻ + Ba²⁺ ⇌ BaSO₄(s). "
            "Fracción condicional: α₄ = Ka₁Ka₂Ka₃Ka₄ / [H⁺]⁴ + ... "
            "Ecuación de Nernst: E = E° - (0.0592/n)·log(Q)"
        )
        chunks = ingestion.chunk_text(chem_text, page_num=42, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        content = chunks[0]["content"]
        assert "⇌" in content
        assert "α₄" in content
        assert "SO₄²⁻" in content

    def test_chunk_negative_overlap_rejected(self) -> None:
        """Verify negative overlap raises ValueError."""
        ingestion = get_ingestion_module()
        with pytest.raises(ValueError):
            ingestion.chunk_text("Texto de prueba", page_num=1, chunk_size=500, overlap=-20)

    def test_chunk_overlap_equal_or_greater_than_size_rejected(self) -> None:
        """Verify overlap >= chunk_size raises ValueError to prevent infinite loops."""
        ingestion = get_ingestion_module()
        with pytest.raises(ValueError):
            ingestion.chunk_text("Texto de prueba", page_num=1, chunk_size=500, overlap=500)
        with pytest.raises(ValueError):
            ingestion.chunk_text("Texto de prueba", page_num=1, chunk_size=500, overlap=600)
