"""
tests/test_m1_adversarial_db_stress.py - Adversarial Stress & Concurrency Test Suite for Milestone 1.

Targets:
- src/db.py
- data/quimica_analitica.db (74 MB disk database with 23,943 indexed chunks)

Verifies:
1. Malformed chemical queries (equations, charges, formulas, reaction arrows).
2. Quotes, wildcards, FTS5 keywords (NEAR, NOT, OR, AND, BM25, SNIPPET).
3. SQL injection resilience on both query and syllabus_unit parameters.
4. Concurrency under rapid repeated multithreaded searches.
5. Large inputs (10,000 to 50,000 chars), whitespace, empty queries, invalid units.
6. Search latency benchmark (< 10 ms target) and zero crashes.
"""

from __future__ import annotations

import concurrent.futures
import os
import random
import string
import time
from typing import List, Tuple
import pytest

from src.db import (
    DEFAULT_DB_PATH,
    get_connection,
    init_db,
    search_chunks,
    sanitize_fts_query,
    get_all_books,
    get_book_by_id,
    get_chunk_count,
    get_chunks_by_unit,
)

REAL_DB_PATH = "data/quimica_analitica.db"
HAS_REAL_DB = os.path.exists(REAL_DB_PATH)


class TestAdversarialChemicalQueries:
    """Stress-test chemical equations, ions, charges, and complex scientific notation."""

    ADVERSARIAL_CHEMICAL_QUERIES = [
        # Ion charges and chemical reactions
        "Ca2+ + SO4 2- -> BaSO4",
        "Ca2+ + SO4(2-) -> CaSO4(s)",
        "Fe3+ + 3OH- <=> Fe(OH)3(s)",
        "2KMnO4 + 5H2C2O4 + 3H2SO4 -> K2SO4 + 2MnSO4 + 10CO2 + 8H2O",
        "[Ag(NH3)2]+ + Cl- + 2H+ -> AgCl(s) + 2NH4+",
        "[Fe(CN)6]4- + Fe3+ -> KFe[Fe(CN)6]",
        "H3O+ + OH- <==> 2H2O",
        "Cr2O7^2- + 14H+ + 6e- -> 2Cr^3+ + 7H2O",
        # Formulas with equilibrium & math operators
        "pH = -log[H+]",
        "pOH = -log[OH-]",
        "pH + pOH = 14.00",
        "Ksp = [Ba2+][SO4 2-] = 1.1 x 10^-10",
        "Ka = [H+][A-] / [HA]",
        "E = E0 - (0.0592/n) * log(Q)",
        # Unicode scientific symbols
        "Ca²⁺ + SO₄²⁻ → BaSO₄",
        "H₃O⁺ + OH⁻ ⇌ 2 H₂O",
        "ΔG° = -nFE° = -RT ln(K)",
        "α = [A⁻] / ([HA] + [A⁻])",
        # Mixed chemical formulas and common search terms
        "Ksp BaSO4 precipitado gravimetria",
        "EDTA4- + Ca2+ -> [Ca(EDTA)]2- constante de formacion",
        "HCl 0.1 M + NaOH 0.1 N punto de equivalencia",
    ]

    @pytest.mark.parametrize("query", ADVERSARIAL_CHEMICAL_QUERIES)
    def test_chemical_queries_do_not_crash(self, query: str) -> None:
        """Verify chemical formulas execute cleanly on both real DB (if available) and in-memory DB."""
        # Sanitize check
        q_and, q_or = sanitize_fts_query(query)
        assert isinstance(q_and, str)
        assert isinstance(q_or, str)

        # Real DB execution
        if HAS_REAL_DB:
            results = search_chunks(query, db_path=REAL_DB_PATH)
            assert isinstance(results, list)

        # In-memory execution
        mem_conn = init_db(":memory:")
        try:
            mem_results = search_chunks(query, conn=mem_conn)
            assert isinstance(mem_results, list)
        finally:
            mem_conn.close()


class TestAdversarialFTS5SyntaxAndInjection:
    """Stress-test FTS5 syntax quirks, reserved keywords, and SQL injection strings."""

    FTS5_EDGE_CASES = [
        # Quotes edge cases
        '"',
        '""',
        '"""',
        '"""""',
        '"unclosed phrase',
        'unclosed phrase"',
        '""nested""',
        '"""three quotes"""',
        "'single quotes'",
        "'' OR ''=''",
        # Wildcard edge cases
        "*",
        "***",
        "* * *",
        "acid*",
        "*acid",
        "*acid*",
        "quim* analit*",
        "? % _",
        # FTS5 Reserved keywords & operators
        "NEAR",
        "NEAR/2",
        "NEAR/0",
        "NEAR(ácido base)",
        "NEAR(ácido, base)",
        "ácido NEAR base",
        "NOT",
        "OR",
        "AND",
        "NOT NOT",
        "OR OR",
        "AND AND",
        "AND OR NOT",
        "NOT ácido",
        "ácido NOT",
        "ácido NOT base",
        "OR ácido",
        "ácido OR",
        "AND ácido",
        "ácido AND",
        "MATCH",
        "RANK",
        "BM25",
        "HIGHLIGHT",
        "SNIPPET",
        # FTS5 column filter syntax attempts
        "content:ácido",
        "book_title:Skoog",
        "nonexistent_column:test",
        "author:Douglas AND edition:9ª",
        # SQL Injection attempts on query parameter
        "' OR 1=1 --",
        "\" OR 1=1 --",
        "1'; DROP TABLE chunks; --",
        "'; DELETE FROM chunks WHERE 1=1; --",
        "' UNION SELECT id, filename, title, author, edition, total_pages, cover_path, language, is_scanned FROM books --",
        "1; ATTACH DATABASE '/tmp/pwned.db' AS pwn; --",
        "admin' --",
        "' OR 'x'='x",
        "\\x00\\x01\\x02",
        # Math & special characters
        "+ - = * / % & ^ $ # @ ! ? < > [ ] { } ( ) | \\ : ; , . ~ `",
        "(((((titulacion)))))",
        "[[[[acido]]]]",
        "{{{{base}}}}",
        # Non-ASCII, Unicode, Emojis
        "🔬 ⚗️ 🧪 💥 📊",
        "滴定 酸 碱",
        "титрирование гравиметрия",
    ]

    @pytest.mark.parametrize("query", FTS5_EDGE_CASES)
    def test_fts5_edge_cases_do_not_crash(self, query: str) -> None:
        """Verify no operational error or crash occurs on adversarial FTS syntax."""
        q_and, q_or = sanitize_fts_query(query)
        assert isinstance(q_and, str)
        assert isinstance(q_or, str)

        if HAS_REAL_DB:
            results = search_chunks(query, db_path=REAL_DB_PATH)
            assert isinstance(results, list)

        mem_conn = init_db(":memory:")
        try:
            results = search_chunks(query, conn=mem_conn)
            assert isinstance(results, list)
        finally:
            mem_conn.close()

    SQLI_SYLLABUS_UNITS = [
        "' OR 1=1 --",
        "'; DROP TABLE chunks; --",
        "U1' OR '1'='1",
        "U1; DROP TABLE books; --",
        "U999",
        "NON_EXISTENT_UNIT",
        "",
        "   ",
        "U1 UNION SELECT 1,2,3,4,5,6,7,8,9",
    ]

    @pytest.mark.parametrize("bad_unit", SQLI_SYLLABUS_UNITS)
    def test_sqli_resilience_on_syllabus_unit(self, bad_unit: str) -> None:
        """Verify syllabus_unit filtering is safe against SQL injection."""
        if HAS_REAL_DB:
            results = search_chunks("ácido", syllabus_unit=bad_unit, db_path=REAL_DB_PATH)
            assert isinstance(results, list)

            # Check that chunks table is intact
            conn = get_connection(REAL_DB_PATH)
            try:
                count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
                assert count > 0
            finally:
                conn.close()

            # get_chunks_by_unit must also be safe
            unit_chunks = get_chunks_by_unit(bad_unit, db_path=REAL_DB_PATH)
            assert isinstance(unit_chunks, list)


class TestExtremeBoundaries:
    """Stress-test extreme inputs: empty, huge, boundary limits."""

    def test_empty_and_whitespace_queries(self) -> None:
        """Empty and whitespace strings must return empty list immediately."""
        cases = ["", " ", "   ", "\t", "\n", "\r\n", " \t \n "]
        for c in cases:
            assert search_chunks(c) == []
            q_and, q_or = sanitize_fts_query(c)
            assert q_and == ""
            assert q_or == ""

    def test_10000_character_query(self) -> None:
        """10,000-character repetitive query must process without OOM or recursion error."""
        long_query = "ácido valoración " * 600  # ~10,200 chars
        assert len(long_query) > 10000

        t0 = time.perf_counter()
        q_and, q_or = sanitize_fts_query(long_query)
        sanitize_time = time.perf_counter() - t0
        assert sanitize_time < 0.1  # Fast regex tokenization

        if HAS_REAL_DB:
            t0 = time.perf_counter()
            results = search_chunks(long_query, db_path=REAL_DB_PATH)
            query_time = time.perf_counter() - t0
            assert isinstance(results, list)
            assert len(results) > 0
            assert query_time < 0.01, f"Repetitive query latency ({query_time*1000:.2f}ms) must be < 10ms"
            assert q_and == '"ácido" AND "valoración"'

    def test_50000_character_random_query(self) -> None:
        """50,000-character random query with punctuation and symbols."""
        chars = string.ascii_letters + string.digits + " + - * / = < > [ ] { } ' \" : ; ! ? @ # $ % ^ &"
        random_query = "".join(random.choices(chars, k=50000))
        assert len(random_query) == 50000

        t0 = time.perf_counter()
        q_and, q_or = sanitize_fts_query(random_query)
        sanitize_time = time.perf_counter() - t0
        assert sanitize_time < 0.5

        if HAS_REAL_DB:
            results = search_chunks(random_query, db_path=REAL_DB_PATH)
            assert isinstance(results, list)

    def test_non_string_type_handling(self) -> None:
        """Test defensive behavior against non-string arguments (int, list, None, float, dict). Zero unhandled exceptions."""
        non_string_inputs = [
            12345,
            0,
            -99,
            12.34,
            None,
            [],
            ["ácido", "base"],
            {"query": "ácido"},
            (1, 2, 3),
            True,
            False,
        ]

        # Test sanitize_fts_query with non-string arguments
        for inp in non_string_inputs:
            q_and, q_or = sanitize_fts_query(inp)
            assert isinstance(q_and, str)
            assert isinstance(q_or, str)

        # Test search_chunks with non-string query arguments
        for inp in non_string_inputs:
            res = search_chunks(inp, db_path=REAL_DB_PATH if HAS_REAL_DB else ":memory:")
            assert isinstance(res, list)

        # Test search_chunks with non-string syllabus_unit arguments
        for inp in non_string_inputs:
            res = search_chunks("ácido", syllabus_unit=inp, db_path=REAL_DB_PATH if HAS_REAL_DB else ":memory:")
            assert isinstance(res, list)

    def test_limit_boundaries(self) -> None:
        """Test limit parameter values: negative (-1), zero (0), normal (1, 5), huge (10000), and string ('5', '0', '-1')."""
        if not HAS_REAL_DB:
            pytest.skip("Requires real database")

        # Negative limit (-1): must return empty list, NOT all rows
        res_neg1 = search_chunks("ácido", limit=-1, db_path=REAL_DB_PATH)
        assert res_neg1 == []
        assert len(res_neg1) == 0

        # Negative limit (-100)
        res_neg100 = search_chunks("ácido", limit=-100, db_path=REAL_DB_PATH)
        assert len(res_neg100) == 0

        # Zero limit (0): must return empty list
        res_0 = search_chunks("ácido", limit=0, db_path=REAL_DB_PATH)
        assert len(res_0) == 0

        # limit = 1
        res_1 = search_chunks("ácido", limit=1, db_path=REAL_DB_PATH)
        assert len(res_1) == 1

        # limit = 5
        res_5 = search_chunks("ácido", limit=5, db_path=REAL_DB_PATH)
        assert len(res_5) == 5

        # Huge limit (10000): must be safely capped at 100
        res_huge = search_chunks("ácido", limit=10000, db_path=REAL_DB_PATH)
        assert 1 <= len(res_huge) <= 100

        # String limit ("5"): safely coerced to int 5
        res_str5 = search_chunks("ácido", limit="5", db_path=REAL_DB_PATH)
        assert len(res_str5) == 5

        # String limit ("0"): safely coerced to int 0 -> empty list
        res_str0 = search_chunks("ácido", limit="0", db_path=REAL_DB_PATH)
        assert len(res_str0) == 0

        # String limit ("-1"): safely coerced to int -1 -> empty list
        res_strneg = search_chunks("ácido", limit="-1", db_path=REAL_DB_PATH)
        assert len(res_strneg) == 0

        # Invalid string limit ("abc"): fallback to default 5
        res_str_invalid = search_chunks("ácido", limit="abc", db_path=REAL_DB_PATH)
        assert len(res_str_invalid) == 5

        # None limit: fallback to default 5
        res_none_limit = search_chunks("ácido", limit=None, db_path=REAL_DB_PATH)
        assert len(res_none_limit) == 5


class TestConcurrencyAndThroughput:
    """Stress-test concurrent access: rapid repeated queries across multiple threads."""

    def test_concurrent_multithreaded_searches(self) -> None:
        """Simulate rapid simultaneous queries from 20 concurrent threads."""
        if not HAS_REAL_DB:
            pytest.skip("Requires real database")

        queries = [
            ("ácido base", "U6"),
            ("Mohr cromato plata", "U5"),
            ("gravimetria precipitacion", "U3"),
            ("EDTA dureza agua", "U7"),
            ("KMnO4 permanganometria", "U8"),
            ("Ca2+ + SO4 2-", None),
            ("error sistematico aleatorio", "U1"),
            ("potenciometria electrodo", "U9"),
            ("espectrofotometria Beer", "U9"),
            ("volhard tiocianato", "U5"),
            ("solubilidad producto Ksp", "U3"),
            ("tampon buffer amortiguador", "U6"),
            ("curva valoracion pH", "U6"),
            ("indicador fenolftaleina", "U6"),
            ("balanza analitica calibracion", "U1"),
        ]

        total_requests = 100
        worker_threads = 10
        exceptions: List[Exception] = []
        latencies: List[float] = []

        def run_search(q: str, unit: str | None) -> Tuple[int, float]:
            t0 = time.perf_counter()
            res = search_chunks(q, syllabus_unit=unit, limit=5, db_path=REAL_DB_PATH)
            dur = (time.perf_counter() - t0) * 1000.0  # ms
            return len(res), dur

        # Launch concurrent workload
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_threads) as executor:
            tasks = []
            for i in range(total_requests):
                q, u = queries[i % len(queries)]
                tasks.append(executor.submit(run_search, q, u))

            for fut in concurrent.futures.as_completed(tasks):
                try:
                    count, lat = fut.result()
                    latencies.append(lat)
                except Exception as e:
                    exceptions.append(e)

        # Assert zero crashes / exceptions under concurrency
        assert len(exceptions) == 0, f"Encountered {len(exceptions)} exceptions under concurrency: {exceptions}"
        assert len(latencies) == total_requests

        # Concurrency latency statistics
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"\n[Concurrency Benchmark] 100 queries / 10 threads -> Avg: {avg_latency:.2f} ms, P95: {p95_latency:.2f} ms")


class TestLatencyBenchmark:
    """Benchmark search latency to verify sub-10ms performance requirement."""

    def test_search_latency_under_10ms_average(self) -> None:
        """Measure latency across 100 single-threaded realistic chemical queries."""
        if not HAS_REAL_DB:
            pytest.skip("Requires real database")

        queries = [
            "titulacion acido base",
            "metodo de mohr",
            "precipitacion de sulfato de bario",
            "valoracion con edta",
            "curva de calibracion",
            "permanganometria hierro",
            "potenciometria electrodo de vidrio",
            "producto de solubilidad",
            "solucion amortiguadora ph",
            "error relativo porcentaje",
            "analisis gravimetrico calcinacion",
            "complejometria negro de eriocromo t",
            "argentometria fajans fluoresceina",
            "oxido reduccion nernst",
            "espectrofotometria ley de beer",
            "muestreo representativo",
            "desviacion estandar varianza",
            "digestión de ostwald BaSO4",
            "Ksp hidroxido de hierro",
            "valorante estandar primario biftalato",
        ]

        # Warm-up query
        search_chunks("quimica analitica", db_path=REAL_DB_PATH)

        latencies_ms: List[float] = []
        for _ in range(5):  # 5 rounds of 20 queries = 100 total queries
            for q in queries:
                t0 = time.perf_counter()
                results = search_chunks(q, db_path=REAL_DB_PATH, limit=5)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(elapsed_ms)
                assert isinstance(results, list)

        latencies_sorted = sorted(latencies_ms)
        n = len(latencies_sorted)
        avg_lat = sum(latencies_sorted) / n
        median_lat = latencies_sorted[n // 2]
        p95_lat = latencies_sorted[int(n * 0.95)]
        max_lat = latencies_sorted[-1]
        min_lat = latencies_sorted[0]

        print(
            f"\n[Latency Benchmark - 100 queries against 23,943 chunks]:\n"
            f"  Min:    {min_lat:.2f} ms\n"
            f"  Avg:    {avg_lat:.2f} ms\n"
            f"  Median: {median_lat:.2f} ms\n"
            f"  P95:    {p95_lat:.2f} ms\n"
            f"  Max:    {max_lat:.2f} ms"
        )

        # Requirement: search latency stays low (< 10 ms)
        assert avg_lat < 10.0, f"Average latency ({avg_lat:.2f} ms) exceeds 10 ms requirement"
        assert median_lat < 10.0, f"Median latency ({median_lat:.2f} ms) exceeds 10 ms requirement"
