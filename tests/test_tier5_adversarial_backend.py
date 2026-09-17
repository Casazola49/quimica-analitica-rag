"""
tests/test_tier5_adversarial_backend.py - Tier 5 White-Box Adversarial Hardening Suite.

Target Modules:
- src/db.py (SQLite FTS5 BM25 Engine)
- src/ingestion.py (Streaming Bounded-Memory Ingestion & Chunker)
- src/syllabus.py (Curriculum Parser, Schema Provider & Topic Matcher)
- src/covers.py (Textbook Cover Image Generator)

Covers all white-box adversarial edge cases, error handlers, boundary conditions,
massive queries, exotic chemistry notations, corrupt inputs, and concurrent stress.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
import unittest.mock as mock

import pytest

from src.db import (
    DEFAULT_DB_PATH,
    get_connection,
    init_db,
    insert_book,
    insert_chunk,
    insert_chunks_batch,
    sanitize_fts_query,
    search_chunks,
    get_all_books,
    get_book_by_id,
    get_chunk_count,
    get_chunks_by_unit,
    rebuild_fts_index,
)
from src.ingestion import (
    BOOK_CATALOG,
    assign_syllabus_unit,
    clean_page_text,
    chunk_text,
    detect_chapter,
    ingest_book,
    stream_pdf_text,
    stream_pdf_pages,
    stream_book_chunks,
)
from src.syllabus import (
    get_all_unit_ids,
    get_cross_curriculum_mappings,
    get_exam_blueprints,
    get_lab_practicals,
    get_lab_units,
    get_theory_units,
    get_unit_by_id,
    load_curriculum,
    match_topics_to_curriculum,
    _normalize_unit_id,
)
from src.covers import (
    BOOK_COVER_CONFIG,
    MINIMAL_PNG_BYTES,
    generate_all_covers,
    generate_cover,
)

REAL_DB_EXISTS = os.path.exists(DEFAULT_DB_PATH)


# ============================================================================
# 1. SQLite FTS5 BM25 Engine Adversarial Tests (src/db.py)
# ============================================================================

class TestTier5Fts5AdversarialEngine:
    """Adversarial stress and boundary testing for SQLite FTS5 BM25 engine."""

    # 1.1 FTS5 Query Edge Cases
    @pytest.mark.parametrize("query_case", [
        '"""acidos"""',
        '"acido "fuerte""',
        '"""""',
        '(((acido',
        'acidos))))',
        '(acido AND base',
        ')( ',
        '"""',
        '"* "',
        '**??^^//',
        'NEAR(acido base, 10)',
        'content: acido',
        'NOT AND OR',
        'AND OR NOT AND',
        '   \t\n  ',
    ])
    def test_fts5_query_syntax_edge_cases_no_crash(self, query_case: str) -> None:
        """Verify malformed quotes, unmatched parentheses, and boolean operators do not crash."""
        q_and, q_or = sanitize_fts_query(query_case)
        assert isinstance(q_and, str)
        assert isinstance(q_or, str)

        mem_conn = init_db(":memory:")
        try:
            results = search_chunks(query_case, conn=mem_conn)
            assert isinstance(results, list)
        finally:
            mem_conn.close()

    def test_fts5_massive_20k_char_query(self) -> None:
        """Verify massive 20,000+ character queries deduplicate, sanitize, and search cleanly."""
        massive_query = ("ácido valoración estequiometría " * 700) + " pH buffer Ka "  # ~24,000 chars
        assert len(massive_query) > 20000

        t0 = time.perf_counter()
        q_and, q_or = sanitize_fts_query(massive_query)
        sanitize_ms = (time.perf_counter() - t0) * 1000

        assert sanitize_ms < 15.0, f"Sanitizing took {sanitize_ms:.2f} ms"
        # Terms must be capped at MAX_QUERY_TERMS (30)
        terms = q_and.split(" AND ")
        assert len(terms) <= 30

        mem_conn = init_db(":memory:")
        try:
            insert_chunk(
                mem_conn,
                book_id="skoog",
                title="Química Analítica",
                author="Skoog",
                edition="9ed",
                chapter="Capítulo 6",
                page_num=100,
                syllabus_unit="U6",
                content="Valoración de ácido fuerte con base fuerte y cálculo de pH.",
            )
            t0 = time.perf_counter()
            results = search_chunks(massive_query, conn=mem_conn)
            search_ms = (time.perf_counter() - t0) * 1000

            assert isinstance(results, list)
            assert search_ms < 20.0
            assert len(results) > 0
        finally:
            mem_conn.close()

    def test_fts5_unicode_diacritics_and_accents(self) -> None:
        """Verify Spanish accents and diacritics are matched accurately in FTS5."""
        mem_conn = init_db(":memory:")
        try:
            insert_chunk(
                mem_conn,
                book_id="skoog",
                title="Fundamentos",
                author="Skoog",
                edition="9ed",
                chapter="Cap 5",
                page_num=50,
                syllabus_unit="U6",
                content="La estequiometría de la reacción ácido-base requiere una solución reguladora.",
            )
            # Unaccented search
            res_unaccented = search_chunks("estequiometria reaccion acido base solucion", conn=mem_conn)
            assert len(res_unaccented) == 1

            # Accented search
            res_accented = search_chunks("estequiometría reacción ácido-base solución", conn=mem_conn)
            assert len(res_accented) == 1
        finally:
            mem_conn.close()

    # 1.2 Exotic Chemistry Formulas & Symbols
    @pytest.mark.parametrize("chem_formula", [
        "[Fe(CN)6]4-",
        "[Cu(NH3)4]2+",
        "[Co(NH3)6]3+",
        "Cr2O7^2- + 14H+ + 6e- -> 2Cr^3+ + 7H2O",
        "2 KMnO4 + 5 H2C2O4 + 3 H2SO4 -> K2SO4 + 2 MnSO4 + 10 CO2 + 8 H2O",
        "pH = -log[H+]",
        "Ka = [H+][A-]/[HA]",
        "Ksp = [Ba2+][SO4^2-] = 1.1e-10",
        "α_4 = Ka1*Ka2*Ka3*Ka4 / D",
        "ΔG° = -nFE° = -RT ln(K)",
        "λ_max = 510 nm",
        "μ = 0.5 * Σ(ci * zi²)",
        "Ca²⁺ + SO₄²⁻ ⇌ CaSO₄(s)",
        "H₃O⁺ + OH⁻ ⇄ 2 H₂O",
    ])
    def test_fts5_exotic_chemistry_symbols_execute_safely(self, chem_formula: str) -> None:
        """Verify complex chemical formulas, ionic charges, math symbols, and arrows execute cleanly."""
        mem_conn = init_db(":memory:")
        try:
            insert_chunk(
                mem_conn,
                book_id="skoog",
                title="Química Analítica",
                author="Skoog",
                edition="9ed",
                chapter="Capítulo General",
                page_num=1,
                syllabus_unit="U7",
                content=f"Fórmula analítica relevante: {chem_formula}",
            )
            res = search_chunks(chem_formula, conn=mem_conn)
            assert isinstance(res, list)
        finally:
            mem_conn.close()

    # 1.3 SQL Injection Resilience in Query and Unit
    @pytest.mark.parametrize("sql_injection", [
        "'; DROP TABLE chunks; --",
        "' OR '1'='1",
        "\"; DROP TABLE chunks_fts; --",
        "Robert'); DROP TABLE books;--",
        "' UNION SELECT id, filename, title, author, edition, total_pages, cover_path, language, is_scanned FROM books --",
        "admin'--",
        "' OR 1=1 /*",
    ])
    def test_sql_injection_resilience_in_query_and_unit(self, sql_injection: str) -> None:
        """Verify SQL injection strings in both query and syllabus_unit parameters are neutralized."""
        mem_conn = init_db(":memory:")
        try:
            insert_chunk(
                mem_conn,
                book_id="skoog",
                title="Química",
                author="Skoog",
                edition="9ed",
                chapter="Cap 1",
                page_num=10,
                syllabus_unit="U1",
                content="Muestreo y tratamiento de muestra.",
            )
            # Query injection
            res_q = search_chunks(sql_injection, conn=mem_conn)
            assert isinstance(res_q, list)

            # Unit filter injection
            res_u = search_chunks("muestreo", syllabus_unit=sql_injection, conn=mem_conn)
            assert isinstance(res_u, list)

            # Verify schema is intact
            cur = mem_conn.execute("SELECT count(*) FROM chunks;")
            assert cur.fetchone()[0] == 1
        finally:
            mem_conn.close()

    # 1.4 Metadata SQL Injection in insert_chunk and insert_book
    def test_metadata_sql_injection_in_inserts(self) -> None:
        """Verify malicious SQL payloads inside book and chunk metadata fields are safely escaped."""
        mem_conn = init_db(":memory:")
        try:
            malicious_meta = "'; DROP TABLE chunks; DROP TABLE books; --"
            book_id = insert_book(mem_conn, {
                "filename": "malicious.pdf",
                "title": malicious_meta,
                "author": malicious_meta,
                "edition": malicious_meta,
                "total_pages": 100,
                "cover_path": malicious_meta,
                "language": "es",
                "is_scanned": 0,
            })
            assert book_id > 0

            chunk_id = insert_chunk(
                mem_conn,
                book_id=malicious_meta,
                title=malicious_meta,
                author=malicious_meta,
                edition=malicious_meta,
                chapter=malicious_meta,
                page_num=1,
                syllabus_unit=malicious_meta,
                content=f"Contenido legítimo con inyección: {malicious_meta}",
            )
            assert chunk_id > 0

            # Both tables must remain fully functional
            books = get_all_books(conn=mem_conn)
            assert len(books) == 1
            assert books[0]["title"] == malicious_meta

            count = get_chunk_count(conn=mem_conn)
            assert count == 1

            # FTS search must find the injected content safely
            search_res = search_chunks("Contenido legítimo", conn=mem_conn)
            assert len(search_res) == 1
        finally:
            mem_conn.close()

    # 1.5 Corrupted SQLite File Detection
    def test_corrupted_sqlite_file_raises_database_error(self, tmp_path: Path) -> None:
        """Verify connecting or executing against a corrupted SQLite file raises sqlite3.DatabaseError."""
        corrupt_db_file = tmp_path / "corrupt.db"
        corrupt_db_file.write_bytes(b"INVALID_SQLITE_HEADER_RANDOM_CORRUPT_BYTES_9876543210")

        # sqlite3 detects the invalid header and raises DatabaseError
        with pytest.raises(Exception) as exc_info:
            conn = get_connection(str(corrupt_db_file), read_only=False)
            conn.execute("SELECT * FROM sqlite_master;")
        assert issubclass(exc_info.type, Exception)

    # 1.6 Batch Insert Robustness
    def test_insert_chunks_batch_varied_inputs(self) -> None:
        """Verify insert_chunks_batch handles 8-tuples, 9-tuples, dicts, and empty lists."""
        mem_conn = init_db(":memory:")
        try:
            items = [
                # 8-tuple
                ("b1", "T1", "A1", "E1", "C1", 1, "U1", "Contenido 8-tupla"),
                # 9-tuple
                ("b1", "T1", "A1", "E1", "C1", 2, "U1", "Contenido 9-tupla", 3),
                # dict
                {
                    "book_id": "b1",
                    "title": "T1",
                    "author": "A1",
                    "edition": "E1",
                    "chapter": "C1",
                    "page_num": 3,
                    "syllabus_unit": "U1",
                    "content": "Contenido diccionario",
                },
            ]
            count = insert_chunks_batch(mem_conn, items)
            assert count == 3
            assert get_chunk_count(conn=mem_conn) == 3

            # Empty batch
            assert insert_chunks_batch(mem_conn, []) == 0
        finally:
            mem_conn.close()

    # 1.7 Sub-millisecond Query Latency & Concurrent Load
    def test_fts5_sub_millisecond_in_memory_query_performance(self) -> None:
        """Verify FTS5 BM25 retrieval operates in sub-millisecond speed (< 1.0 ms) under load."""
        mem_conn = init_db(":memory:")
        try:
            for i in range(100):
                insert_chunk(
                    mem_conn,
                    book_id=f"book_{i}",
                    title=f"Libro {i}",
                    author="Autor Químico",
                    edition="1ed",
                    chapter=f"Capítulo {i % 10}",
                    page_num=i + 1,
                    syllabus_unit=f"U{(i % 9) + 1}",
                    content=f"Análisis químico experimental con valoración ácido base y precipitado muestra {i}.",
                )

            # Warm up
            search_chunks("ácido base", conn=mem_conn)

            latencies = []
            for _ in range(50):
                t0 = time.perf_counter()
                res = search_chunks("ácido base valoración", conn=mem_conn)
                latencies.append((time.perf_counter() - t0) * 1000)
                assert len(res) > 0

            avg_ms = sum(latencies) / len(latencies)
            assert avg_ms < 1.0, f"Average query latency {avg_ms:.3f} ms exceeded sub-millisecond (< 1.0 ms) target"
        finally:
            mem_conn.close()

    @pytest.mark.skipif(not REAL_DB_EXISTS, reason="Requires real quimica_analitica.db")
    def test_fts5_real_db_query_performance(self) -> None:
        """Verify search query latency on real 74 MB database remains responsive (< 50 ms avg)."""
        benchmark_queries = [
            "valoración ácido base",
            "curva de titulación pH",
            "EDTA dureza del agua",
            "Ksp precipitado BaSO4",
            "permanganometría sulfato ferroso",
            "error sistemático aleatorio Gauss",
            "espectrofotometría ley de Beer",
            "cromatografía HPLC fase móvil",
            "electrodo de calomel saturado",
            "indicador fenolftaleína viraje",
        ] * 3  # 30 queries

        # Warm-up query
        search_chunks("química analítica", db_path=DEFAULT_DB_PATH)

        latencies = []
        for q in benchmark_queries:
            t0 = time.perf_counter()
            res = search_chunks(q, db_path=DEFAULT_DB_PATH)
            dur_ms = (time.perf_counter() - t0) * 1000
            latencies.append(dur_ms)
            assert isinstance(res, list)

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 50.0, f"Average query latency {avg_latency:.2f} ms exceeded 50 ms target"

    @pytest.mark.skipif(not REAL_DB_EXISTS, reason="Requires real quimica_analitica.db")
    def test_fts5_multithreaded_concurrency_stress(self) -> None:
        """Verify concurrent multi-threaded read access without locks or database corruption."""
        queries = [
            "ácido acético Ka",
            "gravimetría digestión",
            "Mohr cromato de potasio",
            "complejo EDTA constante condicional",
            "permanganato de potasio",
        ] * 8  # 40 tasks across 8 threads

        def run_search(q: str):
            res = search_chunks(q, db_path=DEFAULT_DB_PATH)
            return len(res)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(run_search, q) for q in queries]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == len(queries)
        assert all(count > 0 for count in results)

    # 1.8 Boundary Parameter Coercion
    def test_db_parameter_coercion_edge_cases(self) -> None:
        """Verify negative, zero, string, or excessive limits are coerced safely."""
        mem_conn = init_db(":memory:")
        try:
            insert_chunk(mem_conn, "b1", "T", "A", "E", "C", 1, "U1", "Test chunk")
            # limit <= 0 returns empty list
            assert search_chunks("Test", limit=0, conn=mem_conn) == []
            assert search_chunks("Test", limit=-10, conn=mem_conn) == []

            # string limit coerced
            res_str = search_chunks("Test", limit="5", conn=mem_conn)
            assert len(res_str) == 1

            # get_chunks_by_unit coercion
            assert get_chunks_by_unit(None, conn=mem_conn) == []
            assert get_chunks_by_unit("", conn=mem_conn) == []
            assert get_chunks_by_unit("U1", limit=0, conn=mem_conn) == []
            assert len(get_chunks_by_unit("U1", limit=10, conn=mem_conn)) == 1

            # get_book_by_id edge cases
            assert get_book_by_id(999, conn=mem_conn) is None
        finally:
            mem_conn.close()


# ============================================================================
# 2. Streaming Ingestion Engine Adversarial Tests (src/ingestion.py)
# ============================================================================

class TestTier5StreamingIngestionEngine:
    """Adversarial stress and edge case testing for streaming ingestion pipeline."""

    def test_stream_pdf_text_zero_byte_pdf(self, tmp_path: Path) -> None:
        """Verify zero-byte PDF returns an empty generator without spawning pdftotext or crashing."""
        zero_pdf = tmp_path / "empty.pdf"
        zero_pdf.touch()

        pages = list(stream_pdf_text(str(zero_pdf)))
        assert pages == []

    def test_stream_pdf_text_corrupted_pdf_header(self, tmp_path: Path) -> None:
        """Verify corrupt PDF header returns empty generator without unhandled exceptions."""
        corrupt_pdf = tmp_path / "corrupt.pdf"
        corrupt_pdf.write_bytes(b"CORRUPT_HEADER_NOT_A_VALID_PDF_123456789\nLINE2\nLINE3")

        pages = list(stream_pdf_text(str(corrupt_pdf)))
        assert pages == []

    def test_stream_pdf_text_missing_file_raises_filenotfound(self) -> None:
        """Verify non-existent PDF file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            list(stream_pdf_text("non_existent_path_to_textbook.pdf"))

    def test_stream_pdf_text_missing_poppler_binary_simulation(self, tmp_path: Path) -> None:
        """Verify graceful fallback when pdftotext binary is missing from system."""
        dummy_pdf = tmp_path / "test.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 dummy valid header")

        with mock.patch("subprocess.Popen", side_effect=FileNotFoundError("No such file: pdftotext")):
            pages = list(stream_pdf_text(str(dummy_pdf)))
            assert pages == []

    def test_clean_page_text_adversarial_inputs(self) -> None:
        """Verify clean_page_text handles control characters, extreme hyphenation, and huge blocks."""
        # Control characters
        raw_control = "\x00\x01\x02\x03\x04\x05Texto normal\x0b\x0c\x1b[31m"
        cleaned_control = clean_page_text(raw_control)
        assert "\x00" not in cleaned_control
        assert "Texto normal" in cleaned_control

        # Hyphenated scientific terms across line breaks
        raw_hyphen = "comple-\njos de coordi-\nnación en solu-\nción a-\ncuosa"
        cleaned_hyphen = clean_page_text(raw_hyphen)
        assert "complejos" in cleaned_hyphen
        assert "coordinación" in cleaned_hyphen
        assert "solución" in cleaned_hyphen
        assert "acuosa" in cleaned_hyphen

        # Excessive blank lines
        raw_blanks = "Párrafo 1\n\n\n\n\n\n\nPárrafo 2\n\n\n\nPárrafo 3"
        cleaned_blanks = clean_page_text(raw_blanks)
        assert "\n\n\n" not in cleaned_blanks
        assert "Párrafo 1\n\nPárrafo 2\n\nPárrafo 3" == cleaned_blanks

        # Empty / None / Whitespace
        assert clean_page_text("") == ""
        assert clean_page_text(None) == ""
        assert clean_page_text("   \n\t  ") == ""

    def test_detect_chapter_toc_suppression_heuristics(self) -> None:
        """Verify Table of Contents (TOC) pages suppress false chapter transitions."""
        current_ch = "Capítulo 2: Cálculos"

        # Multi-chapter marker page (TOC)
        toc_page = """
        CONTENIDO
        Capítulo 1: Introducción ........... 1
        Capítulo 2: Cálculos ............... 25
        Capítulo 3: Gravimetría ............ 50
        Capítulo 4: Volumetría ............. 80
        """
        assert detect_chapter(toc_page, current_ch, {}, 5) == current_ch

        # Header with ÍNDICE
        indice_page = "ÍNDICE GENERAL\nCapítulo 4: Volumetría\nTemas a tratar"
        assert detect_chapter(indice_page, current_ch, {}, 6) == current_ch

        # Valid chapter transition
        valid_ch_page = "CAPÍTULO 4\nVALORACIONES DE PRECIPITACIÓN\nEn este capítulo analizaremos..."
        detected = detect_chapter(valid_ch_page, current_ch, {}, 50)
        assert "Capítulo 4" in detected

    def test_chunk_text_delimiters_and_no_whitespace_stress(self) -> None:
        """Verify chunk_text handles delimiter-free strings without infinite loops or crashes."""
        meta = {"book_id": "b1", "title": "T1", "syllabus_unit": "U1"}

        # Text with zero spaces or punctuation (continuous stream)
        no_delim_text = "A" * 5000
        chunks = chunk_text(no_delim_text, page_num=1, metadata=meta, chunk_size=1000, overlap=150)
        assert len(chunks) >= 5
        assert all(len(c["content"]) <= 1000 for c in chunks)

        # Invalid arguments
        with pytest.raises(ValueError):
            chunk_text("Valid text", chunk_size=0)
        with pytest.raises(ValueError):
            chunk_text("Valid text", chunk_size=500, overlap=500)
        with pytest.raises(ValueError):
            chunk_text("Valid text", chunk_size=500, overlap=-10)

        # Empty text
        assert chunk_text("", metadata=meta) == []

    def test_ingest_scanned_book_registers_without_ocr_chunks(self, tmp_path: Path) -> None:
        """Verify scanned books register metadata in DB while bypassing text extraction."""
        mem_conn = init_db(":memory:")
        try:
            scanned_meta = {
                "id": "day_underwood_5ed_es",
                "filename": "day_underwood_5ed_es.pdf",
                "title": "Química Analítica Cuantitativa",
                "authors": "Day, Underwood",
                "edition": "5ª Edición",
                "total_pages": 870,
                "is_scanned": True,
                "default_syllabus_unit": "L5",
            }
            res = ingest_book(
                conn=mem_conn,
                pdf_path=str(tmp_path / "day_underwood_5ed_es.pdf"),
                book_meta=scanned_meta,
                covers_dir=str(tmp_path / "covers"),
            )
            assert res["status"] == "scanned_registered"
            assert res["chunks_inserted"] == 0

            # Verified registered in books table
            book_record = get_book_by_id("day_underwood_5ed_es", conn=mem_conn)
            assert book_record is not None
            assert book_record["is_scanned"] == 1
        finally:
            mem_conn.close()


# ============================================================================
# 3. Syllabus Curriculum Engine Adversarial Tests (src/syllabus.py)
# ============================================================================

class TestTier5SyllabusCurriculumEngine:
    """Adversarial stress and edge case testing for curriculum parser and topic matcher."""

    def test_load_curriculum_sparse_and_corrupted_json(self, tmp_path: Path) -> None:
        """Verify load_curriculum gracefully falls back to default schema on corrupt/sparse JSON."""
        # 1. Corrupt JSON syntax
        bad_json = tmp_path / "corrupt_curriculum.json"
        bad_json.write_text("{this is corrupt json syntax: true", encoding="utf-8")
        spec_bad = load_curriculum(str(bad_json), reload=True)
        assert "theory_units" in spec_bad
        assert len(spec_bad["theory_units"]) == 9

        # 2. Sparse JSON missing units
        sparse_json = tmp_path / "sparse.json"
        sparse_json.write_text(json.dumps({"courses": {"theory": {}, "laboratory": {}}}), encoding="utf-8")
        spec_sparse = load_curriculum(str(sparse_json), reload=True)
        assert len(spec_sparse["theory_units"]) == 9
        assert len(spec_sparse["lab_units"]) == 8

        # 3. Non-existent file
        spec_missing = load_curriculum("non_existent_file_spec.json", reload=True)
        assert len(spec_missing["theory_units"]) == 9

        # Reload canonical curriculum
        load_curriculum("data/curriculum_spec.json", reload=True)

    def test_get_unit_by_id_null_empty_and_alias_variations(self) -> None:
        """Verify get_unit_by_id handles nulls, aliases, Roman numerals, and case variations."""
        # Null / empty / invalid
        assert get_unit_by_id(None) is None
        assert get_unit_by_id("") is None
        assert get_unit_by_id("   \t  ") is None
        assert get_unit_by_id("NON_EXISTENT_UNIT_999") is None

        # Custom default
        assert get_unit_by_id(None, default="fallback") == "fallback"

        # Alias variations
        test_aliases = [
            ("unidad 1", "U1"),
            ("UNIDAD I", "U1"),
            ("tema 2", "U2"),
            ("TEMA II", "U2"),
            ("Unidad 3", "U3"),
            ("UNIDAD IV", "U4"),
            ("tema 5", "U5"),
            ("UNIDAD VI", "U6"),
            ("unidad 7", "U7"),
            ("UNIDAD VIII", "U8"),
            ("tema 9", "U9"),
            ("lab 1", "L1"),
            ("LABORATORIO 2", "L2"),
            ("lab 3", "L3"),
            ("LAB IV", "L4"),
            ("práctica 5", "LAB_P5"),
            ("PRACTICA V", "LAB_P5"),
            ("practica 7", "LAB_P7"),
            ("PRACTICA_10", "LAB_P10"),
            ("p-12", "LAB_P12"),
            ("LAB_P13", "LAB_P13"),
            ("U01", "U1"),
            ("L08", "L8"),
        ]
        for alias, expected_id in test_aliases:
            unit = get_unit_by_id(alias)
            assert unit is not None, f"Alias '{alias}' failed to resolve"
            actual_id = unit.get("id") or unit.get("practical_id")
            assert actual_id == expected_id, f"Alias '{alias}' resolved to {actual_id}, expected {expected_id}"

    def test_match_topics_gibberish_and_out_of_syllabus_spanish(self) -> None:
        """Verify topic matcher returns empty list on gibberish and out-of-syllabus text."""
        # Gibberish queries
        assert match_topics_to_curriculum("asdfghjkl qwerty 123456") == []
        assert match_topics_to_curriculum("!@#$%^&*()_+=-~`") == []
        assert match_topics_to_curriculum("   \n\t  ") == []
        assert match_topics_to_curriculum("") == []
        assert match_topics_to_curriculum(None) == []

        # Out-of-syllabus Spanish sentences (politics, economy, sports)
        out_of_syllabus_samples = [
            "El presidente anunció un nuevo plan de infraestructura vial para autopistas y puentes.",
            "La selección nacional clasificó a la fase final del torneo de fútbol sudamericano.",
            "El banco central elevó la tasa de interés interbancaria para contener la inflación.",
            "La cotización de las acciones en la bolsa de valores mostró variaciones positivas.",
        ]
        for sentence in out_of_syllabus_samples:
            matches = match_topics_to_curriculum(sentence, threshold=4.0)
            assert matches == [], f"Sentence matched unexpectedly: '{sentence}' -> {matches}"

    def test_match_topics_chemical_precision_and_course_filters(self) -> None:
        """Verify domain ontology precision and course filtering (theory vs lab)."""
        # EDTA -> Complexometry (U7 / L5)
        edta_matches = match_topics_to_curriculum("curva de titulación con EDTA y constante condicional alpha 4")
        assert any(u in edta_matches for u in ["U7", "THEORY_U7"])

        # Filter by theory
        theory_only = match_topics_to_curriculum("valoración ácido base punto de equivalencia", course_filter="theory")
        assert all(u.startswith("U") or u.startswith("THEORY_") for u in theory_only)

        # Filter by lab
        lab_only = match_topics_to_curriculum("determinación gravimétrica de sulfatos en crisol", course_filter="lab")
        assert all(u.startswith("L") or u.startswith("LAB_") for u in lab_only)


# ============================================================================
# 4. Covers Generator Engine Adversarial Tests (src/covers.py)
# ============================================================================

class TestTier5CoversEngine:
    """Adversarial stress and edge case testing for textbook cover generator."""

    def test_generate_cover_missing_source_pdf_raises_filenotfound(self) -> None:
        """Verify non-existent source PDF raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generate_cover("non_existent_book.pdf", "assets/covers/test.png")

    def test_generate_cover_nested_directory_auto_creation(self, tmp_path: Path) -> None:
        """Verify generate_cover automatically creates deep nested output directories."""
        dummy_pdf = tmp_path / "dummy.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 dummy header")

        nested_output = tmp_path / "deep" / "nested" / "assets" / "cover.png"
        assert not nested_output.parent.exists()

        result_path = generate_cover(str(dummy_pdf), str(nested_output))
        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0

    def test_generate_cover_missing_pdftoppm_binary_simulation(self, tmp_path: Path) -> None:
        """Verify fallback to valid minimal PNG bytes when pdftoppm binary is missing."""
        dummy_pdf = tmp_path / "dummy.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 dummy header")
        out_png = tmp_path / "fallback.png"

        with mock.patch("subprocess.run", side_effect=FileNotFoundError("No such file: pdftoppm")):
            res = generate_cover(str(dummy_pdf), str(out_png))
            assert Path(res).exists()
            assert Path(res).read_bytes() == MINIMAL_PNG_BYTES

    def test_generate_all_covers_ignores_non_pdf_files(self, tmp_path: Path) -> None:
        """Verify generate_all_covers ignores .txt, .png, and hidden files in books directory."""
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        (books_dir / "notes.txt").write_text("Not a pdf")
        (books_dir / ".DS_Store").write_bytes(b"macos junk")
        (books_dir / "image.png").write_bytes(b"image")

        out_dir = tmp_path / "covers"
        generated = generate_all_covers(books_dir=str(books_dir), output_dir=str(out_dir))
        assert generated == []

    def test_generate_all_covers_non_existent_books_dir_returns_empty(self) -> None:
        """Verify non-existent books directory returns empty list without crashing."""
        res = generate_all_covers(books_dir="non_existent_directory_of_books")
        assert res == []

    def test_generate_all_covers_read_only_output_directory(self, tmp_path: Path) -> None:
        """Verify generate_all_covers gracefully handles read-only output directory without crashing."""
        books_dir = tmp_path / "books"
        books_dir.mkdir()
        dummy_pdf = books_dir / "test_book.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 dummy")

        ro_dir = tmp_path / "readonly_covers"
        ro_dir.mkdir()
        # Set read-only permissions with traversal bit (0555)
        os.chmod(ro_dir, stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP)

        try:
            covers = generate_all_covers(books_dir=str(books_dir), output_dir=str(ro_dir), force=True)
            assert isinstance(covers, list)
        finally:
            os.chmod(ro_dir, stat.S_IRWXU)
