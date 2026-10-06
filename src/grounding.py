"""
src/grounding.py - Tie each part of an answer to the book passage behind it.

A tutor that cites a page the student cannot open is worse than one that cites
nothing, because it looks rigorous while being unverifiable. This module makes
the link explicit and, more importantly, makes the absence of a link visible.

An answer is split into its sections and each section is compared, word by word,
against the passages the retriever actually supplied. Two outcomes matter:

* supported -- the section's vocabulary is present in a passage, so the portal can
  name the book and page and offer the literal text.
* unsupported -- nothing in the passages backs it. That does not mean the claim
  is false, it means the books do not say it. Labelling it is the honest move and
  is exactly what an instructor needs in order to assess the answer.

The comparison is lexical and deterministic. The model is never asked where its
own claims came from, because that is the one thing it cannot be trusted to
answer.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

# Words at least this long carry meaning; shorter ones are mostly connectors.
_MIN_WORD_LEN = 5

# A section is treated as supported when at least this share of its distinctive
# words appears in the best-matching passage. The score is always shown next to
# the badge: this is a signal for the reader, not a verdict handed down by the
# system, because a well-written paraphrase scores lower than a literal quote.
SUPPORT_THRESHOLD = 0.25

SUPPORTED = "apoyada"
UNSUPPORTED = "sin_apoyo"


def _strip_accents(text: str) -> str:
    """Folds accents so 'gravimétrico' and 'gravimetrico' compare equal."""
    decomposed = unicodedata.normalize("NFD", str(text or ""))
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _words(text: str) -> set[str]:
    """Distinctive lowercased words of a text, accents folded."""
    folded = _strip_accents(text).lower()
    return {w for w in re.findall(r"[a-z]{%d,}" % _MIN_WORD_LEN, folded)}


def split_sections(answer: str) -> List[Dict[str, str]]:
    """
    Splits an answer into its sections on Markdown headings.

    Text before the first heading becomes a leading section so nothing is lost.

    Args:
        answer: The rendered answer.

    Returns:
        A list of ``{"heading": str, "body": str}`` in document order.
    """
    text = str(answer or "").strip()
    if not text:
        return []

    sections: List[Dict[str, str]] = []
    heading: Optional[str] = None
    buffer: List[str] = []

    for line in text.splitlines():
        if re.match(r"^\s{0,3}#{1,6}\s+\S", line):
            if heading is not None or any(b.strip() for b in buffer):
                sections.append({"heading": heading or "", "body": "\n".join(buffer).strip()})
            heading = line.strip()
            buffer = []
        else:
            buffer.append(line)

    if heading is not None or any(b.strip() for b in buffer):
        sections.append({"heading": heading or "", "body": "\n".join(buffer).strip()})

    return [s for s in sections if s["heading"] or s["body"]]


def section_support(
    section_body: str,
    chunks: List[Dict[str, Any]],
) -> Tuple[str, Optional[Dict[str, Any]], float]:
    """
    Measures how strongly one section is supported by the retrieved passages.

    Args:
        section_body: The text of the section.
        chunks: The passages the retriever supplied for this answer.

    Returns:
        ``(level, closest_chunk, score)`` where level is SUPPORTED or
        UNSUPPORTED and score is the share of the section's distinctive words
        found in the best passage. closest_chunk is the strongest matching
        passage for a weak section too, so the reader still sees what came
        nearest; it is None when nothing at all overlapped, because then there is
        genuinely no nearest passage to show.
    """
    section_words = _words(section_body)
    if not section_words or not chunks:
        return UNSUPPORTED, None, 0.0

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    for chunk in chunks:
        chunk_words = _words(chunk.get("content", ""))
        if not chunk_words:
            continue
        overlap = len(section_words & chunk_words)
        # Containment in the passage: how much of what we said is actually there.
        score = overlap / len(section_words)
        if score > best_score:
            best_score = score
            best = chunk

    level = SUPPORTED if best_score >= SUPPORT_THRESHOLD else UNSUPPORTED
    return level, best, round(best_score, 3)


def analyze_grounding(
    answer: str,
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Attaches an evidence card to every section of an answer.

    Args:
        answer: The rendered answer.
        chunks: The passages supplied to the model for this answer.

    Returns:
        One entry per section with its heading, body, support level, the passage
        that backs it (if any) and the match score. A section the books do not
        support is returned as well: hiding it would defeat the purpose.
    """
    results: List[Dict[str, Any]] = []
    for section in split_sections(answer):
        level, chunk, score = section_support(section["body"], chunks)
        results.append(
            {
                "heading": section["heading"],
                "body": section["body"],
                "level": level,
                "chunk": chunk,
                "score": score,
            }
        )
    return results


def compact_grounding(
    answer: str,
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Produces the storable form of the grounding analysis.

    The session has to remember what was shown, or scrolling back up would
    render the answer without its evidence and the student would no longer be
    able to check what they were given. Only the fields needed to render the
    card are kept, plus the passage text that backs it.

    Args:
        answer: The rendered answer.
        chunks: The passages supplied to the model.

    Returns:
        One dict per section: heading, body, level, score and, when a passage
        matched, the evidence reference and its literal text.
    """
    compact: List[Dict[str, Any]] = []
    for sec in analyze_grounding(answer, chunks):
        chunk = sec.get("chunk")
        compact.append(
            {
                "heading": sec["heading"],
                "body": sec["body"],
                "level": sec["level"],
                "score": sec["score"],
                "evidence": (
                    {
                        "book_title": chunk.get("book_title", ""),
                        "author": chunk.get("author", ""),
                        "edition": chunk.get("edition", ""),
                        "chapter": chunk.get("chapter", ""),
                        "page_num": chunk.get("page_num"),
                        "content": str(chunk.get("content", "")).strip(),
                    }
                    if chunk
                    else None
                ),
            }
        )
    return compact


def grounding_summary(grounded: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts supported and unsupported sections for the answer header."""
    total = len(grounded)
    supported = sum(1 for g in grounded if g["level"] == SUPPORTED)
    return {
        "total": total,
        "supported": supported,
        "unsupported": total - supported,
        "coverage": round(supported / total, 3) if total else 0.0,
    }


# Model-authored "[Libro: ..., Página: ...]" tags. They are never verified
# against the index, so showing them would put an unverifiable claim behind the
# appearance of a citation. Stripped from the text before it reaches the student.
_INLINE_CITATION_RE = re.compile(r"\[Libro:[^\]]*\]", re.IGNORECASE)


def strip_inline_citations(answer: str) -> str:
    """
    Removes the model's own inline citation tags from an answer.

    The verified references are rendered separately from the retrieved chunks, so
    keeping the model's tags only duplicates them with unverified page numbers.

    Args:
        answer: The raw answer text.

    Returns:
        The same text without inline citation tags, whitespace normalised.
    """
    cleaned = _INLINE_CITATION_RE.sub("", str(answer or ""))
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()