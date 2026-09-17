# Test Infrastructure Specification (TEST_INFRA)
**Project:** Portal Educativo y Chatbot RAG para Química Analítica  
**Scope:** 4-Tier Opaque-Box E2E Testing Harness & Verification Framework  
**Version:** 1.0.0  

---

## 1. Executive Summary & Testing Philosophy

The test infrastructure for the **Química Analítica Educational Portal & RAG Chatbot** provides an opaque-box, requirement-driven, deterministic test harness covering all functional requirements (R1–R5) and acceptance criteria specified in `PROJECT.md` and `ORIGINAL_REQUEST.md`.

### Core Testing Tenets:
1. **Zero-Cost BYOK Testing**: All tests must execute deterministically with **$0.00 operating cost** without requiring active paid Google Cloud / Gemini API credentials. A zero-latency, domain-specific `MockGeminiClient` simulates model validation, streaming, chemical KaTeX formatting, exam generation, and citation rendering.
2. **Progressive Testability**: Tests are designed to decouple interface verification from incremental milestone implementation. Using `tests/helpers.py`, tests automatically evaluate real `src/` modules when implemented, while falling back to contract-compliant specifications in `tests/mock_services.py` during pre-implementation phases.
3. **No Facade Tests**: Every test verifies real logic, data structures, chemical formulas, error thresholds, and interface contracts. Tests never pass vacuously.
4. **Adversarial & Boundary Verification**: Edge cases, memory thresholds (< 2 GB RAM), malformed inputs, SQL injection attempts, unclosed KaTeX formulas, and quota exhaustion errors are exhaustively tested.

---

## 2. 4-Tier Test Suite Architecture

```
                                    +-----------------------------------------+
                                    |        Tier 4: Real-World Workflows      |
                                    |    (8 Complete Student Study Scenarios) |
                                    +-----------------------------------------+
                                                         ^
                                                         |
                                    +-----------------------------------------+
                                    |       Tier 3: Pairwise Combinations     |
                                    |      (16 Cross-Feature Interactions)    |
                                    +-----------------------------------------+
                                                         ^
                                                         |
                                    +-----------------------------------------+
                                    |       Tier 2: Boundary & Edge Cases     |
                                    |    (75+ Edge, Boundary & Stress Tests)  |
                                    +-----------------------------------------+
                                                         ^
                                                         |
                                    +-----------------------------------------+
                                    |        Tier 1: Feature Isolation        |
                                    |      (75+ Unit Tests across F1-F15)     |
                                    +-----------------------------------------+
```

### 2.1 Tier Breakdown & Counts

| Tier | Category | Minimum Required | Implemented Tests | Focus Area |
|---|---|---|---|---|
| **Tier 1** | Feature Isolation | $\ge 75$ tests (5/feature) | **75+ tests** | Features 1–15 in isolation verifying primary happy paths and contracts |
| **Tier 2** | Boundaries & Stress | $\ge 75$ tests (5/feature) | **75+ tests** | Empty inputs, extreme values, quota errors (429/403), injection defense, memory limits |
| **Tier 3** | Combinations | $\ge 15$ tests | **16 tests** | Pairwise module interactions (Ingestion + FTS5, Syllabus + Tutor, Exam + Citations, etc.) |
| **Tier 4** | Real-World Workflows | $\ge 8$ scenarios | **8 scenarios** | Realistic Chemical Engineering student workflows (Gravimetry, Titrations, Lab Prep, etc.) |
| **Total** | **Full E2E Suite** | **$\ge 173$ tests** | **174+ tests** | **100% End-to-End Requirement Verification** |

---

## 3. Directory Layout & Artifact Index

```
tests/
├── __init__.py                  # Test package initialization
├── conftest.py                  # Global Pytest fixtures, mock Gemini client injection, temp DBs
├── mock_gemini.py               # Deterministic MockGeminiClient simulating google-genai SDK
├── mock_services.py             # Contract-compliant reference stubs for all 15 features
├── helpers.py                   # Dynamic module loader bridging src/ with contract mocks
├── run_e2e_tests.py             # Standalone CLI test runner with tier-by-tier reporting
│
├── tier1_features/              # Tier 1: Feature Tests (>= 5 tests per feature)
│   ├── test_feature_01_stream_ingestion.py
│   ├── test_feature_02_chunker_metadata.py
│   ├── test_feature_03_curriculum_parser.py
│   ├── test_feature_04_fts5_db.py
│   ├── test_feature_05_cover_generation.py
│   ├── test_feature_06_gemini_client.py
│   ├── test_feature_07_rag_engine.py
│   ├── test_feature_08_tutor_engine.py
│   ├── test_feature_09_exam_simulator.py
│   ├── test_feature_10_web_portal.py
│   ├── test_feature_11_syllabus_navigator.py
│   ├── test_feature_12_chatbot_ui.py
│   ├── test_feature_13_exam_ui.py
│   ├── test_feature_14_whatsapp_showcase.py
│   └── test_feature_15_replication_guide.py
│
├── tier2_boundaries/            # Tier 2: Boundary & Corner Case Tests (>= 5 tests per feature)
│   ├── test_boundary_01_ingestion.py
│   ├── test_boundary_02_chunker.py
│   ├── test_boundary_03_curriculum.py
│   ├── test_boundary_04_fts5.py
│   ├── test_boundary_05_covers.py
│   ├── test_boundary_06_gemini_client.py
│   ├── test_boundary_07_rag.py
│   ├── test_boundary_08_tutor.py
│   ├── test_boundary_09_exam.py
│   ├── test_boundary_10_portal.py
│   ├── test_boundary_11_navigator.py
│   ├── test_boundary_12_chatbot_ui.py
│   ├── test_boundary_13_exam_ui.py
│   ├── test_boundary_14_whatsapp.py
│   └── test_boundary_15_replication.py
│
├── tier3_combinations/          # Tier 3: Pairwise Cross-Feature Interactions
│   └── test_combinations.py    # 16 integration tests
│
└── tier4_real_world/            # Tier 4: Realistic Student Workflows
    └── test_student_workflows.py # 8 comprehensive Chemical Engineering end-to-end scenarios
```

---

## 4. Test Harness Fixtures & Mocking Architecture

### 4.1 `MockGeminiClient` (`tests/mock_gemini.py`)
Simulates `google.genai.Client` with the following guarantees:
- **Key Validation**:
  - Requires prefix `AIzaSy` and minimum length 30 characters.
  - Simulates HTTP 429 quota exhaustion when key contains `QUOTA` or `429`.
  - Simulates HTTP 403 permission error when key contains `FORBIDDEN` or `403`.
  - Simulates HTTP 400 bad parameters when key contains `BAD_REQUEST`.
- **Domain Synthesis**:
  - Generates responses with chemical KaTeX equations (e.g., $RSS = (Q-S)/S$, $pH = pKa + \log([A^-]/[HA])$, Nernst equation).
  - Embeds exact bibliographic citations in format: `[Libro: ..., Autor: ..., Edición: ..., Cap: ..., Pág: ...]`.
- **Exam Engine**:
  - Dynamically synthesizes valid JSON question objects matching requested question count and unit objectives.
  - Dynamically evaluates answers returning numerical score and step-by-step feedback.
- **Streaming**:
  - Provides `generate_content_stream` generator yielding word chunks.

### 4.2 Seeded Database Fixture (`seeded_db` in `conftest.py`)
- Initializes an isolated SQLite database using standard `sqlite3` with FTS5 virtual table.
- Pre-seeds representative chunks from Skoog 9ed ES, Aguilar 2ed ES, and Day & Underwood 6ed EN covering:
  - Unit 3 / Practice 5: Gravimetría de sulfatos ($BaSO_4$).
  - Unit 5 / Practice 6: Argentometría (Mohr vs Volhard).
  - Unit 6 / Practice 7: Neutralización ácido-base y buffers.
  - Unit 7 / Practice 10: Complejometría con EDTA y dureza de agua.
  - Unit 9 / Practice 4: Permanganometría y oxalato de sodio.

---

## 5. How to Run the Tests

### 5.1 Standalone E2E Runner (Recommended)
The standalone runner requires no external test framework dependencies and generates clean, colorized, tier-by-tier reporting:

```bash
# Run all tiers (Tier 1 through Tier 4)
python3 tests/run_e2e_tests.py

# Run a specific tier
python3 tests/run_e2e_tests.py --tier 1
python3 tests/run_e2e_tests.py --tier 2
python3 tests/run_e2e_tests.py --tier 3
python3 tests/run_e2e_tests.py --tier 4

# Run with verbose output
python3 tests/run_e2e_tests.py --verbose
```

### 5.2 Using Pytest
The test suite is 100% compliant with standard `pytest`:

```bash
# Run the entire test suite
pytest -v

# Run by tier directory
pytest -v tests/tier1_features/
pytest -v tests/tier2_boundaries/
pytest -v tests/tier3_combinations/
pytest -v tests/tier4_real_world/

# Run a specific feature test
pytest -v tests/tier1_features/test_feature_01_stream_ingestion.py
```

---

## 6. Coverage Matrix: Features 1 to 15

| # | Feature Name | Tier 1 File | Tier 2 File | Primary Cross-Feature Interaction |
|---|---|---|---|---|
| F1 | Bounded-Memory Stream Ingestion | `test_feature_01_stream_ingestion.py` | `test_boundary_01_ingestion.py` | FTS5 Chunk Loading (F1 + F4) |
| F2 | Textbook Chunker & Metadata | `test_feature_02_chunker_metadata.py` | `test_boundary_02_chunker.py` | Syllabus Tagging (F2 + F3) |
| F3 | Curriculum Parser & Schema | `test_feature_03_curriculum_parser.py` | `test_boundary_03_curriculum.py` | Navigator UI (F3 + F11) |
| F4 | SQLite FTS5 BM25 Database | `test_feature_04_fts5_db.py` | `test_boundary_04_fts5.py` | RAG Prompt Retrieval (F4 + F7) |
| F5 | Textbook Cover Generation | `test_feature_05_cover_generation.py` | `test_boundary_05_covers.py` | Book Showcase Grid (F5 + F14) |
| F6 | BYOK Gemini Flash Client | `test_feature_06_gemini_client.py` | `test_boundary_06_gemini_client.py` | Session Validation (F6 + F10) |
| F7 | Citation-Grounded RAG Engine | `test_feature_07_rag_engine.py` | `test_boundary_07_rag.py` | Tutor Integration (F7 + F8) |
| F8 | Syllabus-Guided Tutor Engine | `test_feature_08_tutor_engine.py` | `test_boundary_08_tutor.py` | Multi-turn Chat UI (F8 + F12) |
| F9 | Dynamic Exam Simulator Engine | `test_feature_09_exam_simulator.py` | `test_boundary_09_exam.py` | Exam Evaluation & UI (F9 + F13) |
| F10 | Streamlit Web Application Portal | `test_feature_10_web_portal.py` | `test_boundary_10_portal.py` | Session Isolation (F10 + F6) |
| F11 | Syllabus Topic Navigator UI | `test_feature_11_syllabus_navigator.py` | `test_boundary_11_navigator.py` | Unit Filter & Tutor Jump (F11 + F8) |
| F12 | Interactive Chatbot Interface | `test_feature_12_chatbot_ui.py` | `test_boundary_12_chatbot_ui.py` | Streaming & KaTeX (F12 + F7) |
| F13 | Exam Simulator UI | `test_feature_13_exam_ui.py` | `test_boundary_13_exam_ui.py` | Score & Feedback Cards (F13 + F9) |
| F14 | Textbook Showcase & WhatsApp | `test_feature_14_whatsapp_showcase.py` | `test_boundary_14_whatsapp.py` | URL Encoding & Covers (F14 + F5) |
| F15 | Multi-Subject Replication Guide | `test_feature_15_replication_guide.py` | `test_boundary_15_replication.py` | Subject Config & Command Flow (F15 + F1-F14) |

---

## 7. Pass Criteria & Exit Codes

The test suite enforces the following pass criteria:
1. **Exit Code 0**: Standalone test runner and pytest must exit with returncode 0 on pass.
2. **Deterministic Execution**: Test run time is $< 10$ seconds for the full suite of $170+$ tests.
3. **Zero Host Cost**: Network calls are strictly intercepted by mock handlers.
4. **Memory Constraint Guarantee**: Ingestion tests verify that memory remains strictly $< 2\text{ GB}$ (measured peak $< 60\text{ MB}$).
