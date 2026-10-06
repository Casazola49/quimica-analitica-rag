"""
test_grounding.py - Attaching book evidence to each part of an answer.

These tests encode the promise the portal makes to an instructor: a section is
either backed by a passage the retriever actually supplied, or it is labelled as
not backed. Nothing here trusts the model to say where its own claims came from.
"""

import pytest

from src.grounding import (
    SUPPORT_THRESHOLD,
    SUPPORTED,
    UNSUPPORTED,
    analyze_grounding,
    compact_grounding,
    grounding_summary,
    section_support,
    split_sections,
    strip_inline_citations,
)

PASSAGE = (
    "En el análisis gravimétrico el precipitado se lava con una solución diluida "
    "de un electrolito volátil. El agua pura provoca peptización: las partículas "
    "coloidales regresan al estado disperso y atraviesan el filtro, reduciendo el "
    "rendimiento gravimétrico de ladeterminación."
)


def _chunk(content: str = PASSAGE, page: int = 307) -> dict:
    return {
        "book_title": "Fundamentos de Química Analítica",
        "author": "Douglas A. Skoog",
        "edition": "9ª Edición (2015)",
        "chapter": "Capítulo 12: Métodos de análisis gravimétrico",
        "page_num": page,
        "content": content,
    }


class TestSplitSections:
    def test_splits_on_headings(self) -> None:
        answer = "Intro text\n\n### Uno\nCuerpo uno\n\n### Dos\nCuerpo dos"
        sections = split_sections(answer)
        assert len(sections) == 3
        assert sections[0]["heading"] == ""
        assert sections[1]["heading"] == "### Uno"
        assert "Cuerpo uno" in sections[1]["body"]

    def test_empty_answer(self) -> None:
        assert split_sections("") == []
        assert split_sections(None) == []

    def test_no_headings_is_one_section(self) -> None:
        sections = split_sections("Solo texto sin encabezados.")
        assert len(sections) == 1
        assert sections[0]["body"].startswith("Solo texto")


class TestSectionSupport:
    def test_literal_reuse_is_supported(self) -> None:
        level, chunk, score = section_support(
            "El agua pura provoca peptización y las partículas coloidales "
            "atraviesan el filtro",
            [_chunk()],
        )
        assert level == SUPPORTED
        assert chunk is not None
        assert score >= SUPPORT_THRESHOLD

    def test_unrelated_content_is_not_supported(self) -> None:
        level, _, score = section_support(
            "El puente Golden Gate fue terminado en 1937 por ladivision "
            "Joseph Strauss y Charles Alton Ellis",
            [_chunk()],
        )
        assert level == UNSUPPORTED
        assert score < SUPPORT_THRESHOLD

    def test_no_passages(self) -> None:
        level, chunk, score = section_support("cualquier texto", [])
        assert level == UNSUPPORTED
        assert chunk is None
        assert score == 0.0

    def test_accents_do_not_block_a_match(self) -> None:
        """A student writing 'peptizacion' must match 'peptización'."""
        level, _, _ = section_support("la peptizacion del precipitado", [_chunk()])
        assert level == SUPPORTED

    def test_no_overlap_means_no_passage_is_claimed(self) -> None:
        """With zero shared vocabulary there is nothing to call 'closest'."""
        level, chunk, score = section_support(
            "Puente Golden Gate inaugurado en la bahía", [_chunk()]
        )
        assert level == UNSUPPORTED
        assert chunk is None
        assert score == 0.0


class TestInlineCitationsAreStripped:
    def test_model_citation_tags_are_removed(self) -> None:
        answer = (
            "El lavado evita la peptización. "
            "[Libro: Fundamentos de Química Analítica, Autor: Skoog, "
            "Edición: 9ª, Capítulo: 12, Página: 307]"
        )
        cleaned = strip_inline_citations(answer)
        assert "[Libro:" not in cleaned
        assert "peptización" in cleaned

    def test_several_tags_and_spacing(self) -> None:
        answer = "A [Libro: X, Página: 1] B [Libro: Y, Página: 2] C"
        cleaned = strip_inline_citations(answer)
        assert cleaned.count("[Libro:") == 0
        assert "  " not in cleaned

    def test_empty_input(self) -> None:
        assert strip_inline_citations("") == ""
        assert strip_inline_citations(None) == ""


class TestAnalyzeGrounding:
    ANSWER = (
        "El precipitado se lava con electrolito volátil.\n\n"
        "### Peptización\nEl agua pura provoca peptización y las partículas "
        "coloidales atraviesan el filtro.\n\n"
        "### Historia del puente\nFue inaugurado en 1937 en la bahía de San Francisco."
    )

    def test_mixed_answer_labels_each_section(self) -> None:
        grounded = analyze_grounding(self.ANSWER, [_chunk()])
        levels = {g["heading"]: g["level"] for g in grounded}
        assert levels["### Peptización"] == SUPPORTED
        assert levels["### Historia del puente"] == UNSUPPORTED

    def test_unsupported_sections_are_kept_not_dropped(self) -> None:
        """Hiding them would defeat the purpose of the feature."""
        grounded = analyze_grounding(self.ANSWER, [_chunk()])
        assert len(grounded) == 3

    def test_summary_counts(self) -> None:
        summary = grounding_summary(analyze_grounding(self.ANSWER, [_chunk()]))
        assert summary["total"] == 3
        assert summary["unsupported"] == 1
        assert summary["supported"] == 2
        assert summary["coverage"] == pytest.approx(2 / 3, abs=0.01)

    def test_summary_of_nothing(self) -> None:
        assert grounding_summary([]) == {
            "total": 0, "supported": 0, "unsupported": 0, "coverage": 0.0,
        }


class TestCompactGrounding:
    def test_keeps_evidence_for_the_history_rendering(self) -> None:
        """Scrolling back up must show the same evidence, not a bare answer."""
        answer = "### Peptización\nEl agua pura provoca peptización y las partículas atraviesan el filtro."
        stored = compact_grounding(answer, [_chunk()])
        assert stored[0]["evidence"]["page_num"] == 307
        assert stored[0]["evidence"]["book_title"].startswith("Fundamentos")
        assert "peptización" in stored[0]["evidence"]["content"]

    def test_unsupported_section_has_no_evidence(self) -> None:
        stored = compact_grounding("Puente Golden Gate inaugurado en 1937.", [_chunk()])
        assert stored[0]["level"] == UNSUPPORTED
        assert stored[0]["evidence"] is None

    def test_inline_citations_are_already_gone(self) -> None:
        answer = "### A\nEl agua pura provoca peptización [Libro: X, Página: 9]"
        stored = compact_grounding(strip_inline_citations(answer), [_chunk()])
        assert "[Libro:" not in stored[0]["body"]