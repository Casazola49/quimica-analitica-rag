"""
src/ingestion.py - Streaming Bounded-Memory Textbook Ingestion & Chunker
for Química Analítica Educational Portal.

Features:
- Bounded memory streaming extraction via /usr/bin/pdftotext (<20 MB VmRSS).
- Line-by-line reading with form-feed ('\\x0c') page splitting.
- Word dehyphenation and text normalization.
- Chapter header detection with running-header parsing and TOC suppression.
- Sliding-window chunker (~1,000 characters, 150-character overlap) with smart boundary snapping.
- Syllabus unit metadata enrichment (fusing chapter matrix and ontology matching).
- Transactional batch insertion into SQLite FTS5 database (src/db.py).
"""

from __future__ import annotations

import os
import re
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Complete Course Textbook Catalog
BOOK_CATALOG = [
    {
        "id": "skoog_9ed_es",
        "filename": "Skoog_Fundamentos_de_Quimica_Analitica_9ed_ES.pdf",
        "title": "Fundamentos de Química Analítica",
        "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "edition": "9ª Edición (2015)",
        "language": "es",
        "total_pages": 1090,
        "is_scanned": False,
        "cover_page": 2,
        "default_syllabus_unit": "U1",
    },
    {
        "id": "aguilar_2ed_es",
        "filename": "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf",
        "title": "Introducción a los Equilibrios Iónicos",
        "authors": "Manuel Aguilar San Juan",
        "edition": "2ª Edición (2000)",
        "language": "es",
        "total_pages": 538,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "U6",
    },
    {
        "id": "day_underwood_6ed_en",
        "filename": "Day_Underwood_Quantitative_Analysis_6ed_EN.pdf",
        "title": "Quantitative Analysis",
        "authors": "R. A. Day, Jr., A. L. Underwood",
        "edition": "6th Edition (1991)",
        "language": "en",
        "total_pages": 712,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "L5",
    },
    {
        "id": "skoog_solutions_10ed_en",
        "filename": "Skoog_Fundamentals_of_Analytical_Chemistry_Solutions_Manual_10ed_EN.pdf",
        "title": "Student Solutions Manual: Fundamentals of Analytical Chemistry",
        "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "edition": "10th Edition (2022)",
        "language": "en",
        "total_pages": 233,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "U2",
    },
    {
        "id": "skoog_instrumental_7ed_es",
        "filename": "Skoog_Principios_de_Analisis_Instrumental_7ed_ES.pdf",
        "title": "Principios de Análisis Instrumental",
        "authors": "Douglas A. Skoog, F. James Holler, Stanley R. Crouch",
        "edition": "7ª Edición (2019)",
        "language": "es",
        "total_pages": 888,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "L7",
    },
    {
        "id": "skoog_10ed_en",
        "filename": "Skoog_Fundamentals_of_Analytical_Chemistry_10ed_EN.pdf",
        "title": "Fundamentals of Analytical Chemistry",
        "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "edition": "10th Edition (2022)",
        "language": "en",
        "total_pages": 1165,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "U1",
    },
    {
        "id": "kolthoff_vol1_2ed_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol1_2ed_EN.pdf",
        "title": "Treatise on Analytical Chemistry: Theory and Practice (Vol. 1)",
        "authors": "I. M. Kolthoff, Philip J. Elving, Edward J. Meehan",
        "edition": "2nd Edition (1978)",
        "language": "en",
        "total_pages": 920,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "U2",
    },
    {
        "id": "kolthoff_vol5_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol5_EN.pdf",
        "title": "Treatise on Analytical Chemistry: Optical Methods (Vol. 5)",
        "authors": "I. M. Kolthoff, Philip J. Elving, Ernest B. Sandell",
        "edition": "1st Edition",
        "language": "en",
        "total_pages": 672,
        "is_scanned": False,
        "cover_page": 1,
        "default_syllabus_unit": "L7",
    },
    {
        "id": "day_underwood_5ed_es",
        "filename": "Day_Underwood_Quimica_Analitica_Cuantitativa_5ed_ES.pdf",
        "title": "Química Analítica Cuantitativa",
        "authors": "R. A. Day, Jr., A. L. Underwood",
        "edition": "5ª Edición (1989)",
        "language": "es",
        "total_pages": 870,
        "is_scanned": True,
        "cover_page": 1,
        "default_syllabus_unit": "L5",
    },
    {
        "id": "kolthoff_vol2_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol2_EN.pdf",
        "title": "Treatise on Analytical Chemistry: Part 1, Vol. 2",
        "authors": "I. M. Kolthoff, Philip J. Elving",
        "edition": "1st Edition",
        "language": "en",
        "total_pages": 1322,
        "is_scanned": True,
        "cover_page": 1,
        "default_syllabus_unit": "L2",
    },
    {
        "id": "kolthoff_vol3_2ed_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol3_2ed_EN.pdf",
        "title": "Treatise on Analytical Chemistry: Part 1, Vol. 3",
        "authors": "I. M. Kolthoff, Philip J. Elving",
        "edition": "2nd Edition",
        "language": "en",
        "total_pages": 613,
        "is_scanned": True,
        "cover_page": 1,
        "default_syllabus_unit": "U8",
    },
]

# Chapter-to-Syllabus Mapping Matrix for Skoog 9ed
SKOOG_9ED_CHAPTER_MAP = {
    1: "U1",
    2: "L1",
    3: "U2",
    4: "U1",
    5: "U2",
    6: "U2",
    7: "U2",
    8: "U1",
    9: "U6",
    10: "U2",
    11: "U6",
    12: "U3",
    13: "U1",
    14: "U6",
    15: "U6",
    16: "U6",
    17: "U7",
    18: "U8",
    19: "U8",
    20: "U9",
    21: "L6",
    22: "L6",
    23: "L6",
    24: "L7",
    25: "L7",
    26: "L7",
    27: "L7",
    28: "L8",
    29: "L7",
    30: "U1",
    31: "U1",
    32: "U1",
    33: "U1",
    34: "U1",
    35: "U1",
    36: "L2",
    37: "L2",
    38: "L5",
}

# Chapter-to-Syllabus Mapping Matrix for Aguilar 2ed
AGUILAR_CHAPTER_MAP = {
    1: "U6",
    2: "U6",
    3: "U6",
    4: "U6",
    5: "U3",
    6: "U5",
    7: "U7",
    8: "U7",
    9: "U8",
}

# Chapter-to-Syllabus Mapping Matrix for Day & Underwood 6ed
DAY_UNDERWOOD_CHAPTER_MAP = {
    1: "U1",
    2: "U2",
    3: "U1",
    4: "U3",
    5: "U6",
    6: "U6",
    7: "U6",
    8: "U7",
    9: "U4",
    10: "U8",
    11: "U9",
    12: "L6",
    13: "L6",
    14: "L7",
    15: "L7",
    16: "L7",
    17: "U1",
    18: "U1",
    19: "U1",
}


def stream_pdf_text(pdf_path: str) -> Iterator[Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF using poppler's pdftotext stdout streaming.
    Yields dicts with 'page_num' (1-indexed) and 'text'.
    Peak memory remains strictly bounded (< 20 MB).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # If file is empty (0 bytes), return empty generator
    if os.path.getsize(pdf_path) == 0:
        return

    cmd = ["pdftotext", str(pdf_path), "-"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=65536
        )
    except Exception as e:
        logger.warning(f"Failed to spawn pdftotext for {pdf_path}: {e}")
        return

    page_num = 1
    page_chunks: List[str] = []

    try:
        if proc.stdout:
            for line in proc.stdout:
                if "\x0c" in line:
                    parts = line.split("\x0c")
                    page_chunks.append(parts[0])
                    yield {"page_num": page_num, "text": "".join(page_chunks)}
                    page_num += 1

                    for mid in parts[1:-1]:
                        yield {"page_num": page_num, "text": mid}
                        page_num += 1

                    page_chunks = [parts[-1]]
                else:
                    page_chunks.append(line)

            if page_chunks and "".join(page_chunks).strip():
                yield {"page_num": page_num, "text": "".join(page_chunks)}
    finally:
        if proc.stdout:
            try:
                proc.stdout.close()
            except Exception:
                pass
        proc.wait()


def stream_pdf_pages(pdf_path: str) -> Iterator[Tuple[int, str]]:
    """
    Tuple generator interface for streaming pages: yields (page_num, text).
    """
    for item in stream_pdf_text(pdf_path):
        yield item["page_num"], item["text"]


def clean_page_text(text: str) -> str:
    """
    Cleans extracted page text:
    - Removes non-printable control characters (preserves \\n and \\t).
    - Dehyphenates words broken across line ends (e.g. 'com-\\nplejos' -> 'complejos').
    - Normalizes multiple blank lines.
    """
    if not text:
        return ""
    # Remove control characters
    text = "".join(c for c in text if c in "\n\t" or ord(c) >= 32)
    # Dehyphenate words broken across line breaks
    text = re.sub(r"([A-Za-zÁÉÍÓÚáéíóúñ]+)-\n([A-Za-zÁÉÍÓÚáéíóúñ]+)", r"\1\2", text)
    # Reflow excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_chapter(page_text: str, current_chapter: str, book_meta: dict, page_num: int) -> str:
    """
    Detects chapter transitions from page running headers, titles, or static fallbacks.
    Suppresses false transitions on Table of Contents (TOC) pages.
    """
    if not page_text:
        return current_chapter

    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    if not lines:
        return current_chapter

    # 1. TOC Suppression Heuristics
    markers_count = len(re.findall(r"(?:cap[ií]tulo|chapter)\s+\d+", page_text, re.IGNORECASE))
    if markers_count >= 3:
        return current_chapter

    top_block = " ".join(lines[:4]).upper()
    if any(k in top_block for k in ["CONTENIDO", "ÍNDICE", "CONTENTS", "TABLE OF CONTENTS"]):
        return current_chapter

    # 2. Check Header Lines (Lines 0 to 6)
    for i, line in enumerate(lines[:7]):
        m = re.search(r"(?:^|\b)(?:CAP[IÍ]TULO|CHAPTER)\s+(\d+)(?:[:\.\s\-\–/|]+([^\n\r]+))?", line, re.IGNORECASE)
        if m:
            c_num = int(m.group(1))
            c_title = m.group(2).strip() if m.group(2) else ""
            if not c_title and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not re.search(r"(?:CAP[IÍ]TULO|CHAPTER)", next_line, re.IGNORECASE) and len(next_line) < 100:
                    c_title = next_line
            return f"Capítulo {c_num}" + (f": {c_title}" if c_title else "")

        m_abbr = re.search(r"(?:^|\b)CAP\.?\s*(\d+)\s+([A-Za-zÁÉÍÓÚáéíóúñ\s]{3,60})", line, re.IGNORECASE)
        if m_abbr:
            c_num = int(m_abbr.group(1))
            c_title = m_abbr.group(2).strip()
            return f"Capítulo {c_num}: {c_title}"

    # 3. Check Running Footer Lines
    for line in lines[-4:]:
        m_foot = re.search(r"CAP\.?\s*(\d+)\s+([A-Za-zÁÉÍÓÚáéíóúñ\s]{3,60})", line, re.IGNORECASE)
        if m_foot:
            c_num = int(m_foot.group(1))
            c_title = m_foot.group(2).strip()
            return f"Capítulo {c_num}: {c_title}"

    return current_chapter


def chunk_text(
    text: str,
    page_num: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> List[Dict[str, Any]]:
    """
    Splits text into sliding-window chunks with metadata tagging.
    Snaps split points to natural paragraph or sentence boundaries when available,
    while maintaining exact overlap on continuous or delimiter-free text.
    """
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    meta = metadata or {}
    book_id = meta.get("book_id", "book_default")
    book_title = meta.get("title", meta.get("book_title", "Texto Desconocido"))
    author = meta.get("author", meta.get("authors", "Autor Desconocido"))
    edition = meta.get("edition", "Edición 1")
    chapter = meta.get("chapter", "Capítulo General")
    syllabus_unit = meta.get("syllabus_unit", "U1")

    step = chunk_size - overlap
    text_len = len(text)
    chunks = []
    start = 0
    idx = 0

    while start < text_len:
        end = min(start + chunk_size, text_len)
        # Attempt natural boundary snapping only if text has whitespace/breaks
        if end < text_len:
            search_start = max(start + step, end - min(100, chunk_size // 4))
            slice_zone = text[search_start:end]
            break_pt = -1
            for delim in ["\n\n", ".\n", ". ", "; ", "\n", " "]:
                pos = slice_zone.rfind(delim)
                if pos != -1:
                    break_pt = search_start + pos + len(delim)
                    break
            if break_pt > start + step // 2:
                end = break_pt

        chunk_content = text[start:end]
        if chunk_content:
            chunks.append({
                "book_id": book_id,
                "book_title": book_title,
                "author": author,
                "edition": edition,
                "chapter": chapter,
                "page_num": page_num,
                "syllabus_unit": syllabus_unit,
                "chunk_index": idx,
                "content": chunk_content,
                "token_count": len(chunk_content.split()),
            })
            idx += 1

        if end >= text_len:
            break

        new_start = end - overlap
        if new_start <= start:
            new_start = start + step
        start = min(new_start, text_len)

    return chunks


def assign_syllabus_unit(
    chunk_text: str,
    chapter: str,
    book_meta: dict,
    syllabus_matcher=None
) -> str:
    """
    Assigns the most relevant syllabus unit ID to a chunk.
    Fuses ontology matcher, chapter mapping matrix, and default fallback.
    """
    # 1. Try dynamic ontology match if matcher is available
    if syllabus_matcher:
        try:
            matches = syllabus_matcher(chunk_text, top_k=2, threshold=4.0)
            if matches:
                # Prefer shorthand unit (e.g. U3 over THEORY_U3)
                for m in matches:
                    if m.startswith("U") and m[1:].isdigit():
                        return m
                return matches[0]
        except Exception:
            pass

    # 2. Extract chapter number from chapter string
    book_id = book_meta.get("id", "")
    m = re.search(r"Cap[ií]tulo\s+(\d+)", chapter, re.IGNORECASE)
    c_num = int(m.group(1)) if m else None

    if c_num is not None:
        if book_id == "skoog_9ed_es" and c_num in SKOOG_9ED_CHAPTER_MAP:
            return SKOOG_9ED_CHAPTER_MAP[c_num]
        elif book_id == "aguilar_2ed_es" and c_num in AGUILAR_CHAPTER_MAP:
            return AGUILAR_CHAPTER_MAP[c_num]
        elif book_id == "day_underwood_6ed_en" and c_num in DAY_UNDERWOOD_CHAPTER_MAP:
            return DAY_UNDERWOOD_CHAPTER_MAP[c_num]

    # 3. Fallback to book's default unit
    return book_meta.get("default_syllabus_unit", "U1")


def stream_book_chunks(
    pdf_path: str,
    book_meta: dict,
    target_size: int = 1000,
    overlap: int = 150,
    syllabus_matcher=None
) -> Iterator[Dict[str, Any]]:
    """
    Generator yielding structured chunk dictionaries for a textbook.
    Maintains minimal memory (< 20 MB RSS).
    """
    current_chapter = "Preliminares"

    for item in stream_pdf_text(pdf_path):
        page_num = item["page_num"]
        raw_text = item["text"]
        cleaned = clean_page_text(raw_text)
        if not cleaned:
            continue

        current_chapter = detect_chapter(cleaned, current_chapter, book_meta, page_num)
        unit = assign_syllabus_unit(
            cleaned,
            current_chapter,
            book_meta,
            syllabus_matcher=syllabus_matcher
        )

        meta = {
            "book_id": book_meta["id"],
            "title": book_meta["title"],
            "author": book_meta["authors"],
            "edition": book_meta["edition"],
            "chapter": current_chapter,
            "syllabus_unit": unit,
        }

        page_chunks = chunk_text(cleaned, page_num=page_num, metadata=meta, chunk_size=target_size, overlap=overlap)
        for chunk in page_chunks:
            yield chunk


def ingest_book(
    conn,
    pdf_path: str,
    book_meta: dict,
    batch_size: int = 100,
    syllabus_matcher=None,
    covers_dir: str = "assets/covers"
) -> Dict[str, Any]:
    """
    Ingests a single textbook into the SQLite FTS5 database.
    Batch commits chunks in micro-batches to guarantee low RAM and high throughput.
    """
    import src.db as db

    cover_file = f"{covers_dir}/{book_meta['id']}.png"

    # Register book in database
    db.insert_book(conn, {
        "id": book_meta["id"],
        "filename": book_meta["filename"],
        "title": book_meta["title"],
        "author": book_meta["authors"],
        "edition": book_meta["edition"],
        "total_pages": book_meta["total_pages"],
        "cover_path": cover_file,
        "language": book_meta.get("language", "es"),
        "is_scanned": 1 if book_meta.get("is_scanned", False) else 0,
    })

    if book_meta.get("is_scanned", False):
        logger.info(f"Book {book_meta['id']} is marked scanned; registered metadata without text chunks.")
        return {"book_id": book_meta["id"], "chunks_inserted": 0, "status": "scanned_registered"}

    chunks_batch = []
    total_chunks = 0

    for chunk in stream_book_chunks(pdf_path, book_meta, syllabus_matcher=syllabus_matcher):
        chunks_batch.append(chunk)
        if len(chunks_batch) >= batch_size:
            db.insert_chunks_batch(conn, chunks_batch)
            total_chunks += len(chunks_batch)
            chunks_batch = []

    if chunks_batch:
        db.insert_chunks_batch(conn, chunks_batch)
        total_chunks += len(chunks_batch)

    logger.info(f"Ingested {book_meta['id']}: {total_chunks} chunks inserted.")
    return {"book_id": book_meta["id"], "chunks_inserted": total_chunks, "status": "success"}


def ingest_all_books(
    books_dir: str = "books",
    db_path: str = "data/quimica_analitica.db",
    covers_dir: str = "assets/covers",
    generate_covers: bool = True,
    skip_scanned: bool = False,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Full pipeline orchestrator:
    1. Generates covers into assets/covers/ (optional).
    2. Initializes SQLite FTS5 database (src/db.py).
    3. Ingests all course textbooks in stream mode.
    """
    import src.db as db

    b_dir = Path(books_dir).resolve()
    c_dir = Path(covers_dir).resolve()

    # Step 1: Generate covers
    if generate_covers:
        try:
            from src.covers import generate_all_covers
            logger.info("Generating textbook covers...")
            generate_all_covers(books_dir=str(b_dir), covers_dir=str(c_dir))
        except Exception as e:
            logger.warning(f"Cover generation encountered a warning: {e}")

    # Step 2: Initialize database
    conn = db.init_db(db_path)

    # Step 3: Load syllabus matcher if available
    syllabus_matcher = None
    try:
        from src.syllabus import match_topics_to_curriculum
        syllabus_matcher = match_topics_to_curriculum
        logger.info("Loaded syllabus ontology matcher.")
    except Exception as e:
        logger.info(f"Syllabus matcher not loaded: {e}")

    results = {}
    total_indexed_chunks = 0

    for book_meta in BOOK_CATALOG:
        if skip_scanned and book_meta.get("is_scanned", False):
            continue

        pdf_path = b_dir / book_meta["filename"]
        if not pdf_path.exists():
            logger.warning(f"PDF missing: {pdf_path}")
            continue

        res = ingest_book(
            conn=conn,
            pdf_path=str(pdf_path),
            book_meta=book_meta,
            batch_size=batch_size,
            syllabus_matcher=syllabus_matcher,
            covers_dir=str(c_dir)
        )
        results[book_meta["id"]] = res
        total_indexed_chunks += res.get("chunks_inserted", 0)

    conn.close()
    logger.info(f"Ingestion complete: {total_indexed_chunks} total chunks indexed into {db_path}.")
    return {"total_chunks": total_indexed_chunks, "books": results}


def main():
    parser = argparse.ArgumentParser(description="Química Analítica Streaming Textbook Ingestion")
    parser.add_argument("--books-dir", default="books", help="Directory containing PDF textbooks")
    parser.add_argument("--db-path", default="data/quimica_analitica.db", help="Target SQLite database path")
    parser.add_argument("--covers-dir", default="assets/covers", help="Directory for cover PNG images")
    parser.add_argument("--no-covers", action="store_true", help="Skip cover generation")
    parser.add_argument("--skip-scanned", action="store_true", help="Skip scanned PDFs")
    parser.add_argument("--batch-size", type=int, default=100, help="Transaction batch size")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ingest_all_books(
        books_dir=args.books_dir,
        db_path=args.db_path,
        covers_dir=args.covers_dir,
        generate_covers=not args.no_covers,
        skip_scanned=args.skip_scanned,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
