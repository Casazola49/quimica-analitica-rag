"""Tier 1: Feature 7 - Citation-Grounded RAG Engine Tests.

Verifies retrieval from SQLite FTS5 index, prompt orchestration, and exact bibliographic citations.
"""

from __future__ import annotations

import sqlite3
import pytest
from tests.helpers import get_rag_module


class TestFeature07RagEngine:
    """Feature 7: Citation-Grounded RAG Engine verification."""

    def test_query_rag_returns_dict_structure(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify query_rag returns dictionary with answer, citations, and retrieved_chunks."""
        _, db_path = seeded_db
        rag = get_rag_module()

        result = rag.query_rag("¿Cómo se calcula el pH de un buffer?", valid_api_key, db_path=db_path)
        assert isinstance(result, dict)
        assert "answer" in result
        assert "citations" in result
        assert "retrieved_chunks" in result
        assert isinstance(result["answer"], str)
        assert isinstance(result["citations"], list)
        assert isinstance(result["retrieved_chunks"], list)

    def test_query_rag_citations_structure(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify each citation object contains book title, author, edition, chapter, and page."""
        _, db_path = seeded_db
        rag = get_rag_module()

        result = rag.query_rag("Mohr argentometría cloruros", valid_api_key, db_path=db_path)
        assert len(result["citations"]) >= 1
        citation = result["citations"][0]
        assert "book_title" in citation
        assert "author" in citation
        assert "edition" in citation
        assert "chapter" in citation
        assert "page_num" in citation

    def test_query_rag_grounded_answer_includes_citation_text(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify that the generated answer incorporates source citation bracket tags."""
        _, db_path = seeded_db
        rag = get_rag_module()

        result = rag.query_rag("digestión de Ostwald en sulfatos", valid_api_key, db_path=db_path)
        ans = result["answer"]
        assert len(ans) > 50
        # Assert citation notation [Libro: ...] is present in the response
        assert "[Libro:" in ans or "Skoog" in ans or "Cap." in ans

    def test_query_rag_unit_filtering(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify syllabus_unit filter confines retrieved chunks to the specified unit."""
        _, db_path = seeded_db
        rag = get_rag_module()

        result = rag.query_rag("valoración", valid_api_key, syllabus_unit="U7", db_path=db_path)
        for chunk in result["retrieved_chunks"]:
            assert chunk["syllabus_unit"] == "U7"

    def test_query_rag_empty_query_handles_gracefully(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify that an empty query returns a prompt asking for input without crashing."""
        _, db_path = seeded_db
        rag = get_rag_module()

        result = rag.query_rag("", valid_api_key, db_path=db_path)
        assert "answer" in result
        assert len(result["answer"]) > 0
        assert result["retrieved_chunks"] == []
