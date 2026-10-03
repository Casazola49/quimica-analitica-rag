"""
test_citation_fidelity.py - Regression tests for citation correctness.

A teaching tool is only trustworthy if a cited book and page point at the real
book. These tests lock in the two failure modes that broke that promise:

1. Canonical resolution must not let a shared author alias override the title.
   Every Skoog volume shares Holler and Crouch, so an alias matched against the
   author string used to send every Skoog title to whichever entry came first,
   relabelling "Principios de Analisis Instrumental" as "Fundamentos de Quimica
   Analitica".
2. Citations derived from an indexed chunk must keep the chunk's own verified
   metadata; canonical entries may only fill gaps, never rewrite it.
"""

import re

import pytest

from src.rag import _find_canonical_book, extract_citations

FUNDAMENTALS = "Fundamentos de Química Analítica"
INSTRUMENTAL = "Principios de Análisis Instrumental"
SKOOG_INSTRUMENTAL_AUTHOR = "Douglas A. Skoog, F. James Holler, Stanley R. Crouch"
SKOOG_FUNDAMENTALS_AUTHOR = (
    "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch"
)


def _norm(text: str) -> str:
    """Collapse whitespace so excerpts compare against stored chunk text."""
    return re.sub(r"\s+", " ", text or "").strip()


class TestCanonicalBookResolution:
    """The title must win over a shared author alias."""

    @pytest.mark.parametrize(
        "title,author,expected_id",
        [
            (
                INSTRUMENTAL,
                SKOOG_INSTRUMENTAL_AUTHOR,
                "skoog_instrumental_7ed_es",
            ),
            (FUNDAMENTALS, SKOOG_FUNDAMENTALS_AUTHOR, "skoog_9ed_es"),
            (
                "Fundamentals of Analytical Chemistry",
                SKOOG_FUNDAMENTALS_AUTHOR,
                "skoog_10ed_en",
            ),
            (
                "Introducción a los Equilibrios Iónicos",
                "Rafael Aguilar",
                "aguilar_2ed_es",
            ),
            (
                "Quantitative Analysis",
                "R. A. Day, Jr., A. L. Underwood",
                "day_underwood_6ed_en",
            ),
        ],
    )
    def test_resolves_each_title_to_its_own_book(
        self, title: str, author: str, expected_id: str
    ) -> None:
        """Each course textbook resolves to its own canonical entry."""
        match = _find_canonical_book(title, author)
        assert match is not None, f"no canonical match for {title!r}"
        assert match["id"] == expected_id

    def test_sibling_skoog_volumes_are_not_conflated(self) -> None:
        """The regression: both Skoog titles share an author, so alias matching
        on the author used to resolve either one to skoog_9ed_es."""
        instrumental = _find_canonical_book(INSTRUMENTAL, SKOOG_INSTRUMENTAL_AUTHOR)
        fundamentals = _find_canonical_book(FUNDAMENTALS, SKOOG_FUNDAMENTALS_AUTHOR)
        assert instrumental["id"] != fundamentals["id"]
        assert instrumental["title"] == INSTRUMENTAL
        assert fundamentals["title"] == FUNDAMENTALS

    def test_title_match_survives_an_empty_author(self) -> None:
        """A known title resolves even with no author supplied."""
        match = _find_canonical_book(INSTRUMENTAL, "")
        assert match is not None
        assert match["id"] == "skoog_instrumental_7ed_es"

    def test_empty_title_returns_none(self) -> None:
        """No title means no resolution rather than a guess."""
        assert _find_canonical_book("", "Skoog") is None
        assert _find_canonical_book("   ", "") is None


class TestChunkCitationsKeepTheirMetadata:
    """Indexed chunks are ground truth and must not be relabelled."""

    def test_chunk_citation_keeps_its_own_book_title(self) -> None:
        """A chunk from the Instrumental volume stays attributed to it.

        This is the path that broke before: canonical entries were allowed to
        rewrite an indexed chunk's metadata, so the Instrumental volume was
        relabelled as the Fundamentals textbook.
        """
        chunk = {
            "book_title": INSTRUMENTAL,
            "author": SKOOG_INSTRUMENTAL_AUTHOR,
            "edition": "7ª Edición (2019)",
            "chapter": "Capítulo 23: Potenciometría",
            "page_num": 632,
            "content": "El potencial estándar de oxidación se define como E°.",
        }
        citations = extract_citations("respuesta del modelo sin citas", [chunk])

        matching = [c for c in citations if c["page_num"] == 632]
        assert matching, "the chunk citation was dropped"
        assert matching[0]["book_title"] == INSTRUMENTAL
        assert matching[0]["author"] == SKOOG_INSTRUMENTAL_AUTHOR
        assert matching[0]["edition"] == "7ª Edición (2019)"

    def test_chunk_citation_does_not_raise(self) -> None:
        """The from_chunk branch executes without an UnboundLocalError.

        extract_citations reaches add_citation with from_chunk=True for every
        chunk, so this exercises the branch directly rather than inferring it.
        """
        chunk = {
            "book_title": FUNDAMENTALS,
            "author": SKOOG_FUNDAMENTALS_AUTHOR,
            "edition": "9ª Edición (2015)",
            "chapter": "Capítulo 18",
            "page_num": 482,
            "content": "E = E0 - (RT/nF) ln Q describe el potencial de Nernst.",
        }
        citations = extract_citations("texto del modelo", [chunk])
        assert citations
        assert citations[0]["page_num"] == 482

    def test_chunk_excerpt_comes_from_the_chunk(self) -> None:
        """The excerpt shown to the reader is the stored text, not model prose."""
        body = "La ecuación de Nernst relaciona el potencial con el logaritmo del cociente."
        chunk = {
            "book_title": FUNDAMENTALS,
            "author": SKOOG_FUNDAMENTALS_AUTHOR,
            "edition": "9ª Edición (2015)",
            "chapter": "Capítulo 18",
            "page_num": 491,
            "content": body,
        }
        citations = extract_citations("", [chunk])
        assert citations[0]["excerpt"].startswith(_norm(body)[:40])

    def test_chapter_survives_for_display(self) -> None:
        """The chapter label reaches the citation card."""
        chunk = {
            "book_title": FUNDAMENTALS,
            "author": SKOOG_FUNDAMENTALS_AUTHOR,
            "edition": "9ª Edición (2015)",
            "chapter": "Capítulo 5: Errores en el análisis químico",
            "page_num": 107,
            "content": "El error relativo se expresa como porcentaje.",
        }
        citations = extract_citations("", [chunk])
        assert "Errores" in citations[0]["chapter"]
