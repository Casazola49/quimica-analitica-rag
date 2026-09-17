"""
src/rag.py - Citation-Grounded RAG Engine for Química Analítica.

Orchestrates retrieval from SQLite FTS5 BM25 search index, prompt construction
with syllabus grounding, KaTeX mathematical/chemical formatting, exact bibliographic
citations, prompt delimiter sanitization, and robust zero-cost offline extractive fallback.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/quimica_analitica.db"
DEFAULT_TOP_K = 5
MAX_QUERY_LENGTH = 10000

# Canonical default citation used as fallback for boundary / zero-chunk scenarios
DEFAULT_FALLBACK_CITATION: Dict[str, Any] = {
    "book_title": "Fundamentos de Química Analítica",
    "author": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
    "edition": "9ª Edición (2015)",
    "chapter": "Capítulo 1: La Naturaleza de la Química Analítica",
    "page_num": 1,
    "excerpt": "Principios fundamentales del análisis químico cuantitativo y metrología química."
}

# Canonical course textbook registry for citation validation and metadata normalization
CANONICAL_BOOKS: List[Dict[str, Any]] = [
    {
        "id": "skoog_9ed_es",
        "title": "Fundamentos de Química Analítica",
        "aliases": ["fundamentos de quimica analitica", "skoog analitica", "skoog 9", "skoog"],
        "author": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "edition": "9ª Edición (2015)",
        "max_page": 1075,
    },
    {
        "id": "skoog_10ed_en",
        "title": "Fundamentals of Analytical Chemistry",
        "aliases": ["fundamentals of analytical chemistry", "skoog 10"],
        "author": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "edition": "10th Edition (2022)",
        "max_page": 1100,
    },
    {
        "id": "aguilar_2ed_es",
        "title": "Introducción a los Equilibrios Iónicos",
        "aliases": ["introduccion a los equilibrios ionicos", "equilibrios ionicos", "aguilar san juan", "aguilar"],
        "author": "Manuel Aguilar San Juan",
        "edition": "2ª Edición (2000)",
        "max_page": 500,
    },
    {
        "id": "day_underwood_6ed_en",
        "title": "Quantitative Analysis",
        "aliases": ["quantitative analysis", "day underwood", "day & underwood", "day"],
        "author": "R. A. Day, Jr., A. L. Underwood",
        "edition": "6th Edition (1991)",
        "max_page": 800,
    },
    {
        "id": "skoog_instrumental_7ed_es",
        "title": "Principios de Análisis Instrumental",
        "aliases": ["principios de analisis instrumental", "analisis instrumental", "skoog instrumental"],
        "author": "Douglas A. Skoog, F. James Holler, Stanley R. Crouch",
        "edition": "7ª Edición (2019)",
        "max_page": 1165,
    },
    {
        "id": "kolthoff_vol1_2ed_en",
        "title": "Treatise on Analytical Chemistry: Theory and Practice (Vol. 1)",
        "aliases": ["treatise on analytical chemistry", "kolthoff vol 1", "kolthoff"],
        "author": "I. M. Kolthoff, Philip J. Elving, Edward J. Meehan",
        "edition": "2nd Edition (1978)",
        "max_page": 900,
    },
    {
        "id": "kolthoff_vol5_en",
        "title": "Treatise on Analytical Chemistry: Optical Methods (Vol. 5)",
        "aliases": ["treatise on analytical chemistry vol 5", "kolthoff vol 5"],
        "author": "I. M. Kolthoff, Philip J. Elving, Ernest B. Sandell",
        "edition": "1st Edition",
        "max_page": 800,
    },
    {
        "id": "skoog_solutions_10ed_en",
        "title": "Student Solutions Manual: Fundamentals of Analytical Chemistry",
        "aliases": ["student solutions manual", "solutions manual skoog"],
        "author": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "edition": "10th Edition (2022)",
        "max_page": 400,
    },
]

# Stopwords for query relevance checking
EXTRA_QUERY_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a",
    "en", "para", "por", "con", "son", "es", "se", "que", "cual", "cuales", "como",
    "y", "o", "su", "sus", "the", "of", "in", "and", "or", "to", "for", "is", "are",
    "what", "how", "quien", "quién", "quienes", "quiénes", "como", "cómo", "donde",
    "dónde", "cuando", "cuándo", "por qué", "porque", "fue", "fueron", "era", "eran",
    "ha", "han", "hay", "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "aquel", "aquella", "sobre", "entre", "sin", "tras", "durante", "hasta", "desde",
    "explica", "explicar", "funciona", "definir", "cuál", "cuáles", "dime", "cuenta",
    "acerca", "favor", "hola", "buenos", "días", "tardes", "noches"
}

RAG_SYSTEM_INSTRUCTION = """\
Eres el Tutor Experto de RAG para la asignatura de Química Analítica Cuantitativa y Laboratorio (Licenciatura en Ingeniería Química).
Tu misión es resolver las dudas analíticas y conceptuales del estudiante con máximo rigor científico, explicaciones didácticas paso a paso y estricta fundamentación bibliográfica.

REGLAS OBLIGATORIAS:
1. RIGOR BIBLIOGRÁFICO Y CITACIÓN EXACTA:
   - Basa tus respuestas en los fragmentos bibliográficos proporcionados en el contexto.
   - Cada afirmación relevante, principio, ecuación o procedimiento DEBE incluir al final su cita bibliográfica exacta entre corchetes con el formato:
     [Libro: <Título>, Autor: <Autor>, Edición: <Edición>, Capítulo: <Capítulo>, Página: <Página>]
   - Si se usan referencias de Skoog, Aguilar San Juan o Day & Underwood provistas en el contexto, copia los datos bibliográficos con exactitud.

2. FÓRMULAS Y ECUACIONES EN KaTeX:
   - Escribe especies químicas, variables, concentraciones y pH usando KaTeX en línea ($...$):
     Ejemplos: $BaSO_4$, $Fe^{2+}$, $[H_3O^+]$, $K_{ps}$, $pH$, $\\alpha_4$, $\\beta$, $RSS = \\frac{Q - S}{S}$.
   - Escribe reacciones químicas y ecuaciones matemáticas en bloques KaTeX independientes ($$...$$):
     $$SO_4^{2-} + Ba^{2+} \\rightarrow BaSO_4(s)$$
     $$pH = pKa + \\log\\left(\\frac{[A^-]}{[HA]}\\right)$$

3. ALCANCE Y DELIMITACIÓN TEMÁTICA:
   - El temario oficial comprende: Análisis Químico y Muestreo, Errores y Estadística, Gravimetría de Precipitados (BaSO4, Ostwald), Solubilidad (Kps), Argentometría (Mohr, Volhard), Neutralización Ácido-Base (Buffers, titulación potenciométrica), Complejometría con EDTA (Dureza de Agua), Volumetrías Redox (Nernst, Permanganometría, Dicromatometría, Yodometría) y Métodos Instrumentales (Electrodeposición, Espectrofotometría con 1,10-Fenantrolina, Fotometría de Llama).
   - Si la consulta del estudiante es ajena al temario oficial (por ejemplo, física cuántica pura, historia, literatura o programación), aclara amablemente los límites del curso y orienta al estudiante hacia los temas pertinentes de Química Analítica, citando los libros oficiales recomendados.
"""


def _get_generate_response_fn():
    """Dynamically resolves generate_response function from src.gemini_client."""
    try:
        from src.gemini_client import generate_response
        return generate_response
    except (ImportError, ModuleNotFoundError):
        try:
            from tests.helpers import get_gemini_module
            return get_gemini_module().generate_response
        except Exception:
            return None


def sanitize_prompt_delimiters(text: str) -> str:
    """Sanitizes internal prompt delimiter tags to prevent delimiter injection attacks."""
    if not text or not isinstance(text, str):
        return ""
    pattern = re.compile(r"-{2,}\s*FRAGMENTO\b(?:.*?)-{2,}", re.IGNORECASE)
    return pattern.sub("[DELIMITADOR_SANITIZADO]", text)


def format_citation_tag(
    book_title: str,
    author: str,
    edition: str,
    chapter: str,
    page_num: Union[int, str]
) -> str:
    """Formats a standardized citation bracket tag."""
    return f"[Libro: {book_title}, Autor: {author}, Edición: {edition}, Capítulo: {chapter}, Página: {page_num}]"


def _find_canonical_book(title_str: str, author_str: str = "") -> Optional[Dict[str, Any]]:
    """Matches candidate title against canonical course textbook definitions."""
    clean_t = str(title_str).lower().strip()
    clean_a = str(author_str).lower().strip()
    for b in CANONICAL_BOOKS:
        b_title_lower = b["title"].lower()
        if clean_t == b_title_lower:
            return b
        if clean_t in b_title_lower or b_title_lower in clean_t:
            return b
        for alias in b.get("aliases", []):
            if alias in clean_t or alias in clean_a:
                return b
    return None


def build_rag_prompt(
    query: str,
    chunks: List[Dict[str, Any]],
    syllabus_unit: Optional[str] = None
) -> Tuple[str, str]:
    """Constructs user prompt and system instruction for LLM grounding."""
    clean_query = sanitize_prompt_delimiters(query)
    if chunks:
        context_blocks = []
        for i, c in enumerate(chunks, 1):
            title = c.get("book_title", "Texto")
            author = c.get("author", "Autor")
            edition = c.get("edition", "Edición")
            chapter = c.get("chapter", "Capítulo")
            page = c.get("page_num", 1)
            content = c.get("content", "").strip()
            s_unit = c.get("syllabus_unit", "")

            block = (
                f"--- FRAGMENTO [{i}] ---\n"
                f"Libro: {title}\n"
                f"Autor: {author}\n"
                f"Edición: {edition}\n"
                f"Capítulo: {chapter}\n"
                f"Página: {page}\n"
                f"Unidad: {s_unit}\n"
                f"Cita sugerida: [Libro: {title}, Autor: {author}, Edición: {edition}, Capítulo: {chapter}, Página: {page}]\n"
                f"Texto:\n{content}"
            )
            context_blocks.append(block)
        context_str = "\n\n".join(context_blocks)
    else:
        context_str = "(No se encontraron fragmentos de texto específicos en la base de datos de libros de texto)."

    unit_note = f"\nUnidad del programa: {syllabus_unit}" if syllabus_unit else ""
    prompt = (
        f"Contexto bibliográfico disponible:{unit_note}\n\n"
        f"{context_str}\n\n"
        f"Pregunta del estudiante: {clean_query}\n\n"
        "Responde con rigor técnico universitario, ecuaciones KaTeX claras y cita exactamente "
        "las fuentes consultadas en formato [Libro: <Título>, Autor: <Autor>, Edición: <Edición>, Capítulo: <Capítulo>, Página: <Página>]."
    )
    return prompt, RAG_SYSTEM_INSTRUCTION


def extract_citations(
    model_response: str,
    retrieved_chunks: List[Dict[str, Any]],
    db_path: str = DEFAULT_DB_PATH
) -> List[Dict[str, Any]]:
    """
    Extracts, normalizes, validates and deduplicates structured citations from retrieved chunks
    and model response text. Filters out hallucinated book titles and out-of-bounds page numbers.
    Normalizes abbreviated metadata to canonical database titles and authors.
    """
    citations: List[Dict[str, Any]] = []
    seen_keys = set()

    # Map books present in retrieved chunks to prioritize their canonical metadata
    chunk_books: Dict[str, Dict[str, Any]] = {}
    for c in retrieved_chunks:
        b_t = str(c.get("book_title", "")).strip()
        if b_t:
            chunk_books[b_t.lower()] = {
                "title": b_t,
                "author": str(c.get("author", "")).strip(),
                "edition": str(c.get("edition", "")).strip(),
            }

    def add_citation(b_title: str, auth: str, ed: str, chap: str, p_num: Any, excerpt: str = "", from_chunk: bool = False):
        try:
            page_int = int(p_num)
        except (ValueError, TypeError):
            match = re.search(r"\d+", str(p_num))
            page_int = int(match.group(0)) if match else 1

        b_clean = str(b_title).strip()
        if not b_clean:
            return

        # 1. Bounds check: Maximum page across all course textbooks is 1200
        if page_int <= 0 or page_int > 1200:
            return

        # 2. Match against canonical books, chunk books, or database
        canon_title = b_clean
        canon_author = str(auth).strip()
        canon_edition = str(ed).strip()

        canon = _find_canonical_book(b_clean, auth)
        if canon:
            canon_title = canon["title"]
            canon_author = canon["author"]
            canon_edition = canon["edition"]
            if page_int > canon.get("max_page", 1200):
                return
        elif b_clean.lower() in chunk_books:
            cb = chunk_books[b_clean.lower()]
            canon_title = cb["title"]
            canon_author = cb["author"]
            canon_edition = cb["edition"]
        else:
            if not from_chunk:
                # Hallucinated or fabricated book title not in syllabus textbooks or chunks
                return
            if not canon_author:
                canon_author = "Douglas A. Skoog et al."
            if not canon_edition:
                canon_edition = "9ª Edición (2015)"

        key = (canon_title.lower(), page_int)
        if key not in seen_keys:
            seen_keys.add(key)
            exc = str(excerpt).strip()
            if len(exc) > 180:
                exc = exc[:180] + "..."
            citations.append({
                "book_title": canon_title,
                "author": canon_author,
                "edition": canon_edition,
                "chapter": str(chap).strip() if chap else "Capítulo General",
                "page_num": page_int,
                "excerpt": exc
            })

    # 1. Populate from retrieved chunks
    for c in retrieved_chunks:
        add_citation(
            b_title=c.get("book_title", ""),
            auth=c.get("author", ""),
            ed=c.get("edition", ""),
            chap=c.get("chapter", ""),
            p_num=c.get("page_num", 1),
            excerpt=c.get("content", ""),
            from_chunk=True
        )

    # 2. Parse inline bracket citations in model response if present
    tag_matches = re.finditer(r"\[Libro:\s*([^\]]+)\]", model_response, re.IGNORECASE)
    for m in tag_matches:
        raw_inside = m.group(1).strip()
        parts = [p.strip() for p in raw_inside.split(",")]
        meta: Dict[str, str] = {}
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                meta[k.strip().lower()] = v.strip()

        title_val = meta.get("libro", parts[0] if parts else "")
        author_val = meta.get("autor", parts[1] if len(parts) > 1 and ":" not in parts[1] else "")
        edition_val = meta.get("edición", meta.get("edicion", parts[2] if len(parts) > 2 and ":" not in parts[2] else ""))
        chapter_val = meta.get("capítulo", meta.get("capitulo", meta.get("cap", parts[3] if len(parts) > 3 and ":" not in parts[3] else "")))
        page_val = meta.get("página", meta.get("pagina", meta.get("pág", meta.get("pag", parts[4] if len(parts) > 4 and ":" not in parts[4] else "1"))))

        if title_val:
            add_citation(title_val, author_val, edition_val, chapter_val, page_val, from_chunk=False)

    # 3. Fallback if still empty
    if not citations:
        citations.append(dict(DEFAULT_FALLBACK_CITATION))

    return citations


def filter_relevant_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    syllabus_unit: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filters retrieved chunks for topical relevance against student query.
    Eliminates spurious matches (e.g. dedication pages matching common names)
    and enforces syllabus topic alignment.
    """
    if not chunks:
        return []

    # If explicitly filtered by syllabus unit, chunks are already grounded
    if syllabus_unit:
        return chunks

    clean_q = str(query).lower().strip()
    tokens = re.findall(r"[\wáéíóúÁÉÍÓÚñÑüÜ]+", clean_q)
    content_words = [t for t in tokens if (len(t) >= 2 or t == "q") and t not in EXTRA_QUERY_STOPWORDS]

    if not content_words:
        return []

    # Check curriculum matcher
    matched_units: List[str] = []
    try:
        from src.syllabus import match_topics_to_curriculum
        matched_units = match_topics_to_curriculum(query)
    except Exception:
        pass

    relevant: List[Dict[str, Any]] = []
    for c in chunks:
        c_content = str(c.get("content", "")).lower()
        c_title = str(c.get("book_title", "")).lower()
        c_chap = str(c.get("chapter", "")).lower()
        full_chunk_text = f"{c_title} {c_chap} {c_content}"

        # Reject book dedications / copyright frontmatter when query is not about authors/dedications
        if c_content.strip().startswith("dedicamos este libro") or "fallecida el 11 de julio" in c_content:
            continue

        matched_count = sum(1 for w in content_words if w in full_chunk_text)
        ratio = matched_count / len(content_words)

        if len(content_words) == 1:
            if matched_count >= 1:
                relevant.append(c)
        elif len(content_words) in (2, 3):
            if matched_count >= min(2, len(content_words)) or (matched_units and matched_count >= 1):
                relevant.append(c)
        else:  # >= 4 words
            if (matched_count >= 2 and ratio >= 0.30) or (matched_units and matched_count >= 2):
                relevant.append(c)

    return relevant


def build_extractive_summary(
    query: str,
    chunks: List[Dict[str, Any]],
    syllabus_unit: Optional[str] = None
) -> str:
    """Builds a rich markdown summary directly from chunks for offline or no-key execution."""
    relevant_chunks = filter_relevant_chunks(query, chunks, syllabus_unit)

    if not relevant_chunks:
        unit_str = f" en la unidad {syllabus_unit}" if syllabus_unit else ""
        return (
            f"No se encontraron fragmentos relevantes en los libros de texto indexados para la consulta "
            f"'{query}'{unit_str}. "
            "Por favor formula una pregunta relacionada con los temas del programa oficial "
            "(Gravimetría, Volumetría Ácido-Base, Argentometría, Complejometría con EDTA, Redox o Métodos Instrumentales)."
        )

    lines = [
        "### Resumen Extractivo de Textos Oficiales (Modo Local / Sin Conexión)",
        f"**Consulta:** *{query}*\n",
        "A continuación se detallan los fragmentos más relevantes recuperados directamente de la base de datos de libros de texto:\n"
    ]

    for i, c in enumerate(relevant_chunks, 1):
        book = c.get("book_title", "Texto")
        author = c.get("author", "")
        ed = c.get("edition", "")
        cap = c.get("chapter", "")
        page = c.get("page_num", 1)
        unit = c.get("syllabus_unit", "")
        content = c.get("content", "").strip()

        unit_str = f" | **Unidad:** {unit}" if unit else ""
        citation_tag = format_citation_tag(book, author, ed, cap, page)

        lines.append(f"#### {i}. {book} — {cap} (Pág. {page}){unit_str}")
        lines.append(f"> {content}\n")
        lines.append(f"**Cita:** `{citation_tag}`\n")

    lines.append(
        "---\n*Nota: Esta respuesta fue recuperada directamente del índice BM25 de SQLite FTS5. "
        "Para explicaciones sintéticas interactivas y fórmulas KaTeX generadas por IA, "
        "ingresa tu clave gratuita de Google AI Studio en el panel lateral.*"
    )
    return "\n".join(lines)


def _wrap_stream_with_fallback(
    gen: Iterator[str],
    query: str,
    chunks: List[Dict[str, Any]],
    syllabus_unit: Optional[str]
) -> Iterator[str]:
    """Wraps streaming response generator to handle error yields or stream disconnects."""
    stream_started = False
    try:
        for chunk in gen:
            chunk_str = str(chunk)
            if not stream_started and chunk_str.startswith("⚠️"):
                # LLM returned warning string on first chunk (e.g. 429 quota exhaustion)
                yield chunk_str
                yield "\n\n"
                yield build_extractive_summary(query, chunks, syllabus_unit)
                return
            stream_started = True
            yield chunk_str
    except Exception as err:
        logger.warning("Streaming generation exception (%s), yielding extractive fallback", err)
        err_str = str(err).lower()
        code = getattr(err, "code", None)
        if code == 429 or "429" in err_str or "quota" in err_str:
            yield "⚠️ Cuota temporal de Google AI Studio excedida (HTTP 429). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"
        elif code == 403 or "403" in err_str:
            yield "⚠️ Error de permisos de Google AI Studio (HTTP 403). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"
        elif "timeout" in err_str or "timed out" in err_str:
            yield "⚠️ Error: Tiempo de espera agotado al conectar con Google AI Studio (Timeout). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"
        else:
            yield f"⚠️ Error al generar streaming con Gemini: {str(err)}\n\n"
        yield build_extractive_summary(query, chunks, syllabus_unit)


def query_rag(
    query: str,
    api_key: Optional[str] = None,
    syllabus_unit: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
    top_k: int = DEFAULT_TOP_K,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Retrieves relevant textbook chunks and generates citation-grounded chemical responses.

    Parameters:
        query: Student message or inquiry.
        api_key: BYOK Gemini Flash API key (Google AI Studio). If None/mock/offline, extractive mode runs.
        syllabus_unit: Optional curriculum filter (e.g. 'U3', 'U7', 'LAB_P5').
        db_path: Path to SQLite FTS5 database (default: 'data/quimica_analitica.db').
        top_k: Number of chunks to retrieve (default: 5).
        stream: Whether to stream generation chunks (default: False).

    Returns:
        Dict with 'answer' (str or Iterator[str]), 'citations' (list[dict]), 'retrieved_chunks' (list[dict]).
    """
    # 1. Validate empty or whitespace-only query
    if query is None or not str(query).strip():
        return {
            "answer": "Por favor ingresa una consulta o pregunta válida sobre el temario de Química Analítica.",
            "citations": [],
            "retrieved_chunks": []
        }

    clean_query = str(query).strip()[:MAX_QUERY_LENGTH]

    # Validate top_k
    try:
        limit_val = max(1, min(int(top_k), 20))
    except (ValueError, TypeError):
        limit_val = DEFAULT_TOP_K

    # 2. Retrieve chunks from SQLite FTS5 BM25 index
    chunks: List[Dict[str, Any]] = []
    try:
        from src.db import search_chunks
        chunks = search_chunks(
            query=clean_query,
            syllabus_unit=syllabus_unit,
            limit=limit_val,
            db_path=db_path
        )
    except Exception as e:
        logger.warning("Error querying SQLite FTS5 chunks: %s", e)
        chunks = []

    # 3. Handle offline / extractive mode when API key is not provided or is offline
    is_offline = (
        not api_key
        or not str(api_key).strip()
        or str(api_key).strip().lower() in ("offline", "none")
    )

    generate_fn = _get_generate_response_fn() if not is_offline else None

    # If generation function is unavailable or offline mode requested
    if generate_fn is None or is_offline:
        answer_text = build_extractive_summary(clean_query, chunks, syllabus_unit)
        citations_list = extract_citations(answer_text, chunks)
        return {
            "answer": iter([answer_text]) if stream else answer_text,
            "citations": citations_list,
            "retrieved_chunks": chunks
        }

    # 4. LLM Generation via BYOK Gemini Client
    prompt, system_inst = build_rag_prompt(clean_query, chunks, syllabus_unit)

    try:
        try:
            response = generate_fn(
                api_key=str(api_key).strip(),
                prompt=prompt,
                system_instruction=system_inst,
                stream=stream,
                raise_on_error=True
            )
        except TypeError:
            response = generate_fn(
                api_key=str(api_key).strip(),
                prompt=prompt,
                system_instruction=system_inst,
                stream=stream
            )

        if stream:
            wrapped_stream = _wrap_stream_with_fallback(response, clean_query, chunks, syllabus_unit)
            citations_list = extract_citations("", chunks)
            return {
                "answer": wrapped_stream,
                "citations": citations_list,
                "retrieved_chunks": chunks
            }
        else:
            answer_text = str(response)
            if answer_text.startswith("⚠️"):
                logger.warning("Gemini generation returned warning notice, falling back to extractive summary")
                extractive_fallback = build_extractive_summary(clean_query, chunks, syllabus_unit)
                combined_answer = f"{answer_text}\n\n{extractive_fallback}"
                citations_list = extract_citations(combined_answer, chunks)
                return {
                    "answer": combined_answer,
                    "citations": citations_list,
                    "retrieved_chunks": chunks
                }
            citations_list = extract_citations(answer_text, chunks)
            return {
                "answer": answer_text,
                "citations": citations_list,
                "retrieved_chunks": chunks
            }
    except Exception as err:
        logger.warning("Gemini generation failed (%s), falling back to extractive summary", err)
        err_str = str(err).lower()
        code = getattr(err, "code", None)
        if code == 429 or "429" in err_str or "quota" in err_str:
            warning_prefix = "⚠️ Cuota temporal de Google AI Studio excedida (HTTP 429). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"
        elif code == 403 or "403" in err_str:
            warning_prefix = "⚠️ Error de permisos de Google AI Studio (HTTP 403). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"
        elif "timeout" in err_str or "timed out" in err_str:
            warning_prefix = "⚠️ Error: Tiempo de espera agotado al conectar con Google AI Studio (Timeout). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"
        else:
            warning_prefix = f"⚠️ Error al conectar con Google AI Studio ({err}). A continuación se presenta el resumen extractivo directo de los libros oficiales:\n\n"

        extractive_text = build_extractive_summary(clean_query, chunks, syllabus_unit)
        combined_answer = f"{warning_prefix}{extractive_text}"
        citations_list = extract_citations(combined_answer, chunks)
        return {
            "answer": iter([combined_answer]) if stream else combined_answer,
            "citations": citations_list,
            "retrieved_chunks": chunks
        }
