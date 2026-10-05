"""
test_metrics.py - Anonymous usage metrics.

These tests exist mainly to prove the privacy claim: the store must never be
able to hold a student's question, their answer, or their API key, because that
is the property that makes this feature acceptable to deploy at all.
"""

import csv
import io
import sqlite3

import pytest

from src import metrics


@pytest.fixture()
def db(tmp_path):
    return tmp_path / "usage_metrics.db"


def _rows(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM query_events")]
    finally:
        conn.close()


class TestRecording:
    def test_event_is_stored(self, db) -> None:
        assert metrics.record_query_event(unit="U8", unit_source="inferred", db_path=db) is True
        rows = _rows(db)
        assert len(rows) == 1
        assert rows[0]["unit"] == "U8"
        assert rows[0]["outcome"] == "ok"

    def test_no_text_columns_exist(self, db) -> None:
        """The schema itself must be unable to hold question or answer text."""
        metrics.record_query_event(unit="U2", question_chars=42, db_path=db)
        cols = set(_rows(db)[0].keys())
        assert cols == {
            "id", "occurred_at", "day", "unit", "unit_source", "question_chars",
            "chunks", "citations", "sources", "model", "outcome",
        }
        forbidden = {"question", "query", "answer", "prompt", "api_key", "text", "email"}
        assert not (cols & forbidden)

    def test_collection_can_be_disabled(self, db, monkeypatch) -> None:
        monkeypatch.setenv("METRICS_DISABLED", "1")
        assert metrics.collection_enabled() is False
        assert metrics.record_query_event(unit="U1", db_path=db) is False
        assert metrics.total_queries(db) == 0

    def test_bad_input_does_not_raise(self, db) -> None:
        """A metric failure must never break a student's question."""
        assert metrics.record_query_event(unit=None, citations=-5, chunks=None, db_path=db) in (True, False)
        metrics.record_query_event(unit="U1", db_path=db)
        assert metrics.total_queries(db) >= 0

    def test_unwritable_path_is_swallowed(self, tmp_path) -> None:
        blocked = tmp_path / "no_such_dir_as_file" / "x.db"
        blocked.parent.write_text("not a directory")
        assert metrics.record_query_event(unit="U1", db_path=blocked) is False


class TestAggregates:
    def _seed(self, db) -> None:
        for i in range(4):
            metrics.record_query_event(unit="U8", unit_source="inferred", citations=3, sources=2, db_path=db)
        metrics.record_query_event(unit="U2", unit_source="selected", citations=1, sources=1, db_path=db)
        metrics.record_query_event(unit="U8", outcome="quota", citations=0, sources=0, db_path=db)

    def test_total_and_by_unit(self, db) -> None:
        self._seed(db)
        assert metrics.total_queries(db) == 6
        by_unit = dict(metrics.queries_by_unit(db))
        assert by_unit["U8"] == 5
        assert by_unit["U2"] == 1

    def test_outcomes_breakdown(self, db) -> None:
        self._seed(db)
        outcomes = dict(metrics.outcomes_breakdown(db))
        assert outcomes["ok"] == 5
        assert outcomes["quota"] == 1

    def test_average_citations_ignores_failures(self, db) -> None:
        """A quota-blocked answer has zero citations and must not drag the mean."""
        self._seed(db)
        assert metrics.average_citations(db) == 2.6

    def test_by_day_is_ordered(self, db) -> None:
        self._seed(db)
        days = metrics.queries_by_day(db)
        assert len(days) == 1
        assert days[0][1] == 6

    def test_empty_database_is_handled(self, db) -> None:
        assert metrics.total_queries(db) == 0
        assert metrics.average_citations(db) == 0.0
        assert metrics.summary(db)["by_unit"] == []

    def test_summary_shape(self, db) -> None:
        self._seed(db)
        data = metrics.summary(db)
        assert set(data) == {"total", "by_unit", "by_day", "outcomes", "avg_citations", "sources"}
        assert data["total"] == 6


class TestExport:
    def test_csv_is_aggregated_only(self, db) -> None:
        """The export must not contain one row per event: that would leak timing."""
        for _ in range(10):
            metrics.record_query_event(unit="U1", db_path=db)
        rows = list(csv.reader(io.StringIO(metrics.export_csv(db))))
        header = rows[0]
        assert header == ["seccion", "clave", "valor"]
        # 10 events collapse into a handful of aggregate rows.
        assert len(rows) < 10
        assert ("total", "consultas", "10") in [tuple(r) for r in rows]

    def test_csv_contains_no_question_text(self, db) -> None:
        metrics.record_query_event(unit="U9", question_chars=55, db_path=db)
        text = metrics.export_csv(db)
        assert "question" not in text.lower()
        assert "55" not in text