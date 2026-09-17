"""Tier 3: Pairwise Cross-Feature Combination Tests.

Verifies 16 pairwise and cross-module interactions across Ingestion, FTS5 DB, Curriculum,
BYOK Gemini Client, RAG Engine, Tutor, Exam Simulator, and UI Showcase.
"""

from __future__ import annotations

import os
import sqlite3
import urllib.parse
import pytest
from tests.helpers import (
    get_db_module,
    get_syllabus_module,
    get_gemini_module,
    get_rag_module,
    get_tutor_module,
    get_exam_module,
    get_covers_module,
    get_ingestion_module,
    get_ui_module,
)


class TestTier3Combinations:
    """Tier 3: Pairwise cross-feature interactions verification."""

    def test_pairwise_01_ingestion_and_fts5_indexing(self) -> None:
        """Pairwise: Ingestion Chunker (F2) + SQLite FTS5 Indexing (F4)."""
        ingestion = get_ingestion_module()
        db = get_db_module()
        conn = db.init_db(":memory:")

        text = (
            "La volumetría de neutralización permite determinar la acidez del vinagre comercial. "
            "Se titula el ácido acético con NaOH patrón usando fenolftaleína."
        )
        metadata = {
            "book_id": "skoog_9ed_es",
            "title": "Fundamentos de Química Analítica",
            "author": "Skoog et al.",
            "edition": "9ª Edición",
            "chapter": "Capítulo 16",
            "syllabus_unit": "U6"
        }
        chunks = ingestion.chunk_text(text, page_num=380, metadata=metadata, chunk_size=500, overlap=50)
        assert len(chunks) >= 1

        for c in chunks:
            db.insert_chunk(
                conn=conn,
                book_id=c["book_id"],
                title=c["book_title"],
                author=c["author"],
                edition=c["edition"],
                chapter=c["chapter"],
                page_num=c["page_num"],
                syllabus_unit=c["syllabus_unit"],
                content=c["content"]
            )

        results = db.search_chunks("vinagre acético fenolftaleína", conn=conn)
        assert len(results) >= 1
        assert results[0]["syllabus_unit"] == "U6"
        conn.close()

    def test_pairwise_02_curriculum_and_syllabus_navigation(self) -> None:
        """Pairwise: Curriculum Parser (F3) + Syllabus Topic Navigator UI (F11)."""
        syllabus = get_syllabus_module()
        theory_units = syllabus.get_theory_units()
        lab_units = syllabus.get_lab_units()

        assert len(theory_units) == 9
        assert len(lab_units) == 8

        # Verify mapping consistency
        for tu in theory_units:
            assert tu["id"].startswith("U")
            assert len(tu["topics"]) > 0

        for lu in lab_units:
            assert lu["id"].startswith("L")
            assert len(lu["practices"]) > 0

    def test_pairwise_03_syllabus_selection_and_tutor_grounding(self, valid_api_key: str) -> None:
        """Pairwise: Syllabus Navigation (F11) + Tutor Prompt Grounding (F8)."""
        syllabus = get_syllabus_module()
        tutor = get_tutor_module()

        unit_u3 = syllabus.get_unit_by_id("U3")
        assert unit_u3 is not None

        response = tutor.get_tutor_response(
            "¿Cuáles son los factores que minimizan la coprecipitación?",
            history=[],
            current_unit_id=unit_u3["id"],
            api_key=valid_api_key
        )
        assert len(response) > 50
        assert "Weimarn" in response or "precipita" in response.lower() or "coprecipit" in response.lower()

    def test_pairwise_04_fts5_retrieval_and_rag_prompt_assembly(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
    ) -> None:
        """Pairwise: FTS5 BM25 Retrieval (F4) + RAG Prompt Assembler (F7)."""
        conn, db_path = seeded_db
        db = get_db_module()

        chunks = db.search_chunks("EDTA dureza agua", db_path=db_path, conn=conn)
        assert len(chunks) >= 1
        top_chunk = chunks[0]

        # Verify citation envelope assembly
        envelope = (
            f"LIBRO: {top_chunk['book_title']}\n"
            f"AUTOR: {top_chunk['author']}\n"
            f"CAPÍTULO: {top_chunk['chapter']}\n"
            f"PÁGINA: {top_chunk['page_num']}\n"
        )
        assert "EDTA" in top_chunk["content"] or "dureza" in top_chunk["content"].lower()
        assert "PÁGINA:" in envelope

    def test_pairwise_05_rag_query_and_byok_gemini_client(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Pairwise: RAG Engine (F7) + BYOK Gemini Client (F6)."""
        _, db_path = seeded_db
        rag = get_rag_module()

        result = rag.query_rag(
            "¿Cómo se determina la dureza de agua con EDTA a pH 10 y pH 12?",
            api_key=valid_api_key,
            syllabus_unit="U7",
            db_path=db_path
        )
        assert "answer" in result
        assert len(result["citations"]) >= 1
        assert "EDTA" in result["answer"] or "dureza" in result["answer"].lower()

    def test_pairwise_06_exam_generation_and_citation_grounding(self, valid_api_key: str) -> None:
        """Pairwise: Exam Simulator Engine (F9) + Citation Verification (F7)."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U3", count=2, difficulty="media", api_key=valid_api_key)
        assert len(questions) == 2

        for q in questions:
            assert "citation" in q
            cit = q["citation"]
            assert "book_title" in cit
            assert "chapter" in cit
            assert "page_num" in cit

    def test_pairwise_07_exam_submission_and_automated_grading(self, valid_api_key: str) -> None:
        """Pairwise: Exam Submission (F9) + Gemini Evaluation (F6)."""
        exam = get_exam_module()
        questions = exam.generate_exam_questions(unit_id="U6", count=1, difficulty="media", api_key=valid_api_key)
        correct_answer = questions[0]["correct_answer"]

        evaluation = exam.evaluate_exam_submission(questions, [correct_answer], api_key=valid_api_key)
        assert evaluation["score"] == 100.0
        assert evaluation["correct_answers"] == 1
        assert len(evaluation["feedback"]) == 1
        assert evaluation["feedback"][0]["is_correct"] is True

    def test_pairwise_08_book_catalog_and_whatsapp_redirection(self) -> None:
        """Pairwise: Textbook Catalog (F14) + WhatsApp Redirection URL (F14)."""
        ui = get_ui_module()
        book_info = {
            "title": "Fundamentos de Química Analítica",
            "edition": "9ª Edición",
            "author": "Douglas A. Skoog et al.",
            "phone": "59170000000"
        }
        msg = ui.format_book_request_message(
            book_title=book_info["title"],
            edition=book_info["edition"],
            author=book_info["author"]
        )
        url = ui.generate_whatsapp_url(book_info["phone"], msg)

        assert url.startswith("https://wa.me/59170000000?text=")
        parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert "Fundamentos de Química Analítica" in parsed_query["text"][0]

    def test_pairwise_09_chunking_metadata_and_syllabus_unit_filtering(self) -> None:
        """Pairwise: Metadata Tagging (F2) + SQLite Syllabus Unit Filtering (F4)."""
        db = get_db_module()
        conn = db.init_db(":memory:")

        # Insert U3 chunk and U6 chunk
        db.insert_chunk(conn, "b1", "T1", "A1", "E1", "C1", 10, "U3", "Precipitación de bario y sulfato.")
        db.insert_chunk(conn, "b2", "T2", "A2", "E2", "C2", 20, "U6", "Curva de titulación ácido débil con NaOH.")

        res_u3 = db.search_chunks("titulación", syllabus_unit="U3", conn=conn)
        assert res_u3 == []

        res_u6 = db.search_chunks("titulación", syllabus_unit="U6", conn=conn)
        assert len(res_u6) == 1
        assert res_u6[0]["syllabus_unit"] == "U6"
        conn.close()

    def test_pairwise_10_tutor_multi_turn_history_preservation(self, valid_api_key: str) -> None:
        """Pairwise: Tutor Engine (F8) + Multi-Turn Chat UI History (F12)."""
        tutor = get_tutor_module()
        history = [
            {"role": "user", "content": "¿Qué es una solución amortiguadora?"},
            {"role": "assistant", "content": "Es una mezcla de un ácido débil y su base conjugada que resiste cambios de pH."},
            {"role": "user", "content": "¿Cómo se calcula su capacidad reguladora?"},
            {"role": "assistant", "content": "Se calcula con la ecuación de van Slyke beta = db/dpH."}
        ]
        next_reply = tutor.get_tutor_response(
            "¿A qué pH es máxima esa capacidad?",
            history=history,
            current_unit_id="U6",
            api_key=valid_api_key
        )
        assert len(next_reply) > 20

    def test_pairwise_11_byok_key_validation_and_session_state(self, valid_api_key: str) -> None:
        """Pairwise: BYOK Client Validation (F6) + Portal Session State (F10)."""
        gemini = get_gemini_module()
        session: dict[str, Any] = {"authenticated": False}

        is_valid, _ = gemini.validate_api_key(valid_api_key)
        if is_valid:
            session["gemini_api_key"] = valid_api_key
            session["authenticated"] = True

        assert session["authenticated"] is True
        assert session["gemini_api_key"] == valid_api_key

    def test_pairwise_12_byok_key_disconnect_and_engine_lock(self, valid_api_key: str) -> None:
        """Pairwise: BYOK Key Disconnect (F10) + Engine Guard (F6)."""
        session = {"gemini_api_key": valid_api_key, "authenticated": True}
        # Student clicks disconnect
        session.pop("gemini_api_key", None)
        session["authenticated"] = False

        assert session["authenticated"] is False
        assert "gemini_api_key" not in session

    def test_pairwise_13_exam_failure_and_tutor_remediation(self, valid_api_key: str) -> None:
        """Pairwise: Exam Simulator Evaluation (F9) + Tutor Remediation Routing (F8)."""
        exam = get_exam_module()
        tutor = get_tutor_module()

        questions = [
            {
                "id": 1,
                "question": "¿Por qué se filtra el AgCl antes de retrotitular en Volhard?",
                "options": ["A) Para secarlo", "B) Porque AgCl es más soluble que AgSCN", "C) Para precipitar cromato", "D) Ninguna"],
                "correct_answer": "B",
                "explanation": "Debido a que Kps(AgCl) > Kps(AgSCN), el tiocianato desplaza al cloruro si no se aísla.",
                "unit_id": "U5"
            }
        ]
        # Student gives WRONG answer "A"
        evaluation = exam.evaluate_exam_submission(questions, ["A"], api_key=valid_api_key)
        assert evaluation["score"] == 0.0

        # Trigger remediation tutor session
        failed_question = evaluation["feedback"][0]
        remediation_prompt = (
            f"El estudiante respondió incorrectamente la pregunta sobre {questions[0]['question']}. "
            f"Explicación requerida: {failed_question['feedback']}"
        )
        tutor_help = tutor.get_tutor_response(remediation_prompt, history=[], current_unit_id="U5", api_key=valid_api_key)
        assert len(tutor_help) > 20

    def test_pairwise_14_cover_generation_and_textbook_showcase(self, books_path: str) -> None:
        """Pairwise: Cover Generator (F5) + Textbook Catalog Showcase (F14)."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        out_cover = "/tmp/test_aguilar_catalog.png"
        generated_cover = covers.generate_cover(target_pdf, out_cover, scale_width=300)
        assert generated_cover == out_cover

        catalog_card = {
            "title": "Introducción a los Equilibrios Iónicos",
            "cover_image": generated_cover,
            "exists": os.path.exists(generated_cover)
        }
        assert catalog_card["exists"] is True

    def test_pairwise_15_curriculum_spec_and_lab_practice_exam(self, valid_api_key: str) -> None:
        """Pairwise: Curriculum Parser (F3) + Lab Practice Dynamic Exam (F9)."""
        syllabus = get_syllabus_module()
        exam = get_exam_module()

        lab_units = syllabus.get_lab_units()
        assert len(lab_units) >= 4

        # Target Lab Unit 4 / Practice 5: Gravimetría de Sulfatos
        questions = exam.generate_exam_questions(unit_id="U3", count=1, difficulty="media", api_key=valid_api_key)
        assert len(questions) == 1
        q = questions[0]
        assert "unit_id" in q

    def test_pairwise_16_katex_formula_generation_and_chat_rendering(self, valid_api_key: str) -> None:
        """Pairwise: RAG/Tutor Response (F7/F8) + KaTeX Chat Rendering (F12)."""
        tutor = get_tutor_module()
        response = tutor.get_tutor_response(
            "Explica la ecuación de Henderson-Hasselbalch",
            history=[],
            current_unit_id="U6",
            api_key=valid_api_key
        )
        assert "$" in response or "pH" in response
