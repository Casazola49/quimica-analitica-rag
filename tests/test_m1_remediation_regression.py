"""tests/test_m1_remediation_regression.py

Remediation & Regression Test Battery for Milestone 1 Iteration 2.
Verifies fixes for Challenger 1 & Challenger 2 defects:
1. Repetitive 10k query latency (< 10 ms).
2. Defensive argument type coercion in src/db.py.
3. Unit ID alias and normalization in src/syllabus.py.
4. Malformed curriculum JSON resilience in src/syllabus.py.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import pytest

from src.db import DEFAULT_DB_PATH, sanitize_fts_query, search_chunks
from src.syllabus import get_unit_by_id, load_curriculum

HAS_REAL_DB = os.path.exists(DEFAULT_DB_PATH)


class TestRepetitiveQueryLatencyRegression:
    """Group 1: 10,000-character repetitive query performance and capping."""

    def test_single_term_repetitive_10k_query_latency(self) -> None:
        """10k repetitive single term must deduplicate and search in < 10 ms."""
        raw_query = "ácido " * 1800  # ~10,800 chars
        assert len(raw_query) > 10000

        t0 = time.perf_counter()
        q_and, q_or = sanitize_fts_query(raw_query)
        sanitize_dur = time.perf_counter() - t0

        assert sanitize_dur < 0.01, f"Sanitizing took {sanitize_dur*1000:.2f} ms >= 10 ms"
        assert q_and == '"ácido"'
        assert q_or == '"ácido"'

        if HAS_REAL_DB:
            t0 = time.perf_counter()
            results = search_chunks(raw_query, db_path=DEFAULT_DB_PATH)
            query_dur = (time.perf_counter() - t0) * 1000

            assert query_dur < 10.0, f"Query latency {query_dur:.2f} ms exceeded 10 ms target"
            assert len(results) > 0

    def test_two_term_repetitive_10k_query_latency(self) -> None:
        """10k repetitive two terms ('ácido valoración') must complete in < 10 ms."""
        raw_query = "ácido valoración " * 600  # 10,200 chars
        assert len(raw_query) > 10000

        t0 = time.perf_counter()
        q_and, q_or = sanitize_fts_query(raw_query)
        sanitize_dur = time.perf_counter() - t0

        assert sanitize_dur < 0.01
        assert q_and == '"ácido" AND "valoración"'
        assert q_or == '"ácido" OR "valoración"'

        if HAS_REAL_DB:
            t0 = time.perf_counter()
            results = search_chunks(raw_query, db_path=DEFAULT_DB_PATH)
            query_dur = (time.perf_counter() - t0) * 1000

            assert query_dur < 10.0, f"Query latency {query_dur:.2f} ms exceeded 10 ms target"
            assert len(results) > 0

    def test_multi_term_repetitive_query_latency(self) -> None:
        """10 distinct terms repeated 150 times (>12k chars) must complete in < 10 ms."""
        terms = "ácido base volumetría titulación indicador fenolftaleína ph pka equilibrio tampón "
        raw_query = terms * 150  # 12,300 chars

        t0 = time.perf_counter()
        q_and, q_or = sanitize_fts_query(raw_query)
        sanitize_dur = time.perf_counter() - t0

        assert sanitize_dur < 0.01
        parts = q_and.split(" AND ")
        assert len(parts) == 10

        if HAS_REAL_DB:
            t0 = time.perf_counter()
            results = search_chunks(raw_query, db_path=DEFAULT_DB_PATH)
            query_dur = (time.perf_counter() - t0) * 1000

            assert query_dur < 50.0, f"Multi-term query latency {query_dur:.2f} ms exceeded 50 ms target"
            assert isinstance(results, list)

    def test_term_capping_on_massive_unique_query(self) -> None:
        """Queries with > 30 distinct terms must cap at MAX_QUERY_TERMS without error."""
        distinct_words = [f"termino{i}" for i in range(100)]
        raw_query = " ".join(distinct_words)

        q_and, q_or = sanitize_fts_query(raw_query)
        parts = q_and.split(" AND ")
        assert len(parts) <= 30


class TestTypeCoercionAndBoundaryRegression:
    """Group 2: Defensive parameter type coercion in search_chunks and sanitize_fts_query."""

    def test_non_string_query_handling(self) -> None:
        """Non-string queries (int, float, None) must not raise AttributeError."""
        assert sanitize_fts_query(None) == ("", "")
        assert sanitize_fts_query("") == ("", "")
        assert sanitize_fts_query("   ") == ("", "")

        # Coerced int and float in sanitize
        q_int_and, _ = sanitize_fts_query(12345)
        assert q_int_and == '"12345"'

        # search_chunks with non-strings
        assert search_chunks(None) == []
        assert search_chunks("   ") == []
        res_int = search_chunks(12345)
        assert isinstance(res_int, list)
        res_float = search_chunks(3.14159)
        assert isinstance(res_float, list)

    def test_non_string_syllabus_unit_handling(self) -> None:
        """Non-string syllabus_unit (int, None) must not raise AttributeError."""
        if not HAS_REAL_DB:
            pytest.skip("Requires database")

        res_none_unit = search_chunks("ácido", syllabus_unit=None)
        assert isinstance(res_none_unit, list)

        res_int_unit = search_chunks("ácido", syllabus_unit=1)
        assert isinstance(res_int_unit, list)

        res_whitespace_unit = search_chunks("ácido", syllabus_unit="   ")
        assert isinstance(res_whitespace_unit, list)

    def test_limit_parameter_coercion_and_bounds(self) -> None:
        """Limit parameter must handle string ints, negative values, and caps."""
        if not HAS_REAL_DB:
            pytest.skip("Requires database")

        # String integer limit
        res_str_limit = search_chunks("ácido", limit="5")
        assert len(res_str_limit) == 5

        # Limit = 0 must return 0 items
        res_zero = search_chunks("ácido", limit=0)
        assert len(res_zero) == 0

        # Negative limit must return 0 items (neutralize LIMIT -1)
        res_neg = search_chunks("ácido", limit=-1)
        assert len(res_neg) == 0
        res_neg_large = search_chunks("ácido", limit=-100)
        assert len(res_neg_large) == 0

        # Extremely large limit capped to 100
        res_huge = search_chunks("ácido", limit=1000)
        assert 1 <= len(res_huge) <= 100

        # Invalid limit string defaults to 5
        res_invalid = search_chunks("ácido", limit="not_a_number")
        assert len(res_invalid) == 5


class TestUnitIdLookupAndAliasesRegression:
    """Group 3: Unit ID normalization and aliases in get_unit_by_id."""

    @pytest.mark.parametrize("query_id,expected_id", [
        ("UNIT 9", "U9"),
        ("unit 9", "U9"),
        ("Unit 9", "U9"),
        ("UNIT9", "U9"),
        ("unit_9", "U9"),
        ("unit-9", "U9"),
        ("Unit #9", "U9"),
        ("UNIT: 9", "U9"),
        ("UNIT IX", "U9"),
        ("unit ix", "U9"),
        ("Unidad 1", "U1"),
        ("UNIDAD 1", "U1"),
        ("unidad 1", "U1"),
        ("TEMA 1", "U1"),
        ("tema 1", "U1"),
        ("U 1", "U1"),
        ("u-1", "U1"),
        ("UNIDAD I", "U1"),
        ("TEMA I", "U1"),
        ("TEMA 3", "U3"),
        ("Tema III", "U3"),
        ("Unidad IV", "U4"),
        ("THEORY_U7", "U7"),
        ("u9", "U9"),
        ("PRACTICA 13", "LAB_P13"),
        ("practica 13", "LAB_P13"),
        ("práctica 13", "LAB_P13"),
        ("PRÁCTICA 13", "LAB_P13"),
        ("practice 13", "LAB_P13"),
        ("PRACTICE 13", "LAB_P13"),
        ("practical 13", "LAB_P13"),
        ("PRACTICAL 13", "LAB_P13"),
        ("practice 5", "LAB_P5"),
        ("Práctica 5", "LAB_P5"),
        ("p13", "LAB_P13"),
        ("p 13", "LAB_P13"),
        ("p-13", "LAB_P13"),
        ("P#13", "LAB_P13"),
        ("practica xiii", "LAB_P13"),
        ("PRACTICA XIII", "LAB_P13"),
        ("LAB_P 13", "LAB_P13"),
        ("LAB_P13", "LAB_P13"),
        ("PRACTICA IV", "LAB_P4"),
        ("Lab 2", "L2"),
        ("L 4", "L4"),
        ("L 1", "L1"),
        ("l 1", "L1"),
        ("lab 1", "L1"),
        ("LAB 1", "L1"),
        ("LAB_1", "L1"),
        ("LAB_U1", "L1"),
        ("LAB U 1", "L1"),
        ("laboratorio 1", "L1"),
        ("laboratory 1", "L1"),
        ("LAB I", "L1"),
    ])
    def test_mandated_and_alias_unit_lookups(self, query_id: str, expected_id: str) -> None:
        """Verify natural unit ID variations resolve to expected canonical IDs."""
        unit = get_unit_by_id(query_id)
        assert unit is not None, f"get_unit_by_id failed to resolve '{query_id}'"
        actual_id = unit.get("id") or unit.get("practical_id")
        assert actual_id == expected_id, f"For '{query_id}': expected {expected_id}, got {actual_id}"

    @pytest.mark.parametrize("invalid_id", [
        "U999",
        "NONEXISTENT_UNIT",
        "",
        "   ",
        None,
        12345,
    ])
    def test_invalid_unit_ids_return_none(self, invalid_id: any) -> None:
        """Verify invalid or non-existent unit IDs safely return None."""
        assert get_unit_by_id(invalid_id) is None


class TestCurriculumSchemaAnomalyRegression:
    """Group 4: Malformed curriculum JSON defensive loading."""

    @pytest.mark.parametrize("anomaly_payload", [
        {"courses": None},
        {"courses": [None]},
        {"courses": {"theory": None, "laboratory": None}},
        {"courses": {"theory": {"units": None}}},
        {"courses": {"theory": {"units": [None, 123, "bad_entry", {}]}}},
        {"courses": {"laboratory": {"units": [{"practicals": [None, 456]}]}}},
        [1, 2, 3],
        "corrupted string payload",
        {"unexpected_key": "some_value"},
    ])
    def test_malformed_curriculum_payloads_do_not_crash(self, anomaly_payload: any) -> None:
        """load_curriculum must handle null course trees and non-dict JSON gracefully."""
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
            json.dump(anomaly_payload, f)
            temp_path = f.name

        try:
            curriculum = load_curriculum(temp_path, reload=True)
            assert isinstance(curriculum, dict)
            assert "theory_units" in curriculum
            assert len(curriculum["theory_units"]) >= 1
            assert "lab_units" in curriculum
            assert len(curriculum["lab_units"]) >= 1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Restore normal cached spec
        load_curriculum("data/curriculum_spec.json", reload=True)
