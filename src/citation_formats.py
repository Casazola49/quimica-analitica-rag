"""
src/citation_formats.py - Render verified citations as a formatted bibliography.

A teacher who wants to justify an answer needs something they can paste into a
report, and retyping author/title/edition/page by hand is exactly the friction
that makes people skip citing. The portal already holds verified metadata for
each source, so the bibliography is a formatting job, not a research one.

Three styles are offered because the audience decides: APA 7 for social
sciences, MLA 9 for humanities, IEEE for engineering and chemistry papers.

Every field here comes from the chunk that was actually retrieved, so the
excerpt and the page number are ground truth. Only the year and the publisher
are genuinely absent from the index, and those are rendered with the correct
convention for "no date" rather than invented.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

STYLES = ("APA", "MLA", "IEEE")

# A citation entry as produced by src.rag.extract_citations.
Citation = dict


def _clean(value: Optional[object]) -> str:
    """Normalises whitespace and drops empty placeholders."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_authors(author_str: Optional[str]) -> list[tuple[str, str]]:
    """
    Splits an author string into ``(surname, initials)`` pairs.

    The index stores authors as "Douglas A. Skoog, Donald M. West". The last
    whitespace-separated token of each comma-separated name is the surname and
    everything before it is given names, which is enough for the Latin-script
    names this index holds.

    Args:
        author_str: Raw author string from the citation.

    Returns:
        A list of ``(surname, initials)`` pairs, empty when nothing parses.
    """
    parsed: list[tuple[str, str]] = []
    for chunk in _clean(author_str).split(","):
        parts = chunk.split()
        if len(parts) < 2:
            if len(parts) == 1 and parts[0].endswith("."):
                continue
            continue
        surname = parts[-1].strip(" .")
        given = parts[:-1]
        initials = " ".join(f"{p[0]}." for p in given if p and p[0].isalpha())
        if surname:
            parsed.append((surname, initials))
    return parsed


def _strip_trailing_period(text: str) -> str:
    """Removes a trailing period so a formatter can add its own."""
    return text[:-1] if text.endswith(".") else text


def _page_range(citation: Citation) -> str:
    """Returns the page locator, or an empty string when the source has none."""
    page = citation.get("page_num")
    return f"p. {page}" if page else ""


_EDITION_RE = re.compile(
    r"^\s*(\d+)\s*(?:ª|°|a|th|st|nd|rd)?\s*(?:edici[oó]n|edition|ed)\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\((\d{4})\)")


def _split_edition(edition_str: Optional[str]) -> tuple[str, Optional[str]]:
    """
    Splits the stored edition label into a citation form and a year.

    The index stores values like "9ª Edición (2015)" or "6th Edition (1991)".
    The year is real data that was being thrown away, which forced APA to fall
    back to "sin fecha" for books that do have one.

    Args:
        edition_str: Raw edition string from the citation.

    Returns:
        ``(edition_label, year_or_None)``. The label is normalised to the
        numeric form the styles expect.
    """
    text = _clean(edition_str)
    if not text:
        return "", None

    year_match = _YEAR_RE.search(text)
    year = year_match.group(1) if year_match else None

    match = _EDITION_RE.match(text)
    if match:
        number = match.group(1)
        ordinal = re.match(r"^\d+\s*([a-zª°]{1,2})\b", text, re.IGNORECASE)
        suffix = (ordinal.group(1) if ordinal else "").lower()
        return f"{number}{suffix} ed.", year
    return text, year


def _locator(citation: Citation) -> str:
    """Chapter and page locator, in the shape the styles want."""
    bits = []
    chapter = _clean(citation.get("chapter"))
    if chapter and chapter.lower() != "capítulo general":
        bits.append(_strip_trailing_period(chapter))
    page = _page_range(citation)
    if page:
        bits.append(page)
    return ", ".join(bits)


def format_apa(citation: Citation) -> str:
    """
    Formats one source as an APA 7 reference.

    Args:
        citation: A citation dict from extract_citations.

    Returns:
        The reference string. The publication year is recovered from the stored
        edition label; only when it is genuinely absent does the entry carry
        ``s. f.``, rather than inventing a date.
    """
    authors = _parse_authors(citation.get("author"))
    if not authors:
        who = _clean(citation.get("author")) or "Autor desconocido"
    elif len(authors) == 1:
        who = f"{authors[0][0]}, {authors[0][1]}"
    else:
        joined = ", ".join(f"{s}, {i}" for s, i in authors[:-1])
        who = f"{joined}, & {authors[-1][0]}, {authors[-1][1]}"
    if len(authors) > 3:
        who = f"{authors[0][0]}, {authors[0][1]}, et al."

    title = _strip_trailing_period(_clean(citation.get("book_title")))
    edition, year = _split_edition(citation.get("edition"))
    locator = _locator(citation)

    reference = f"{who} ({year or 's. f.'}). *{title}*"
    details = [d for d in (edition, locator) if d]
    if details:
        reference += f" ({', '.join(details)})"
    return reference + "."


def format_mla(citation: Citation) -> str:
    """
    Formats one source as an MLA 9 works-cited entry.

    Args:
        citation: A citation dict from extract_citations.

    Returns:
        The entry string.
    """
    authors = _parse_authors(citation.get("author"))
    if not authors:
        who = _clean(citation.get("author")) or "Autor desconocido"
    elif len(authors) == 1:
        who = authors[0][0]
    elif len(authors) == 2:
        who = f"{authors[0][0]}, y {authors[1][0]}"
    else:
        who = f"{authors[0][0]}, y otros."

    title = _strip_trailing_period(_clean(citation.get("book_title")))
    edition, year = _split_edition(citation.get("edition"))
    locator = _locator(citation)

    entry = f"{_strip_trailing_period(who)}. *{title}*"
    details = [d for d in (edition, year, locator) if d]
    if details:
        entry += f". {', '.join(details)}"
    return entry + "."


def format_ieee(citation: Citation) -> str:
    """
    Formats one source as an IEEE reference.

    Args:
        citation: A citation dict from extract_citations.

    Returns:
        The entry string, without a bracketed index so the caller can number it.
    """
    authors = _parse_authors(citation.get("author"))
    if authors:
        # IEEE prints initials before the surname and joins with "and".
        who = " and ".join(f"{i} {s}".strip() for s, i in authors) or "Autor desconocido"
    else:
        who = _clean(citation.get("author")) or "Autor desconocido"

    title = _clean(citation.get("book_title"))
    edition, year = _split_edition(citation.get("edition"))
    locator = _locator(citation)

    entry = f"{who}, *{title}*"
    details = [d for d in (edition, year, locator) if d]
    if details:
        entry += f", {', '.join(details)}"
    return entry + "."


_FORMATTERS = {"APA": format_apa, "MLA": format_mla, "IEEE": format_ieee}


def format_bibliography(
    citations: Iterable[Citation],
    style: str = "APA",
    numbered: bool = False,
) -> list[str]:
    """
    Formats a list of citations and removes duplicates.

    Args:
        citations: Citations from a tutor or exam answer.
        style: One of STYLES, case-insensitive.
        numbered: Prefix IEEE-style entries with ``[1]``, ``[2]``, ... Useful
            when the list is meant for a "Referencias" section.

    Returns:
        One formatted string per distinct source, in a stable order.

    Raises:
        ValueError: If style is not one of STYLES.
    """
    formatter = _FORMATTERS.get(str(style).upper())
    if formatter is None:
        raise ValueError(f"Unsupported citation style: {style!r}. Use one of {STYLES}.")

    seen: set[str] = set()
    entries: list[str] = []
    for citation in citations:
        if not citation:
            continue
        text = formatter(citation)
        if text in seen:
            continue
        seen.add(text)
        entries.append(text)

    if numbered:
        return [f"[{i}] {e}" for i, e in enumerate(entries, start=1)]
    return entries
