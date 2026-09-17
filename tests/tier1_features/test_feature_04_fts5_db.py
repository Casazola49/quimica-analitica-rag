"""Tier 1: Feature 4 - SQLite FTS5 BM25 Database Tests.

Verifies SQLite FTS5 disk-backed index, BM25 relevance scoring, and curriculum filtering.
"""

from __future__ import annotations

import sqlite3
import pytest
from tests.helpers import get_db_module


class TestFeature04Fts5Db:
    """Feature 4: SQLite FTS5 BM25 Search Database verification."""

    def test_init_db_creates_tables_and_fts5_index(self) -> None:
        """Verify init_db initializes 'chunks' table and 'chunks_fts' virtual table."""
        db = get_db_module()
        conn = db.init_db(":memory:")
        assert isinstance(conn, sqlite3.Connection)

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "chunks" in tables, "Table 'chunks' must be created"
        assert "chunks_fts" in tables, "FTS5 virtual table 'chunks_fts' must be created"
        conn.close()

    def test_insert_chunk_stores_and_indexes_record(self) -> None:
        """Verify inserting a chunk returns a valid ID and populates FTS5 index."""
        db = get_db_module()
        conn = db.init_db(":memory:")

        chunk_id = db.insert_chunk(
            conn=conn,
            book_id="skoog_9ed_es",
            title="Fundamentos de Química Analítica",
            author="Douglas A. Skoog",
            edition="9ª Edición",
            chapter="Capítulo 12",
            page_num=315,
            syllabus_unit="U3",
            content="La digestión de Ostwald mejora la pureza del precipitado de BaSO4."
        )
        assert isinstance(chunk_id, int)
        assert chunk_id > 0

        # Verify FTS index holds content
        res = db.search_chunks("Ostwald BaSO4", conn=conn)
        assert len(res) >= 1
        assert res[0]["id"] == chunk_id
        conn.close()

    def test_search_chunks_bm25_ranking(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify search_chunks returns results ranked by relevance."""
        conn, db_path = seeded_db
        db = get_db_module()

        results = db.search_chunks("Mohr cromato plata", db_path=db_path, conn=conn)
        assert len(results) >= 1
        top_match = results[0]
        assert "Mohr" in top_match["content"]
        assert top_match["syllabus_unit"] == "U5"
        assert "score" in top_match
        assert isinstance(top_match["score"], float)

    def test_search_chunks_syllabus_unit_filtering(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify filtering search results by syllabus unit."""
        conn, db_path = seeded_db
        db = get_db_module()

        # Query matches both U3 (Skoog) and U6 (Aguilar), filter by U6
        results = db.search_chunks("valoraciones", syllabus_unit="U6", db_path=db_path, conn=conn)
        for r in results:
            assert r["syllabus_unit"] == "U6", f"Expected syllabus_unit U6, got {r['syllabus_unit']}"

    def test_search_chunks_returns_complete_citation_metadata(self, seeded_db: tuple[sqlite3.Connection, str]) -> None:
        """Verify all fields required for exact academic citations are present."""
        conn, db_path = seeded_db
        db = get_db_module()

        results = db.search_chunks("EDTA quelato", db_path=db_path, conn=conn)
        assert len(results) >= 1
        chunk = results[0]

        required_keys = ["id", "book_title", "author", "edition", "chapter", "page_num", "syllabus_unit", "content", "score"]
        for key in required_keys:
            assert key in chunk, f"Missing required citation metadata key: '{key}'"
            assert chunk[key] is not None
