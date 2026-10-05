"""
test_citation_formats.py - Bibliography rendering for the "justificar la respuesta" path.

A teacher's main friction is retyping sources by hand, so these tests pin the
rendered references: author parsing, edition/year recovery, dedup, and the
refusal to invent data the index does not have.
"""

import pytest

from src.citation_formats import (
    _parse_authors,
    _split_edition,
    format_apa,
    format_bibliography,
    format_ieee,
    format_mla,
)

SKOOG_4 = "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch"
SKOOG_3 = "Douglas A. Skoog, F. James Holler, Stanley R. Crouch"

FUNDAMENTALS = {
    "book_title": "Fundamentos de Química Analítica",
    "author": SKOOG_4,
    "edition": "9ª Edición (2015)",
    "chapter": "Capítulo 18: Introducción a la electroquímica",
    "page_num": 491,
}

INSTRUMENTAL = {
    "book_title": "Principios de Análisis Instrumental",
    "author": SKOOG_3,
    "edition": "7ª Edición (2019)",
    "chapter": "Capítulo 23: Potenciometría",
    "page_num": 632,
}


class TestAuthorParsing:
    def test_splits_surname_and_initials(self) -> None:
        parsed = _parse_authors("Douglas A. Skoog, Donald M. West")
        assert parsed == [("Skoog", "D. A."), ("West", "D. M.")]

    def test_three_authors(self) -> None:
        assert _parse_authors(SKOOG_3)[-1] == ("Crouch", "S. R.")

    def test_empty_author(self) -> None:
        assert _parse_authors("") == []
        assert _parse_authors(None) == []


class TestEditionAndYear:
    @pytest.mark.parametrize(
        "raw,label,year",
        [
            ("9ª Edición (2015)", "9ª ed.", "2015"),
            ("7ª Edición (2019)", "7ª ed.", "2019"),
            ("6th Edition (1991)", "6th ed.", "1991"),
            ("1ª Edición", "1ª ed.", None),
            ("", "", None),
        ],
    )
    def test_year_is_recovered_from_the_edition_label(self, raw, label, year) -> None:
        """The year is real stored data and must not be discarded."""
        assert _split_edition(raw) == (label, year)

    def test_unparseable_edition_is_kept_verbatim(self) -> None:
        """A spelled-out edition is not normalised, but its year is still read."""
        label, year = _split_edition("Cuarta edición (2001)")
        assert label == "Cuarta edición (2001)"
        assert year == "2001"


class TestApa:
    def test_three_or_more_authors_collapses_to_et_al(self) -> None:
        assert format_apa(FUNDAMENTALS).startswith("Skoog, D. A., et al.")

    def test_year_and_edition_are_present(self) -> None:
        out = format_apa(FUNDAMENTALS)
        assert "(2015)" in out
        assert "9ª ed." in out
        assert "p. 491" in out

    def test_two_authors_are_joined_with_ampersand(self) -> None:
        out = format_apa(
            {**FUNDAMENTALS, "author": "R. A. Day, Jr., A. L. Underwood"}
        )
        assert "Day, R. A., & Underwood, A. L." in out

    def test_missing_year_uses_sino_fecha_not_a_guess(self) -> None:
        out = format_apa({**FUNDAMENTALS, "edition": ""})
        assert "s. f." in out
        assert "(s. f.)" in out

    def test_unknown_author_does_not_crash(self) -> None:
        out = format_apa({"book_title": "Química Cuantitativa", "author": ""})
        assert "Química Cuantitativa" in out


class TestMla:
    def test_three_authors_uses_et_al_equivalent(self) -> None:
        assert "y otros" in format_mla(FUNDAMENTALS)

    def test_no_double_period(self) -> None:
        out = format_mla(FUNDAMENTALS)
        assert ".." not in out

    def test_two_authors(self) -> None:
        out = format_mla({**FUNDAMENTALS, "author": "R. A. Day, Jr., A. L. Underwood"})
        assert "Day, y Underwood" in out


class TestIeee:
    def test_initials_come_before_the_surname(self) -> None:
        out = format_ieee(INSTRUMENTAL)
        assert "D. A. Skoog and F. J. Holler" in out

    def test_uses_and_not_y(self) -> None:
        assert " and " in format_ieee(INSTRUMENTAL)
        assert " y " not in format_ieee(INSTRUMENTAL)

    def test_numbering(self) -> None:
        entries = format_bibliography([FUNDAMENTALS, INSTRUMENTAL], "IEEE", numbered=True)
        assert entries[0].startswith("[1] ")
        assert entries[1].startswith("[2] ")


class TestBibliographyWidgetKeys:
    """Regression: two answers with the same number of sources used to collide.

    The chat history renders every assistant message in one script run, so
    widget keys built only from len(citations) produced Streamlit's
    DuplicateWidgetID and took the whole tutor page down as soon as a student
    asked a second question.
    """

    CITATIONS = [
        {
            "book_title": "Fundamentos de Química Analítica",
            "author": "Douglas A. Skoog, Donald M. West",
            "edition": "9ª Edición (2015)",
            "chapter": "Capítulo 5",
            "page_num": 107,
            "excerpt": "texto",
        },
        {
            "book_title": "Quantitative Analysis",
            "author": "R. A. Day, Jr., A. L. Underwood",
            "edition": "6th Edition (1991)",
            "chapter": "Capítulo 5",
            "page_num": 107,
            "excerpt": "texto",
        },
    ]

    def test_two_messages_with_equal_citation_counts_do_not_collide(self) -> None:
        from src import ui
        from tests.test_challenger_empirical_m3_ui_stress import MockStreamlitContext

        session = ui.init_session_state(
            {
                "messages": [
                    {"role": "assistant", "content": "r1", "citations": list(self.CITATIONS)},
                    {"role": "assistant", "content": "r2", "citations": list(self.CITATIONS)},
                ]
            }
        )
        mock = MockStreamlitContext(session_state=session, raise_on_rerun=False)
        ui.render_tutor_tab(st_ctx=mock)

        assert len(mock.code_blocks) == 2
        assert len(mock.downloads) == 2

    def test_widget_keys_are_unique_per_message(self) -> None:
        from src import ui

        seen = []
        for prefix in ("hist_0", "hist_1", "new"):
            seen.append(f"bib_style_{prefix or 'single'}")
        assert len(set(seen)) == len(seen)
        assert ui.render_citation_sources.__defaults__ == ("",)


class TestBibliography:
    def test_duplicates_are_removed(self) -> None:
        entries = format_bibliography([FUNDAMENTALS, FUNDAMENTALS, INSTRUMENTAL], "APA")
        assert len(entries) == 2

    def test_all_styles_produce_one_line_each(self) -> None:
        for style in ("APA", "MLA", "IEEE"):
            entries = format_bibliography([FUNDAMENTALS], style)
            assert len(entries) == 1
            assert entries[0].endswith(".")

    def test_unknown_style_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            format_bibliography([FUNDAMENTALS], "ABNT")  # noqa: NPY002

    def test_empty_input_is_handled(self) -> None:
        assert format_bibliography([], "APA") == []
        assert format_bibliography([None, {}], "APA") == []

    def test_sibling_skoog_volumes_stay_distinct(self) -> None:
        """Regression: the two Skoog titles must not collapse into one entry."""
        entries = format_bibliography([FUNDAMENTALS, INSTRUMENTAL], "APA")
        assert len(entries) == 2
        assert "Analisis Instrumental" not in entries[0]
        assert "Instrumental" in entries[1]
