"""Tier 2: Feature 7 - Citation-Grounded RAG Engine Boundary Tests.

Verifies edge cases: out-of-syllabus queries, zero retrieved chunks, huge query strings, missing DB paths.
"""

from __future__ import annotations

import sqlite3
import pytest
from tests.helpers import get_rag_module


class TestBoundary07Rag:
    """Boundary & Corner Case tests for Feature 7."""

    def test_rag_out_of_syllabus_query_grounds_gracefully(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify queries completely outside syllabus (e.g. quantum chromodynamics) respond gracefully with grounding."""
        _, db_path = seeded_db
        rag = get_rag_module()

        out_of_scope = "¿Cómo funciona la cromodinámica cuántica y el confinamiento de quarks?"
        result = rag.query_rag(out_of_scope, valid_api_key, db_path=db_path)
        assert "answer" in result
        assert len(result["answer"]) > 0
        # The prompt orchestration ensures answers cite course materials or guide back to curriculum
        assert "citations" in result

    def test_rag_zero_retrieved_chunks_fallback_citation(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify query with 0 matching chunks in DB returns answer and fallback citation without crashing."""
        _, db_path = seeded_db
        rag = get_rag_module()

        nonsense_query = "xyzqwerty12345nonexistentterm"
        result = rag.query_rag(nonsense_query, valid_api_key, db_path=db_path)
        assert "answer" in result
        assert len(result["citations"]) >= 1  # Fallback general citation provided

    def test_rag_huge_query_string_safety(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify query string of 5,000 characters is handled without memory error or buffer overflow."""
        _, db_path = seeded_db
        rag = get_rag_module()

        huge_query = "Explica la gravimetría de sulfatos " + ("con BaCl2 y digestión Ostwald " * 150)
        result = rag.query_rag(huge_query, valid_api_key, db_path=db_path)
        assert "answer" in result
        assert len(result["answer"]) > 20

    def test_rag_missing_db_path_handled_safely(self, valid_api_key: str) -> None:
        """Verify passing a non-existent DB path produces clean answer with fallback citations."""
        rag = get_rag_module()
        result = rag.query_rag("Mohr argentometría", valid_api_key, db_path="/nonexistent/db.db")
        assert "answer" in result
        assert "citations" in result

    def test_rag_whitespace_only_query(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Verify whitespace-only query prompts student for input."""
        _, db_path = seeded_db
        rag = get_rag_module()
        result = rag.query_rag("     \n\t   ", valid_api_key, db_path=db_path)
        assert "consulta" in result["answer"].lower() or "ingresa" in result["answer"].lower()
        assert result["retrieved_chunks"] == []
