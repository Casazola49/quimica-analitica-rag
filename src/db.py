"""
src/db.py - SQLite FTS5 BM25 Database Engine for Química Analítica Portal

Provides persistent storage and sub-5ms BM25 full-text retrieval for
textbook chunks, syllabus unit mapping, and citation metadata.
"""

from __future__ import annotations

import os
import re
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "data/quimica_analitica.db"

# Informative stopwords in Spanish and English
STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a",
    "en", "para", "por", "con", "son", "es", "se", "que", "cual", "cuales", "como",
    "y", "o", "su", "sus", "the", "of", "in", "and", "or", "to", "for", "is", "are",
    "what", "how"
}

# Maximum unique terms to include in FTS5 query expressions to protect against DoS
MAX_QUERY_TERMS = 30



def get_connection(
    db_path_or_conn: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH,
    read_only: bool = False
) -> sqlite3.Connection:
    """
    Get or create an SQLite connection with optimized PRAGMAs.
    """
    if isinstance(db_path_or_conn, sqlite3.Connection):
        return db_path_or_conn

    db_path = str(db_path_or_conn)
    if db_path != ":memory:":
        if not os.path.exists(db_path) and read_only:
            raise FileNotFoundError(f"Database file not found at: {db_path}")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    if not read_only and db_path != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA temp_store = MEMORY;")
            conn.execute("PRAGMA cache_size = -8000;")  # ~8 MB page cache
        except sqlite3.OperationalError:
            pass
    return conn


def init_db(db_path: Union[str, sqlite3.Connection] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Initialize SQLite schema: books, chunks, and chunks_fts with triggers.
    """
    conn = get_connection(db_path, read_only=False)

    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            author TEXT,
            edition TEXT,
            total_pages INTEGER,
            cover_path TEXT,
            language TEXT DEFAULT 'es',
            is_scanned INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            book_title TEXT NOT NULL,
            author TEXT,
            edition TEXT,
            chapter TEXT,
            page_num INTEGER NOT NULL,
            syllabus_unit TEXT,
            content TEXT NOT NULL,
            token_count INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_book_id ON chunks(book_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_syllabus_unit ON chunks(syllabus_unit);
        CREATE INDEX IF NOT EXISTS idx_chunks_page_num ON chunks(page_num);

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            book_title,
            author,
            edition,
            chapter,
            syllabus_unit,
            tokenize='unicode61'
        );

        -- Synchronization Triggers
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, content, book_title, author, edition, chapter, syllabus_unit)
            VALUES (new.id, new.content, new.book_title, new.author, new.edition, new.chapter, new.syllabus_unit);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            DELETE FROM chunks_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            DELETE FROM chunks_fts WHERE rowid = old.id;
            INSERT INTO chunks_fts(rowid, content, book_title, author, edition, chapter, syllabus_unit)
            VALUES (new.id, new.content, new.book_title, new.author, new.edition, new.chapter, new.syllabus_unit);
        END;
        """)

    return conn


def insert_book(conn: sqlite3.Connection, book_data: Dict[str, Any]) -> int:
    """
    Insert textbook metadata or update existing record on conflict.
    """
    with conn:
        cur = conn.execute("""
            INSERT INTO books (filename, title, author, edition, total_pages, cover_path, language, is_scanned)
            VALUES (:filename, :title, :author, :edition, :total_pages, :cover_path, :language, :is_scanned)
            ON CONFLICT(filename) DO UPDATE SET
                title = excluded.title,
                author = excluded.author,
                edition = excluded.edition,
                total_pages = excluded.total_pages,
                cover_path = excluded.cover_path,
                language = excluded.language,
                is_scanned = excluded.is_scanned
            RETURNING id;
        """, {
            "filename": book_data["filename"],
            "title": book_data["title"],
            "author": book_data.get("author", book_data.get("authors")),
            "edition": book_data.get("edition"),
            "total_pages": book_data.get("total_pages"),
            "cover_path": book_data.get("cover_path"),
            "language": book_data.get("language", "es"),
            "is_scanned": int(book_data.get("is_scanned", 0))
        })
        row = cur.fetchone()
        return row[0] if row else 1


def insert_chunk(
    conn: sqlite3.Connection,
    book_id_or_data: Union[Dict[str, Any], int, str] = None,
    *args,
    **kwargs
) -> int:
    """
    Polymorphic insertion of a single chunk. Supports dictionary input or positional arguments:
    (conn, book_id, title, author, edition, chapter, page_num, syllabus_unit, content)
    """
    if isinstance(book_id_or_data, dict):
        d = book_id_or_data
        book_id = str(d.get("book_id", ""))
        book_title = str(d.get("book_title", d.get("title", "")))
        author = str(d.get("author", d.get("authors", "")))
        edition = str(d.get("edition", ""))
        chapter = str(d.get("chapter", ""))
        page_num = int(d.get("page_num", 1))
        syllabus_unit = str(d.get("syllabus_unit", ""))
        content = str(d.get("content", ""))
        token_count = d.get("token_count", len(content.split()) if content else 0)
    elif "content" in kwargs or len(args) >= 6 or kwargs:
        book_id = str(kwargs.get("book_id", book_id_or_data or ""))
        book_title = str(kwargs.get("title", kwargs.get("book_title", args[0] if len(args) > 0 else "")))
        author = str(kwargs.get("author", args[1] if len(args) > 1 else ""))
        edition = str(kwargs.get("edition", args[2] if len(args) > 2 else ""))
        chapter = str(kwargs.get("chapter", args[3] if len(args) > 3 else ""))
        page_num = int(kwargs.get("page_num", args[4] if len(args) > 4 else 1))
        syllabus_unit = str(kwargs.get("syllabus_unit", args[5] if len(args) > 5 else ""))
        content = str(kwargs.get("content", args[6] if len(args) > 6 else ""))
        token_count = kwargs.get("token_count", len(content.split()) if content else 0)
    else:
        # Positional arguments: (conn, book_id, title, author, edition, chapter, page_num, syllabus_unit, content)
        book_id = str(book_id_or_data)
        book_title = str(args[0]) if len(args) > 0 else ""
        author = str(args[1]) if len(args) > 1 else ""
        edition = str(args[2]) if len(args) > 2 else ""
        chapter = str(args[3]) if len(args) > 3 else ""
        page_num = int(args[4]) if len(args) > 4 else 1
        syllabus_unit = str(args[5]) if len(args) > 5 else ""
        content = str(args[6]) if len(args) > 6 else ""
        token_count = kwargs.get("token_count", len(content.split()) if content else 0)

    with conn:
        cur = conn.execute("""
            INSERT INTO chunks (book_id, book_title, author, edition, chapter, page_num, syllabus_unit, content, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (book_id, book_title, author, edition, chapter, page_num, syllabus_unit, content, token_count))
        return cur.lastrowid


def insert_chunks_batch(
    conn: sqlite3.Connection,
    chunks_list: List[Union[Dict[str, Any], tuple]]
) -> int:
    """
    Batch insert chunks inside a single transaction for maximum speed.
    """
    params = []
    for item in chunks_list:
        if isinstance(item, dict):
            c_text = item.get("content", "")
            t_count = item.get("token_count", len(c_text.split()) if c_text else 0)
            b_id = str(item.get("book_id", ""))
            b_title = str(item.get("book_title", item.get("title", "")))
            author = str(item.get("author", item.get("authors", "")))
            edition = str(item.get("edition", ""))
            chapter = str(item.get("chapter", ""))
            p_num = int(item.get("page_num", 1))
            s_unit = str(item.get("syllabus_unit", ""))
            params.append((b_id, b_title, author, edition, chapter, p_num, s_unit, c_text, t_count))
        else:
            # item is tuple
            if len(item) == 8:
                # (book_id, title, author, edition, chapter, page_num, syllabus_unit, content)
                b_id, b_title, author, edition, chapter, p_num, s_unit, c_text = item
                params.append((str(b_id), str(b_title), str(author), str(edition), str(chapter), int(p_num), str(s_unit), str(c_text), len(str(c_text).split())))
            elif len(item) == 9:
                params.append(item)
            else:
                params.append(item)

    with conn:
        conn.executemany("""
            INSERT INTO chunks (book_id, book_title, author, edition, chapter, page_num, syllabus_unit, content, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, params)
    return len(params)


def sanitize_fts_query(raw_query: Union[str, Any]) -> Tuple[str, str]:
    """
    Safely tokenize user query and produce strict AND and fallback OR expressions.
    Eliminates all FTS5 syntax errors caused by chemical symbols, ion charges, math operators,
    and SQL injection attempts.
    Enforces term deduplication and a 30-term maximum query cap to prevent latency freezes.
    """
    if raw_query is None:
        return ("", "")

    query_str = str(raw_query).strip()
    if not query_str:
        return ("", "")

    # Extract quoted strings and word tokens (including Spanish accents and chemistry alphanumeric)
    tokens = re.findall(r'\"[^\"]+\"|[\wáéíóúÁÉÍÓÚñÑüÜ]+', query_str)
    if not tokens:
        return ("", "")

    quoted = []
    boolean_ops = {"AND", "OR", "NOT"}

    for t in tokens:
        if t.upper() in boolean_ops:
            quoted.append(t.upper())
            continue
        if t.startswith('"') and t.endswith('"'):
            # Strip invalid chars inside phrase
            clean_phrase = re.sub(r'[^a-zA-Z0-9_\u00C0-\u017F\s]', '', t[1:-1]).strip()
            if clean_phrase:
                quoted.append(f'"{clean_phrase}"')
        else:
            # Individual token
            clean_token = re.sub(r'[^a-zA-Z0-9_\u00C0-\u017F]', '', t).strip()
            if clean_token:
                quoted.append(f'"{clean_token}"')

    # If query was solely operators or empty
    meaningful = [q for q in quoted if q not in boolean_ops]
    if not meaningful:
        return ("", "")

    # Check if user explicitly wrote boolean operators
    has_explicit_bool = any(q in boolean_ops for q in quoted)
    if has_explicit_bool:
        # Build query preserving valid operator placements and cap total meaningful terms
        expr_parts = []
        meaningful_count = 0
        for q in quoted:
            if q in boolean_ops:
                if expr_parts and expr_parts[-1] not in boolean_ops:
                    expr_parts.append(q)
            else:
                if meaningful_count >= MAX_QUERY_TERMS:
                    break
                meaningful_count += 1
                expr_parts.append(q)
        # Strip trailing boolean operator
        while expr_parts and expr_parts[-1] in boolean_ops:
            expr_parts.pop()
        if expr_parts:
            combined = " ".join(expr_parts)
            return (combined, combined)
        return ("", "")

    # Standard query without explicit operators: filter stopwords if other terms exist
    filtered = [q for q in meaningful if q.strip('"').lower() not in STOPWORDS]
    target = filtered if filtered else meaningful

    # Deduplicate terms while preserving order (case-insensitive deduplication)
    seen = set()
    deduped = []
    for term in target:
        key = term.strip('"').lower()
        if key not in seen:
            seen.add(key)
            deduped.append(term)

    # Enforce term count cap (maximum 30 unique terms)
    capped = deduped[:MAX_QUERY_TERMS]

    query_and = " AND ".join(capped)
    query_or = " OR ".join(capped)
    return (query_and, query_or)


def search_chunks(
    query: Union[str, Any],
    syllabus_unit: Optional[Union[str, Any]] = None,
    limit: Union[int, Any] = 5,
    db_path: str = DEFAULT_DB_PATH,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve chunks using SQLite FTS5 BM25 ranking with snippet and citation metadata.
    Accepts an existing connection or opens one to db_path.
    Safely coerces query, syllabus_unit, and limit parameters.
    """
    if query is None:
        return []
    query_str = str(query).strip()
    if not query_str:
        return []

    try:
        limit_val = int(limit)
        if limit_val <= 0:
            return []
        limit_val = min(limit_val, 100)
    except (ValueError, TypeError):
        limit_val = 5

    query_and, query_or = sanitize_fts_query(query_str)
    if not query_and:
        return []

    should_close = False
    if conn is None:
        if db_path != ":memory:" and not os.path.exists(db_path):
            return []
        try:
            conn = get_connection(db_path, read_only=False)
            should_close = True
        except FileNotFoundError:
            return []

    try:
        sql = """
        SELECT 
            c.id,
            c.book_id,
            c.book_title,
            c.author,
            c.edition,
            c.chapter,
            c.page_num,
            c.syllabus_unit,
            c.content,
            snippet(chunks_fts, 0, '<b>', '</b>', '...', 25) AS snippet,
            bm25(chunks_fts) AS raw_score
        FROM chunks_fts f
        JOIN chunks c ON f.rowid = c.id
        WHERE chunks_fts MATCH :match_query
          AND (:unit IS NULL OR c.syllabus_unit = :unit OR c.syllabus_unit LIKE :unit_like)
        ORDER BY raw_score ASC
        LIMIT :limit;
        """

        unit_filter = None
        if syllabus_unit is not None:
            unit_str = str(syllabus_unit).strip()
            if unit_str:
                unit_filter = unit_str
        unit_like = f"%{unit_filter}%" if unit_filter else None

        cursor = conn.execute(sql, {
            "match_query": query_and,
            "unit": unit_filter,
            "unit_like": unit_like,
            "limit": limit_val
        })
        rows = cursor.fetchall()

        # Fallback to OR query if fewer than limit results found
        if len(rows) < limit_val and query_or != query_and:
            cursor = conn.execute(sql, {
                "match_query": query_or,
                "unit": unit_filter,
                "unit_like": unit_like,
                "limit": limit_val
            })
            rows = cursor.fetchall()

        results = []
        for r in rows:
            raw_s = float(r["raw_score"])
            b_title = str(r["book_title"] or "")
            author = str(r["author"] or "")
            edition = str(r["edition"] or "")
            chapter = str(r["chapter"] or "")
            page_num = int(r["page_num"])

            citation = f"{b_title}"
            if author or edition:
                meta = ", ".join(filter(None, [author, edition]))
                citation += f" ({meta})"
            if chapter:
                citation += f", {chapter}"
            citation += f", pág. {page_num}"

            results.append({
                "id": int(r["id"]),
                "book_id": str(r["book_id"] or ""),
                "book_title": b_title,
                "author": author,
                "edition": edition,
                "chapter": chapter,
                "page_num": page_num,
                "syllabus_unit": str(r["syllabus_unit"] or ""),
                "content": str(r["content"] or ""),
                "snippet": str(r["snippet"] or ""),
                "score": round(abs(raw_s), 4),
                "raw_bm25": raw_s,
                "citation": citation
            })
        return results
    except sqlite3.OperationalError as e:
        logger.warning(f"FTS search error for query '{query_str}': {e}")
        return []
    finally:
        if should_close and conn:
            conn.close()


def get_all_books(
    db_path: str = DEFAULT_DB_PATH,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve all textbooks for catalog showcase and WhatsApp button generation.
    """
    should_close = False
    if conn is None:
        if db_path != ":memory:" and not os.path.exists(db_path):
            return []
        try:
            conn = get_connection(db_path, read_only=False)
            should_close = True
        except FileNotFoundError:
            return []

    try:
        cursor = conn.execute("""
            SELECT id, filename, title, author, edition, total_pages, cover_path, language, is_scanned
            FROM books
            ORDER BY id ASC;
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        if should_close and conn:
            conn.close()


def get_book_by_id(
    book_id: Union[int, str],
    db_path: str = DEFAULT_DB_PATH,
    conn: Optional[sqlite3.Connection] = None
) -> Optional[Dict[str, Any]]:
    """
    Lookup a textbook by primary key ID or filename stem.
    """
    should_close = False
    if conn is None:
        if db_path != ":memory:" and not os.path.exists(db_path):
            return None
        try:
            conn = get_connection(db_path, read_only=False)
            should_close = True
        except FileNotFoundError:
            return None

    try:
        cur = conn.execute("SELECT * FROM books WHERE id = ? OR filename LIKE ?;", (book_id, f"{book_id}%"))
        row = cur.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        if should_close and conn:
            conn.close()


def get_chunk_count(
    db_path: str = DEFAULT_DB_PATH,
    conn: Optional[sqlite3.Connection] = None
) -> int:
    """
    Return total count of indexed chunks.
    """
    should_close = False
    if conn is None:
        if db_path != ":memory:" and not os.path.exists(db_path):
            return 0
        try:
            conn = get_connection(db_path, read_only=False)
            should_close = True
        except FileNotFoundError:
            return 0

    try:
        cur = conn.execute("SELECT COUNT(*) FROM chunks;")
        return cur.fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        if should_close and conn:
            conn.close()


def get_chunks_by_unit(
    syllabus_unit: Union[str, Any],
    limit: Union[int, Any] = 50,
    db_path: str = DEFAULT_DB_PATH,
    conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve chunks belonging to a specific syllabus unit (for exam generator or tutor).
    Defensively coerces syllabus_unit and limit.
    """
    if syllabus_unit is None:
        return []
    unit_str = str(syllabus_unit).strip()
    if not unit_str:
        return []

    try:
        limit_val = int(limit)
        if limit_val <= 0:
            return []
        limit_val = min(limit_val, 500)
    except (ValueError, TypeError):
        limit_val = 50

    should_close = False
    if conn is None:
        if db_path != ":memory:" and not os.path.exists(db_path):
            return []
        try:
            conn = get_connection(db_path, read_only=False)
            should_close = True
        except FileNotFoundError:
            return []

    try:
        sql = """
            SELECT c.id, c.book_id, c.book_title, c.author, c.edition,
                   c.chapter, c.page_num, c.syllabus_unit, c.content, c.token_count
            FROM chunks c
            WHERE c.syllabus_unit = ? OR c.syllabus_unit LIKE ?
            ORDER BY c.page_num ASC
            LIMIT ?;
        """
        cur = conn.execute(sql, (unit_str, f"%{unit_str}%", limit_val))
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        if should_close and conn:
            conn.close()


def rebuild_fts_index(conn: sqlite3.Connection) -> None:
    """
    Rebuild chunks_fts virtual index from relational chunks table.
    """
    with conn:
        conn.execute("DELETE FROM chunks_fts;")
        conn.execute("""
            INSERT INTO chunks_fts (rowid, content, book_title, author, edition, chapter, syllabus_unit)
            SELECT id, content, book_title, author, edition, chapter, syllabus_unit
            FROM chunks;
        """)
