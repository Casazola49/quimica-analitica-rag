"""Tier 1: Feature 2 - Textbook Chunker & Metadata Tagging Tests.

Verifies text chunking with sliding-window overlap and complete bibliographic/syllabus metadata.
"""

from __future__ import annotations

import pytest
from tests.helpers import get_ingestion_module


class TestFeature02ChunkerMetadata:
    """Feature 2: Textbook Chunker & Metadata Tagging verification."""

    def test_chunk_text_splits_long_content(self) -> None:
        """Verify that text longer than chunk_size is split into multiple chunks."""
        ingestion = get_ingestion_module()
        long_text = "Química Analítica Cuantitativa. " * 100  # ~3200 characters
        metadata = {
            "book_id": "skoog_9ed_es",
            "title": "Fundamentos de Química Analítica",
            "author": "Douglas A. Skoog",
            "edition": "9ª Edición",
            "chapter": "Capítulo 12",
            "syllabus_unit": "U3"
        }

        chunks = ingestion.chunk_text(long_text, page_num=315, metadata=metadata, chunk_size=1000, overlap=150)
        assert len(chunks) >= 3, f"Expected at least 3 chunks for 3200 chars, got {len(chunks)}"

    def test_chunk_text_preserves_metadata(self) -> None:
        """Verify that all bibliographic and curriculum metadata fields are retained on each chunk."""
        ingestion = get_ingestion_module()
        sample_text = "La determinación de sulfato se basa en la precipitación de BaSO4."
        metadata = {
            "book_id": "skoog_9ed_es",
            "title": "Fundamentos de Química Analítica",
            "author": "Douglas A. Skoog",
            "edition": "9ª Edición",
            "chapter": "Capítulo 12",
            "syllabus_unit": "U3"
        }

        chunks = ingestion.chunk_text(sample_text, page_num=316, metadata=metadata, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        c = chunks[0]
        assert c["book_id"] == "skoog_9ed_es"
        assert c["book_title"] == "Fundamentos de Química Analítica"
        assert c["author"] == "Douglas A. Skoog"
        assert c["edition"] == "9ª Edición"
        assert c["chapter"] == "Capítulo 12"
        assert c["syllabus_unit"] == "U3"
        assert c["page_num"] == 316
        assert c["content"] == sample_text

    def test_chunk_text_overlap_continuity(self) -> None:
        """Verify that adjacent chunks overlap as specified."""
        ingestion = get_ingestion_module()
        text = "0123456789" * 30  # 300 characters
        chunks = ingestion.chunk_text(text, page_num=1, chunk_size=100, overlap=20)
        assert len(chunks) >= 3

        # Chunk 0 ends at index 100, Chunk 1 starts at index 80
        tail_of_c0 = chunks[0]["content"][-20:]
        head_of_c1 = chunks[1]["content"][:20]
        assert tail_of_c0 == head_of_c1, "Adjacent chunks must overlap precisely by the overlap length"

    def test_chunk_text_chunk_index_ordering(self) -> None:
        """Verify that chunk_index is sequential and 0-indexed."""
        ingestion = get_ingestion_module()
        text = "Palabra clave de química. " * 80
        chunks = ingestion.chunk_text(text, page_num=5, chunk_size=400, overlap=50)
        indices = [c["chunk_index"] for c in chunks]
        expected_indices = list(range(len(chunks)))
        assert indices == expected_indices, f"Expected indices {expected_indices}, got {indices}"

    def test_chunk_text_empty_input_returns_empty_list(self) -> None:
        """Verify that empty string produces an empty chunk list."""
        ingestion = get_ingestion_module()
        assert ingestion.chunk_text("", page_num=1) == []
        assert ingestion.chunk_text(None, page_num=1) == []
