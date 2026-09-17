# Project: Portal Educativo y Chatbot RAG para Química Analítica

## Architecture
- **Language & Runtime**: Python 3.12+
- **Data Ingestion & Indexing**: Bounded-memory streaming (`pdftotext` stdout streaming), sliding-window chunker with metadata tagging (book, author, edition, chapter, page, syllabus unit), SQLite FTS5 disk-backed BM25 search database (`data/quimica_analitica.db`). Peak memory < 60 MB RSS.
- **Syllabus Hierarchy**: JSON curriculum guide (`data/curriculum_spec.json`) parsed from `plan_global/` covering 9 Theory Units (37 subtopics) and 8 Lab Units (13 practical experiments).
- **Core LLM & BYOK**: `google-genai` client using Gemini Flash (e.g., `gemini-2.5-flash` or `gemini-1.5-flash`), with client-side API key management via session state (`st.session_state`). Zero host API key or server costs.
- **RAG & Tutor Engine**: Hybrid retrieval (FTS5 BM25 search scored by relevance), strict citation prompt orchestration requiring verifiable citations (Book, Author, Edition, Chapter, Page), syllabus-guided progressive tutoring, and dynamic exam question generation + grading.
- **Web Application**: Streamlit portal (`app.py`) featuring:
  - API Key setup & validation with direct link to Google AI Studio.
  - Syllabus Navigator & Topic Explorer.
  - Interactive Tutor Chatbot with streaming and KaTeX chemical formula rendering.
  - Dynamic Exam Simulator (unit selection, question generation, automated grading with feedback and citations).
  - Textbook Showcase with cover previews (`assets/covers/`) and one-click WhatsApp request links (`https://wa.me/<PHONE>?text=<MESSAGE>`).
- **Standardization & Portability**: `REPLICATION_GUIDE.md` for replicating the portal to any Chemical Engineering subject in < 30 minutes.

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Bounded-Memory Stream Ingestion | Streaming text extraction via `pdftotext` (<2 GB RAM peak; benchmarked ~14.2 MB) | M1 | R1 |
| 2 | Textbook Chunker & Metadata Tagging | Chunks text with book title, author, edition, chapter, page, and syllabus unit tags | M1 | R1 |
| 3 | Curriculum Parser & Schema | Structured parser and JSON data schema for Theory (9 units) and Lab (8 units / 13 practices) | M1 | R1 |
| 4 | SQLite FTS5 BM25 Search Database | Disk-backed search index for sub-5ms exact keyword, chemical formula, and phrase retrieval | M1 | R1 |
| 5 | Textbook Cover Generation | Generates lightweight PNG covers from first page of PDFs via `pdftoppm` | M1 | R4 |
| 6 | BYOK Gemini Flash Client | Client session API key management, key validation, and friendly setup instructions | M2 | R2 |
| 7 | Citation-Grounded RAG Engine | Retrieves chunks and formats prompt forcing exact citations (Book, Author, Edition, Chapter, Page) | M2 | R3 |
| 8 | Syllabus-Guided Tutor Engine | Interactive tutor mode progressive walkthrough of theory units and lab practices | M2 | R3 |
| 9 | Dynamic Exam Simulator Engine | Unit-based question generator and automated evaluation with detailed feedback and citations | M2 | R3 |
| 10 | Streamlit Web Application Portal | Responsive UI with tab/sidebar navigation for tutor, exam, syllabus, and library | M3 | R2 |
| 11 | Syllabus Topic Navigator UI | Interactive curriculum browser displaying units, objectives, topics, and mapped textbooks | M3 | R2 |
| 12 | Interactive Chatbot Interface | Chat UI with streaming responses, conversation history, and KaTeX chemical formulas | M3 | R2 |
| 13 | Exam Simulator UI | Interactive practice exam interface with question display, answer input, and grading cards | M3 | R2 |
| 14 | Textbook Showcase & WhatsApp Links | Book cards with covers, authors, editions, direct links, and WhatsApp request button (`https://wa.me/...`) | M3 | R4 |
| 15 | Multi-Subject Replication Guide | Comprehensive `REPLICATION_GUIDE.md` for duplicating portal for any course in <30 min | M4 | R5 |
| 16 | E2E Testing Suite (Tiers 1-4) | Comprehensive test suite covering features, boundaries, pairwise combinations, and real-world scenarios | E2E-Track | Criteria |
| 17 | Final E2E Pass & Hardening | 100% pass on all E2E tests + Tier 5 adversarial stress testing | M5 | Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Test harness, test runners, Tier 1-4 test suites, TEST_INFRA.md, TEST_READY.md | Architecture Specs | DONE |
| M1 | Ingestion Pipeline & Syllabus Mapping | `src/ingestion.py`, `src/syllabus.py`, `src/db.py`, `src/covers.py`, `data/quimica_analitica.db`, `data/curriculum_spec.json`, covers in `assets/covers/` | none | DONE |
| M2 | BYOK Gemini Client & RAG/Tutor/Exam Engines | `src/gemini_client.py`, `src/rag.py`, `src/tutor.py`, `src/exam.py` | M1 | DONE |
| M3 | Educational Web Portal & WhatsApp Integration | `app.py`, `src/ui.py`, session state management, WhatsApp links, syllabus explorer | M1, M2 | DONE |
| M4 | Multi-Subject Replication Guide | `REPLICATION_GUIDE.md`, `requirements.txt`, `packages.txt`, `src/covers.py` CLI | M1, M2, M3 | DONE |
| M5 | Final Milestone: 100% E2E Pass & Hardening | Full suite verification, regression check, Tier 5 adversarial testing | M1-M4, E2E-Track | DONE |

## Code Layout
```
/home/raymond/Work/agy_work/quimica_analitica_02/
├── ORIGINAL_REQUEST.md
├── PROJECT.md
├── TEST_INFRA.md
├── TEST_READY.md
├── REPLICATION_GUIDE.md
├── requirements.txt
├── run_app.sh
├── app.py                     # Streamlit web application entry point
├── src/
│   ├── __init__.py
│   ├── db.py                  # SQLite FTS5 database interface
│   ├── syllabus.py            # Syllabus parser and topic matching
│   ├── ingestion.py           # Streaming bounded-memory PDF ingestion
│   ├── covers.py              # Cover image generator (pdftoppm)
│   ├── gemini_client.py       # BYOK Gemini Flash client and validation
│   ├── rag.py                 # Retrieval and citation-grounded prompt formatting
│   ├── tutor.py               # Syllabus-guided tutoring logic
│   └── exam.py                # Dynamic exam question generation & grading
├── data/
│   ├── curriculum_spec.json   # Parsed curriculum JSON specification
│   └── quimica_analitica.db   # SQLite FTS5 search index (generated)
├── assets/
│   └── covers/                # Book cover preview PNG images
└── tests/
    ├── conftest.py
    ├── run_e2e_tests.py       # Standalone E2E test runner
    ├── tier1_features/        # >= 5 tests per feature (>= 80 tests)
    ├── tier2_boundaries/      # Boundary, corner, and error handling tests
    ├── tier3_combinations/    # Pairwise cross-feature interaction tests
    └── tier4_real_world/      # Real-world chemistry student scenarios
```

## Interface Contracts
### `src/db.py` ↔ `src/rag.py` & `src/ingestion.py`
- `init_db(db_path: str = "data/quimica_analitica.db") -> sqlite3.Connection`
- `insert_chunk(conn, book_id, title, author, edition, chapter, page_num, syllabus_unit, content) -> int`
- `search_chunks(query: str, syllabus_unit: str = None, limit: int = 5, db_path: str = "data/quimica_analitica.db") -> list[dict]`
  - Each returned dict: `{"id": int, "book_title": str, "author": str, "edition": str, "chapter": str, "page_num": int, "syllabus_unit": str, "content": str, "score": float}`

### `src/syllabus.py` ↔ `src/tutor.py` & `app.py`
- `load_curriculum(path: str = "data/curriculum_spec.json") -> dict`
- `get_theory_units() -> list[dict]`
- `get_lab_units() -> list[dict]`
- `get_unit_by_id(unit_id: str) -> dict`
- `match_topics_to_curriculum(text: str) -> list[str]`

### `src/gemini_client.py` ↔ `src/rag.py`, `src/tutor.py`, `src/exam.py`, `app.py`
- `validate_api_key(api_key: str) -> tuple[bool, str]`
- `get_gemini_client(api_key: str)`
- `generate_response(api_key: str, prompt: str, system_instruction: str = None, stream: bool = False) -> str | Iterator[str]`

### `src/rag.py` ↔ `app.py`
- `query_rag(query: str, api_key: str, syllabus_unit: str = None, db_path: str = "data/quimica_analitica.db") -> dict`
  - Returned dict: `{"answer": str, "citations": list[dict], "retrieved_chunks": list[dict]}`

### `src/tutor.py` ↔ `app.py`
- `get_tutor_response(student_message: str, history: list[dict], current_unit_id: str, api_key: str) -> str | Iterator[str]`

### `src/exam.py` ↔ `app.py`
- `generate_exam_questions(unit_id: str, count: int, difficulty: str, api_key: str) -> list[dict]`
- `evaluate_exam_submission(questions: list[dict], student_answers: list[str], api_key: str) -> dict`
  - Returned dict: `{"score": float, "feedback": list[dict], "citations": list[dict]}`
