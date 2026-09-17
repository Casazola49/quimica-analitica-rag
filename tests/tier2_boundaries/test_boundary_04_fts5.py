"""Tier 2: Feature 4 - SQLite FTS5 BM25 Database Boundary Tests.

Verifies edge cases: empty search queries, SQL injection resilience, FTS5 operator chars, and Spanish accents.
"""

from __future__ import annotations

import sqlite3
import pytest
from tests.helpers import get_db_module


class TestBoundary04Fts5:
    """Boundary & Corner Case tests for Feature 4."""

    def test_fts5_empty_query_returns_empty_list(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify empty or pure whitespace query returns empty list without raising sqlite3.OperationalError."""
        conn, db_path = seeded_db
        db = get_db_module()
        assert db.search_chunks("", db_path=db_path, conn=conn) == []
        assert db.search_chunks("   ", db_path=db_path, conn=conn) == []
        assert db.search_chunks("!@#$%^&*()", db_path=db_path, conn=conn) == []

    def test_fts5_sql_injection_resilience(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify malicious SQL injection string is safely sanitized and executed as text."""
        conn, db_path = seeded_db
        db = get_db_module()
        malicious_query = "' OR 1=1; DROP TABLE chunks; --"
        # Must execute cleanly without error and without dropping table
        results = db.search_chunks(malicious_query, db_path=db_path, conn=conn)
        assert isinstance(results, list)

        # Verify table still exists and data intact
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM chunks")
        count = cursor.fetchone()[0]
        assert count > 0, "Table 'chunks' must remain intact and not dropped"

    def test_fts5_special_operator_syntax(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify FTS5 special boolean operators (AND, OR, NOT, *, quotes) do not trigger syntax errors."""
        conn, db_path = seeded_db
        db = get_db_module()
        queries = [
            "BaSO4 AND Ostwald",
            "Mohr OR Volhard",
            "EDTA NOT calcio",
            '"precipitado rojo"',
            "gravim*",
            "((((titulación))))"
        ]
        for q in queries:
            res = db.search_chunks(q, db_path=db_path, conn=conn)
            assert isinstance(res, list)

    def test_fts5_nonexistent_unit_filter(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify filtering by non-existent syllabus unit returns [] without error."""
        conn, db_path = seeded_db
        db = get_db_module()
        results = db.search_chunks("sulfato", syllabus_unit="U999", db_path=db_path, conn=conn)
        assert results == []

    def test_fts5_accent_insensitive_matching(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify search matches words with or without Spanish diacritical accents."""
        conn, db_path = seeded_db
        db = get_db_module()

        # Seeded chunk has 'valoración' and 'ácido'
        res_unaccented = db.search_chunks("acido valoracion", db_path=db_path, conn=conn)
        res_accented = db.search_chunks("ácido valoración", db_path=db_path, conn=conn)

        assert len(res_unaccented) >= 1
        assert len(res_accented) >= 1
