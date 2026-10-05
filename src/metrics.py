"""
src/metrics.py - Anonymous usage metrics for the instructor-facing report.

The question a department keeps asking is "does this actually help, and where do
students struggle?". Answering it needs evidence, and collecting that evidence
about students carries real obligations. The design rule here is simple:

    Never store a student's words, their key, or anything that identifies them.

What is recorded is a shape, not content: when a question happened, which unit
was searched, how much material came back, how many sources were cited, whether
a quota or saturation warning fired, and how long the question was. From those
alone you can build the per-unit and per-source tables an instructor needs.

Question text is deliberately NOT stored and not hashed. A hash of a short
question is trivially reversible by brute-forcing common phrasings, so hashing
would be storage with extra steps.

The database lives beside the portal at data/usage_metrics.db and is
git-ignored, so usage data never enters version control. On Streamlit Cloud the
filesystem is ephemeral and resets on redeploy, which makes these metrics
session-scoped there; run the portal locally or on a persistent host for a
longer window.
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "usage_metrics.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT    NOT NULL,
    day            TEXT NOT NULL,
    unit           TEXT,
    unit_source    TEXT,
    question_chars INTEGER,
    chunks         INTEGER,
    citations      INTEGER,
    sources        INTEGER,
    model          TEXT,
    outcome        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_day  ON query_events(day);
CREATE INDEX IF NOT EXISTS idx_events_unit ON query_events(unit);
"""

# Outcomes a query can end in. Kept closed so the aggregate report has a fixed
# vocabulary instead of free text creeping in.
OUTCOME_OK = "ok"
OUTCOME_OFFLINE = "offline"
OUTCOME_QUOTA = "quota"
OUTCOME_KEY = "key_rejected"
OUTCOME_ERROR = "error"


def _ensure_parent(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def collection_enabled() -> bool:
    """
    Whether anonymous metrics collection is switched on.

    Defaults to enabled unless ``METRICS_DISABLED`` is set, so the instructor
    can turn it off from the environment without a code change.
    """
    return str(os.environ.get("METRICS_DISABLED", "")).strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }


def record_query_event(
    unit: Optional[str] = None,
    unit_source: str = "unknown",
    question_chars: int = 0,
    chunks: int = 0,
    citations: int = 0,
    sources: int = 0,
    model: Optional[str] = None,
    outcome: str = OUTCOME_OK,
    db_path: Optional[Path] = None,
) -> bool:
    """
    Records one anonymous query event.

    The caller passes counts and a unit id. Nothing here receives, stores or
    derives the student's question text, their API key, or their answer.

    Args:
        unit: Syllabus unit that was searched, or None when unfiltered.
        unit_source: How the unit was chosen: "inferred", "selected" or "none".
        question_chars: Length of the question, used only as a size bucket.
        chunks: How many chunks the retriever returned.
        citations: How many citations the answer carried.
        sources: How many distinct books those citations came from.
        model: Which model served the answer, or None offline.
        outcome: One of the OUTCOME_* constants.
        db_path: Override for the metrics database, used by tests.

    Returns:
        True when the event was stored, False when collection is disabled or the
        write failed. Never raises: losing a metric must not break a student's
        question.
    """
    if not collection_enabled():
        return False
    path = Path(db_path or DEFAULT_DB_PATH)
    try:
        _ensure_parent(path)
        now = datetime.now(timezone.utc)
        with _connect(path) as conn:
            conn.execute(
                "INSERT INTO query_events "
                "(occurred_at, day, unit, unit_source, question_chars, "
                " chunks, citations, sources, model, outcome) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    now.strftime("%Y-%m-%d"),
                    unit,
                    unit_source,
                    max(0, int(question_chars or 0)),
                    max(0, int(chunks or 0)),
                    max(0, int(citations or 0)),
                    max(0, int(sources or 0)),
                    model,
                    outcome,
                ),
            )
        return True
    except Exception:
        return False


def _query(db_path: Path, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    try:
        _ensure_parent(db_path)
        with _connect(db_path) as conn:
            return list(conn.execute(sql, params).fetchall())
    except Exception:
        return []


def total_queries(db_path: Optional[Path] = None) -> int:
    """Total recorded events."""
    path = Path(db_path or DEFAULT_DB_PATH)
    rows = _query(path, "SELECT COUNT(*) AS n FROM query_events")
    return int(rows[0]["n"]) if rows else 0


def queries_by_unit(db_path: Optional[Path] = None) -> list[tuple[str, int]]:
    """Events grouped by unit, most asked first."""
    path = Path(db_path or DEFAULT_DB_PATH)
    rows = _query(
        path,
        "SELECT COALESCE(unit,'sin unidad') AS unit, COUNT(*) AS n "
        "FROM query_events GROUP BY unit ORDER BY n DESC",
    )
    return [(str(r["unit"]), int(r["n"])) for r in rows]


def queries_by_day(db_path: Optional[Path] = None) -> list[tuple[str, int]]:
    """Events grouped by UTC day, oldest first."""
    path = Path(db_path or DEFAULT_DB_PATH)
    rows = _query(
        path,
        "SELECT day, COUNT(*) AS n FROM query_events GROUP BY day ORDER BY day ASC",
    )
    return [(str(r["day"]), int(r["n"])) for r in rows]


def outcomes_breakdown(db_path: Optional[Path] = None) -> list[tuple[str, int]]:
    """Events grouped by outcome, so quota problems are visible to the instructor."""
    path = Path(db_path or DEFAULT_DB_PATH)
    rows = _query(
        path,
        "SELECT outcome, COUNT(*) AS n FROM query_events GROUP BY outcome ORDER BY n DESC",
    )
    return [(str(r["outcome"]), int(r["n"])) for r in rows]


def source_usage(db_path: Optional[Path] = None) -> list[tuple[str, int]]:
    """
    Which books the answers actually leaned on, from the citation totals.

    Derived from the aggregate counts rather than from stored citations: the
    metrics table holds no book names of its own, and summing `sources` is enough
    to show which textbooks carry the course.
    """
    path = Path(db_path or DEFAULT_DB_PATH)
    rows = _query(
        path,
        "SELECT SUM(sources) AS total_sources, SUM(citations) AS total_citations, "
        "COUNT(*) AS answers FROM query_events",
    )
    if not rows or not rows[0]["answers"]:
        return []
    return [
        ("respuestas", int(rows[0]["answers"])),
        ("citas totales", int(rows[0]["total_citations"] or 0)),
        ("libros distintos citados (suma)", int(rows[0]["total_sources"] or 0)),
    ]


def average_citations(db_path: Optional[Path] = None) -> float:
    """Mean number of citations per answer, rounded to one decimal."""
    path = Path(db_path or DEFAULT_DB_PATH)
    rows = _query(
        path,
        "SELECT AVG(citations) AS avg_citations FROM query_events WHERE outcome = 'ok'",
    )
    if not rows or rows[0]["avg_citations"] is None:
        return 0.0
    return round(float(rows[0]["avg_citations"]), 1)


def export_csv(db_path: Optional[Path] = None) -> str:
    """
    Builds a CSV of the aggregates an instructor can take away.

    Only aggregates are exported: no per-event rows, so no timing detail and no
    way to single out an individual session.
    """
    path = Path(db_path or DEFAULT_DB_PATH)
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["seccion", "clave", "valor"])
    writer.writerow(["total", "consultas", total_queries(path)])
    writer.writerow(["promedio", "citas por respuesta", average_citations(path)])
    for unit, n in queries_by_unit(path):
        writer.writerow(["por_unidad", unit, n])
    for day, n in queries_by_day(path):
        writer.writerow(["por_dia", day, n])
    for outcome, n in outcomes_breakdown(path):
        writer.writerow(["por_resultado", outcome, n])
    for label, value in source_usage(path):
        writer.writerow(["fuentes", label, value])
    return buf.getvalue()


def summary(db_path: Optional[Path] = None) -> dict[str, Any]:
    """Everything the instructor tab renders, in one call."""
    path = Path(db_path or DEFAULT_DB_PATH)
    return {
        "total": total_queries(path),
        "by_unit": queries_by_unit(path),
        "by_day": queries_by_day(path),
        "outcomes": outcomes_breakdown(path),
        "avg_citations": average_citations(path),
        "sources": source_usage(path),
    }