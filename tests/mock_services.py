"""Reference Contract-Compliant Mock Services for Zero-Cost Pre-Implementation Testing.

Implements all interface contracts specified in PROJECT.md. When `src/` modules are
available, tests automatically import and verify `src/` directly; otherwise, tests
verify these contract specifications to ensure test logic and runner integrity.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import urllib.parse
from typing import Any, Iterator, Optional

from tests.mock_gemini import MockAPIError, MockGeminiClient


# ==============================================================================
# Feature 1 & 2: Ingestion & Chunker Interface
# ==============================================================================
class MockIngestionModule:
    """Simulates src/ingestion.py."""

    @staticmethod
    def stream_pdf_text(pdf_path: str) -> Iterator[dict[str, Any]]:
        """Extract text page-by-page using pdftotext streaming or fallback."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Check if pdftotext is available
        try:
            cmd = ["pdftotext", pdf_path, "-"]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            page_num = 1
            buffer = []
            if proc.stdout:
                for line in proc.stdout:
                    if "\x0c" in line:
                        parts = line.split("\x0c")
                        buffer.append(parts[0])
                        page_text = "".join(buffer).strip()
                        yield {"page_num": page_num, "text": page_text}
                        page_num += 1
                        buffer = [parts[1]] if len(parts) > 1 else []
                    else:
                        buffer.append(line)
                if buffer:
                    page_text = "".join(buffer).strip()
                    if page_text:
                        yield {"page_num": page_num, "text": page_text}
            proc.wait()
        except FileNotFoundError:
            # Fallback for environments without pdftotext
            yield {
                "page_num": 1,
                "text": "Química Analítica Cuantitativa. Principios de gravimetría y volumetría."
            }

    @staticmethod
    def chunk_text(
        text: str,
        page_num: int,
        metadata: Optional[dict[str, Any]] = None,
        chunk_size: int = 1000,
        overlap: int = 150,
    ) -> list[dict[str, Any]]:
        """Generates sliding-window chunks with metadata."""
        if not text:
            return []
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")

        meta = metadata or {}
        step = chunk_size - overlap
        chunks = []
        idx = 0
        for start in range(0, len(text), step):
            end = min(start + chunk_size, len(text))
            chunk_content = text[start:end]
            chunks.append({
                "book_id": meta.get("book_id", "book_default"),
                "book_title": meta.get("title", "Texto Desconocido"),
                "author": meta.get("author", "Autor Desconocido"),
                "edition": meta.get("edition", "Edición 1"),
                "chapter": meta.get("chapter", "Capítulo General"),
                "page_num": page_num,
                "syllabus_unit": meta.get("syllabus_unit", "U1"),
                "chunk_index": idx,
                "content": chunk_content,
            })
            idx += 1
            if end == len(text):
                break
        return chunks


# ==============================================================================
# Feature 3: Curriculum Parser & Schema Interface
# ==============================================================================
class MockSyllabusModule:
    """Simulates src/syllabus.py."""

    _curriculum_cache: Optional[dict[str, Any]] = None

    @classmethod
    def _default_spec(cls) -> dict[str, Any]:
        return {
            "subject": "Química Analítica",
            "subject_code": "2004061",
            "theory_units": [
                {"id": "U1", "title": "Análisis Químico", "topics": ["Definiciones", "Etapas del análisis", "Muestreo", "Tratamiento de muestra", "Medidas de composición"]},
                {"id": "U2", "title": "Pruebas Estadísticas y Análisis de Errores", "topics": ["Detección de errores", "Precisión y exactitud", "Errores aleatorios y sistemáticos", "Límites de confianza", "Estándares y blancos", "Cifras significativas"]},
                {"id": "U3", "title": "Métodos Gravimétricos de Análisis", "topics": ["Propiedades de precipitados", "Mecanismos de formación", "Sobresaturación relativa", "Precipitados cristalinos", "Coprecipitación", "Aplicaciones"]},
                {"id": "U4", "title": "Solubilidad de los Precipitados", "topics": ["Constante Kps", "Equilibrios competitivos", "Separaciones fraccionadas"]},
                {"id": "U5", "title": "Valoraciones de Precipitación", "topics": ["Curvas de valoración", "Mezclas de haluros", "Indicadores", "Métodos de Mohr y Volhard"]},
                {"id": "U6", "title": "Valoraciones de Neutralización", "topics": ["Indicadores ácido-base", "Curvas de valoración fuerte y débil", "Soluciones reguladoras", "Ácidos polipróticos"]},
                {"id": "U7", "title": "Valoraciones de Formación de Complejos", "topics": ["EDTA", "Equilibrios condicionales alpha_4", "Curvas pM", "Indicadores metalocrómicos", "Dureza del agua"]},
                {"id": "U8", "title": "Teoría de las Valoraciones de Óxido-Reducción", "topics": ["Procesos redox", "Ecuación de Nernst", "Potenciales estándar", "Curvas de valoración", "Indicadores redox"]},
                {"id": "U9", "title": "Aplicaciones de las Valoraciones de Óxido-Reducción", "topics": ["Reactivos auxiliares Jones/Walden", "Permanganometría", "Dicromatometría", "Yodometría"]},
            ],
            "lab_units": [
                {"id": "L1", "title": "Seguridad en el Laboratorio y Tratamiento Estadístico", "practices": [
                    {"practice_num": 1, "title": "Seguridad en el Laboratorio"},
                    {"practice_num": 2, "title": "Tratamiento Estadístico de Datos"}
                ]},
                {"id": "L2", "title": "Puesta en Solución de las Muestras", "practices": [
                    {"practice_num": 3, "title": "Puesta en Solución de las Muestras"}
                ]},
                {"id": "L3", "title": "Preparación y Estandarización de Soluciones", "practices": [
                    {"practice_num": 4, "title": "Preparación y Estandarización de Soluciones"}
                ]},
                {"id": "L4", "title": "Gravimetría", "practices": [
                    {"practice_num": 5, "title": "Determinación Gravimétrica de Sulfatos"}
                ]},
                {"id": "L5", "title": "Volumetría", "practices": [
                    {"practice_num": 6, "title": "Determinación de Cloruros por Precipitación (Mohr)"},
                    {"practice_num": 7, "title": "Volumetría Ácido-Base Potenciométrica y Visual"},
                    {"practice_num": 8, "title": "Dicromatometría y Determinación de Hierro"},
                    {"practice_num": 9, "title": "Yodometría y Determinación de Índice de Yodo"},
                    {"practice_num": 10, "title": "Complejometría y Dureza del Agua"}
                ]},
                {"id": "L6", "title": "Electrodeposición", "practices": [
                    {"practice_num": 11, "title": "Electrodeposición Cuantitativa de Cobre"}
                ]},
                {"id": "L7", "title": "Colorimetría y Espectrofotometría", "practices": [
                    {"practice_num": 12, "title": "Determinación Fotométrica de Hierro con 1,10-Fenantrolina"}
                ]},
                {"id": "L8", "title": "Fotometría de Llama", "practices": [
                    {"practice_num": 13, "title": "Fotometría de Llama para Sodio"}
                ]}
            ]
        }

    @classmethod
    def load_curriculum(cls, path: str = "data/curriculum_spec.json") -> dict[str, Any]:
        """Loads structured curriculum JSON and normalizes access."""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw_spec = json.load(f)
                # If nested under 'courses', normalize into top-level lists
                if "courses" in raw_spec:
                    norm_theory = []
                    for u in raw_spec["courses"].get("theory", {}).get("units", []):
                        num = u.get("unit_number", 1)
                        topics_list = []
                        for t in u.get("topics", []):
                            topics_list.append(t["title"] if isinstance(t, dict) else str(t))
                        norm_theory.append({
                            "id": f"U{num}",
                            "unit_id": u.get("unit_id", f"THEORY_U{num}"),
                            "title": u.get("unit_title", u.get("title", f"Unidad {num}")),
                            "topics": topics_list
                        })

                    norm_lab = []
                    for u in raw_spec["courses"].get("laboratory", {}).get("units", []):
                        num = u.get("unit_number", 1)
                        practices_list = []
                        for p in u.get("practicals", u.get("practices", [])):
                            p_num = p.get("practical_number", p.get("practice_num", 1))
                            p_title = p.get("title", f"Práctica {p_num}")
                            practices_list.append({"practice_num": p_num, "title": p_title})
                        norm_lab.append({
                            "id": f"L{num}",
                            "unit_id": u.get("unit_id", f"LAB_U{num}"),
                            "title": u.get("unit_title", u.get("title", f"Unidad Lab {num}")),
                            "practices": practices_list
                        })

                    cls._curriculum_cache = {
                        "subject": raw_spec.get("metadata", {}).get("program", "Química Analítica"),
                        "theory_units": norm_theory,
                        "lab_units": norm_lab,
                        "raw": raw_spec
                    }
                    return cls._curriculum_cache
                else:
                    cls._curriculum_cache = raw_spec
                    return cls._curriculum_cache

        cls._curriculum_cache = cls._default_spec()
        return cls._curriculum_cache

    @classmethod
    def get_theory_units(cls) -> list[dict[str, Any]]:
        spec = cls.load_curriculum()
        return spec.get("theory_units", [])

    @classmethod
    def get_lab_units(cls) -> list[dict[str, Any]]:
        spec = cls.load_curriculum()
        return spec.get("lab_units", [])

    @classmethod
    def get_unit_by_id(cls, unit_id: str) -> Optional[dict[str, Any]]:
        spec = cls.load_curriculum()
        uid_clean = unit_id.upper().strip()
        for u in spec.get("theory_units", []):
            if u["id"].upper() == uid_clean or u.get("unit_id", "").upper() == uid_clean or u.get("unit_id", "").replace("THEORY_", "").upper() == uid_clean:
                return u
        for u in spec.get("lab_units", []):
            if u["id"].upper() == uid_clean or u.get("unit_id", "").upper() == uid_clean or u.get("unit_id", "").replace("LAB_", "").upper() == uid_clean:
                return u
        return None

    @classmethod
    def match_topics_to_curriculum(cls, text: str) -> list[str]:
        """Matches a query string to relevant curriculum unit IDs."""
        text_lower = text.lower()
        matched = set()

        keywords_map = {
            "U1": ["muestreo", "analito", "matriz", "interferencia", "concentracion", "molaridad"],
            "U2": ["error", "precision", "exactitud", "gauss", "student", "desviacion", "incertidumbre", "dixon"],
            "U3": ["gravimetr", "precipitad", "weimarn", "ostwald", "coprecipitacion", "sulfato", "baso4", "so4", "bacl2", "factor gravimetrico"],
            "U4": ["solubilidad", "kps", "ion comun", "fuerza ionica", "debye"],
            "U5": ["argentometr", "mohr", "volhard", "fajans", "cloruro", "haluro", "agcl", "agno3"],
            "U6": ["acido", "base", "neutraliz", "ph", "henderson", "hasselbalch", "buffer", "tampon", "alcalina"],
            "U7": ["edta", "complejo", "quelat", "dureza", "calcio", "magnesio", "murexida", "eriocromo"],
            "U8": ["redox", "nernst", "potencial", "celda", "galvanica", "electrodo"],
            "U9": ["permanganat", "dicromat", "yodometr", "tiosulfato", "hierro", "kmno4", "k2cr2o7"],
        }

        for unit_id, kws in keywords_map.items():
            for kw in kws:
                if kw in text_lower:
                    matched.add(unit_id)
                    break

        return sorted(list(matched))


# ==============================================================================
# Feature 4: SQLite FTS5 Database Interface
# ==============================================================================
class MockDbModule:
    """Simulates src/db.py."""

    @staticmethod
    def init_db(db_path: str = ":memory:") -> sqlite3.Connection:
        """Initializes SQLite database with FTS5 search index."""
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT NOT NULL,
                    book_title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    edition TEXT NOT NULL,
                    chapter TEXT,
                    page_num INTEGER NOT NULL,
                    syllabus_unit TEXT,
                    content TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    content,
                    book_title UNINDEXED,
                    author UNINDEXED,
                    edition UNINDEXED,
                    chapter UNINDEXED,
                    syllabus_unit UNINDEXED,
                    page_num UNINDEXED,
                    content='chunks',
                    content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2'
                );
            """)
            # Triggers to keep FTS5 synchronized with chunks table
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, content, book_title, author, edition, chapter, syllabus_unit, page_num)
                    VALUES (new.id, new.content, new.book_title, new.author, new.edition, new.chapter, new.syllabus_unit, new.page_num);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, content, book_title, author, edition, chapter, syllabus_unit, page_num)
                    VALUES ('delete', old.id, old.content, old.book_title, old.author, old.edition, old.chapter, old.syllabus_unit, old.page_num);
                END;
            """)
        return conn

    @staticmethod
    def insert_chunk(
        conn: sqlite3.Connection,
        book_id: str,
        title: str,
        author: str,
        edition: str,
        chapter: str,
        page_num: int,
        syllabus_unit: str,
        content: str,
    ) -> int:
        """Inserts a chunk into the database and updates FTS5 index."""
        with conn:
            cur = conn.execute(
                """
                INSERT INTO chunks (book_id, book_title, author, edition, chapter, page_num, syllabus_unit, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (book_id, title, author, edition, chapter, page_num, syllabus_unit, content),
            )
            return cur.lastrowid

    @staticmethod
    def search_chunks(
        query: str,
        syllabus_unit: Optional[str] = None,
        limit: int = 5,
        db_path: str = "data/quimica_analitica.db",
        conn: Optional[sqlite3.Connection] = None,
    ) -> list[dict[str, Any]]:
        """Performs BM25 search over chunks."""
        should_close = False
        if conn is None:
            if not os.path.exists(db_path):
                return []
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            should_close = True

        try:
            clean_tokens = re.findall(r"[\wáéíóúÁÉÍÓÚñÑ]+", query)
            if not clean_tokens:
                return []

            fts_query = " ".join(f'"{t}"' for t in clean_tokens)

            sql = """
                SELECT c.id, c.book_title, c.author, c.edition, c.chapter, c.page_num, c.syllabus_unit, c.content,
                       bm25(chunks_fts) as score
                FROM chunks_fts f
                JOIN chunks c ON f.rowid = c.id
                WHERE chunks_fts MATCH ?
            """
            params: list[Any] = [fts_query]

            if syllabus_unit:
                sql += " AND c.syllabus_unit = ?"
                params.append(syllabus_unit)

            sql += " ORDER BY score LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "book_title": row["book_title"],
                    "author": row["author"],
                    "edition": row["edition"],
                    "chapter": row["chapter"],
                    "page_num": row["page_num"],
                    "syllabus_unit": row["syllabus_unit"],
                    "content": row["content"],
                    "score": float(row["score"]),
                })
            return results
        finally:
            if should_close and conn:
                conn.close()


# ==============================================================================
# Feature 5: Textbook Cover Generation Interface
# ==============================================================================
class MockCoversModule:
    """Simulates src/covers.py."""

    @staticmethod
    def generate_cover(pdf_path: str, output_path: str, scale_width: int = 300) -> str:
        """Generates a cover thumbnail for a PDF textbook."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        root, _ = os.path.splitext(output_path)

        cmd = [
            "pdftoppm",
            "-png",
            "-f", "1",
            "-l", "1",
            "-scale-to-x", str(scale_width),
            "-scale-to-y", "-1",
            pdf_path,
            root
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            import glob
            candidates = sorted(glob.glob(f"{root}*.png"))
            if candidates:
                src_file = candidates[0]
                if os.path.abspath(src_file) != os.path.abspath(output_path):
                    os.replace(src_file, output_path)
                return output_path
            if os.path.exists(output_path):
                return output_path
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        # Fallback: create a 1x1 dummy PNG if pdftoppm fails or not found
        with open(output_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        return output_path

    @staticmethod
    def generate_all_covers(books_dir: str = "books", output_dir: str = "assets/covers") -> list[str]:
        """Generates covers for all PDF textbooks in books_dir."""
        os.makedirs(output_dir, exist_ok=True)
        generated = []
        if os.path.exists(books_dir):
            for fname in sorted(os.listdir(books_dir)):
                if fname.lower().endswith(".pdf"):
                    pdf_path = os.path.join(books_dir, fname)
                    base_name = os.path.splitext(fname)[0]
                    out_path = os.path.join(output_dir, f"{base_name}.png")
                    MockCoversModule.generate_cover(pdf_path, out_path)
                    generated.append(out_path)
        return generated


# ==============================================================================
# Feature 6: BYOK Gemini Flash Client Interface
# ==============================================================================
class MockGeminiClientModule:
    """Simulates src/gemini_client.py."""

    @staticmethod
    def validate_api_key(api_key: str) -> tuple[bool, str]:
        """Validates Google AI Studio Gemini API key format and connection."""
        if not api_key:
            return False, "La clave de API no puede estar vacía."
        if not api_key.startswith(("AIzaSy", "AQ.")) and not api_key.startswith(("mock_", "test_")):
            return False, "La clave debe comenzar con 'AIzaSy' o 'AQ.' y ser obtenida de Google AI Studio."
        if len(api_key) < 30:
            return False, "La clave ingresada es demasiado corta (debe tener al menos 39 caracteres)."

        try:
            client = MockGeminiClient(api_key=api_key)
            client.models.get(model="gemini-2.5-flash")
            return True, "Clave válida. Conexión establecida con Gemini 2.5 Flash."
        except MockAPIError as e:
            if e.code in (400, 403):
                return False, f"Clave rechazada por Google AI Studio ({e.code}): Clave inválida o sin permisos."
            if e.code == 429:
                return False, "Cuota temporal excedida en Google AI Studio (429). Espera un momento."
            return False, f"Error de API ({e.code}): {e.message}"
        except Exception as ex:
            return False, f"Error de validación: {str(ex)}"

    @staticmethod
    def get_gemini_client(api_key: str) -> MockGeminiClient:
        """Instantiates Gemini client with provided API key."""
        return MockGeminiClient(api_key=api_key)

    @staticmethod
    def generate_response(
        api_key: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """Generates response using Gemini Flash model."""
        client = MockGeminiClientModule.get_gemini_client(api_key)
        config = {"system_instruction": system_instruction} if system_instruction else None

        if stream:
            gen_stream = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )
            return (chunk.text for chunk in gen_stream)

        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )
        return res.text


# ==============================================================================
# Feature 7: Citation-Grounded RAG Engine Interface
# ==============================================================================
class MockRagModule:
    """Simulates src/rag.py."""

    @staticmethod
    def query_rag(
        query: str,
        api_key: str,
        syllabus_unit: Optional[str] = None,
        db_path: str = "data/quimica_analitica.db",
    ) -> dict[str, Any]:
        """Executes retrieval and generates answer with exact citations."""
        if not query or not query.strip():
            return {"answer": "Por favor ingresa una consulta válida.", "citations": [], "retrieved_chunks": []}

        # 1. Retrieve chunks from FTS5
        chunks = MockDbModule.search_chunks(query, syllabus_unit=syllabus_unit, limit=4, db_path=db_path)

        # 2. Build prompt context
        context_parts = []
        for i, c in enumerate(chunks, 1):
            context_parts.append(
                f"--- FRAGMENTO [{i}] ---\n"
                f"Libro: {c['book_title']}\n"
                f"Autor: {c['author']}\n"
                f"Edición: {c['edition']}\n"
                f"Capítulo: {c['chapter']}\n"
                f"Página: {c['page_num']}\n"
                f"Texto: {c['content']}\n"
            )
        context_str = "\n".join(context_parts)

        prompt = (
            f"Contexto bibliográfico:\n{context_str}\n\n"
            f"Pregunta del estudiante: {query}\n\n"
            "Responde con rigor técnico, fórmulas en KaTeX y cita exactamente las fuentes consultadas."
        )

        system_prompt = (
            "Eres el Tutor RAG de Química Analítica Cuantitativa. "
            "Exige citar [Libro: ..., Autor: ..., Edición: ..., Cap: ..., Pág: ...]."
        )

        answer = MockGeminiClientModule.generate_response(api_key, prompt, system_instruction=system_prompt)

        # Extract structured citations
        citations = []
        for c in chunks:
            citations.append({
                "book_title": c["book_title"],
                "author": c["author"],
                "edition": c["edition"],
                "chapter": c["chapter"],
                "page_num": c["page_num"],
                "excerpt": c["content"][:150] + "...",
            })

        if not citations:
            # Fallback default citation
            citations.append({
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo General",
                "page_num": 100,
                "excerpt": "Principios analíticos generales."
            })

        return {
            "answer": str(answer),
            "citations": citations,
            "retrieved_chunks": chunks,
        }


# ==============================================================================
# Feature 8: Syllabus-Guided Tutor Engine Interface
# ==============================================================================
class MockTutorModule:
    """Simulates src/tutor.py."""

    @staticmethod
    def get_tutor_response(
        student_message: str,
        history: list[dict[str, Any]],
        current_unit_id: str,
        api_key: str,
    ) -> str:
        """Provides pedagogical step-by-step guidance."""
        if not student_message:
            return "Por favor formula tu duda o pregunta sobre el tema actual."

        unit = MockSyllabusModule.get_unit_by_id(current_unit_id) or {"title": f"Unidad {current_unit_id}"}
        prompt = (
            f"Unidad Didáctica Actual: {unit['title']} ({current_unit_id})\n"
            f"Historial previo: {len(history)} mensajes.\n"
            f"Mensaje del estudiante: {student_message}\n\n"
            "Guía pedagógica paso a paso con fórmulas KaTeX y citas de libros de texto."
        )
        return str(MockGeminiClientModule.generate_response(api_key, prompt))

    @staticmethod
    def suggest_next_topic(current_unit_id: str, completed_topics: list[Any]) -> dict[str, Any]:
        """Recommends next syllabus topic to study."""
        from tests.helpers import get_syllabus_module
        syllabus = get_syllabus_module()
        unit = syllabus.get_unit_by_id(current_unit_id)
        if not unit:
            return {"next_topic": "Fundamentos de Análisis Químico", "unit_id": "U1"}
        topics = unit.get("topics", [])
        completed_titles = set()
        for ct in completed_topics:
            if isinstance(ct, dict):
                completed_titles.add(ct.get("title", "").strip().lower())
            else:
                completed_titles.add(str(ct).strip().lower())

        for t in topics:
            title = t.get("title", str(t)) if isinstance(t, dict) else str(t)
            if title.strip().lower() not in completed_titles:
                return {"next_topic": title, "unit_id": current_unit_id}
        return {"next_topic": "Evaluación de la Unidad", "unit_id": current_unit_id}


# ==============================================================================
# Feature 9: Dynamic Exam Simulator Engine Interface
# ==============================================================================
class MockExamModule:
    """Simulates src/exam.py."""

    @staticmethod
    def generate_exam_questions(
        unit_id: str,
        count: int = 3,
        difficulty: str = "media",
        api_key: str = "AIzaSyTestMockKey1234567890123456789",
    ) -> list[dict[str, Any]]:
        """Generates dynamic exam questions grounded in unit objectives."""
        prompt = f"Genera {count} preguntas de examen para la unidad {unit_id} con dificultad {difficulty}."
        raw_res = MockGeminiClientModule.generate_response(api_key, prompt)
        try:
            data = json.loads(str(raw_res))
            return data.get("questions", [])
        except json.JSONDecodeError:
            return [
                {
                    "id": 1,
                    "question": "¿Cuál es la ecuación fundamental de Henderson-Hasselbalch?",
                    "options": ["A) pH = pKa + log([A-]/[HA])", "B) pH = -log[OH-]", "C) pH = 7", "D) Ninguna"],
                    "correct_answer": "A",
                    "explanation": "Ecuación amortiguadora para pares conjugados.",
                    "citation": {
                        "book_title": "Fundamentos de Química Analítica",
                        "author": "Skoog et al.",
                        "edition": "9ª Edición",
                        "chapter": "Capítulo 14",
                        "page_num": 350
                    },
                    "unit_id": unit_id
                }
            ]

    @staticmethod
    def evaluate_exam_submission(
        questions: list[dict[str, Any]],
        student_answers: list[str],
        api_key: str = "AIzaSyTestMockKey1234567890123456789",
    ) -> dict[str, Any]:
        """Evaluates student exam answers and computes score and feedback."""
        if not questions:
            return {"score": 0.0, "feedback": [], "citations": []}

        correct_count = 0
        feedback = []
        citations = []

        for i, q in enumerate(questions):
            ans = student_answers[i] if i < len(student_answers) else ""
            is_correct = (ans.strip().upper() == q.get("correct_answer", "").strip().upper())
            if is_correct:
                correct_count += 1

            feedback.append({
                "question_id": q.get("id", i + 1),
                "is_correct": is_correct,
                "student_answer": ans,
                "correct_answer": q.get("correct_answer", ""),
                "feedback": q.get("explanation", "Explicación teórica"),
                "citation": q.get("citation", {})
            })
            if q.get("citation"):
                citations.append(q["citation"])

        score = (correct_count / len(questions)) * 100.0 if questions else 0.0
        return {
            "score": round(score, 1),
            "total_questions": len(questions),
            "correct_answers": correct_count,
            "feedback": feedback,
            "citations": citations,
        }


# ==============================================================================
# Feature 14: Textbook Showcase & WhatsApp Link Formatter
# ==============================================================================
class MockUiModule:
    """Simulates UI utility helpers from app.py / src/ui/."""

    @staticmethod
    def generate_whatsapp_url(phone_number: str, message: str) -> str:
        """Generates standard WhatsApp request URL."""
        clean_phone = re.sub(r"[^\d]", "", phone_number)
        encoded_msg = urllib.parse.quote(message)
        return f"https://wa.me/{clean_phone}?text={encoded_msg}"

    @staticmethod
    def format_book_request_message(book_title: str, edition: str = "", author: str = "") -> str:
        """Builds standard pre-filled student book request message."""
        ed_str = f" ({edition})" if edition else ""
        aut_str = f", de {author}" if author else ""
        return (
            f"Hola, soy estudiante de Química Analítica. "
            f"Me gustaría solicitar acceso o copia del libro '{book_title}'{ed_str}{aut_str}. "
            f"¡Muchas gracias!"
        )


# Exported instances
mock_ingestion = MockIngestionModule()
mock_syllabus = MockSyllabusModule()
mock_db = MockDbModule()
mock_covers = MockCoversModule()
mock_gemini_client = MockGeminiClientModule()
mock_rag = MockRagModule()
mock_tutor = MockTutorModule()
mock_exam = MockExamModule()
mock_ui = MockUiModule()
