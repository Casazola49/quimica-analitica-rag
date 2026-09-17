# Original User Request

## 2026-09-12T16:43:32Z

A zero-cost, open-source web educational portal and RAG chatbot for Chemical Engineering students (piloted on "Química Analítica" theory and lab), enabling students to use their own free Google AI Studio Gemini API key to query course books with exact citations, receive syllabus-guided tutoring, take dynamic practice exams, and request textbooks via WhatsApp.

Working directory: /home/raymond/Work/agy_work/quimica_analitica_02
Integrity mode: development

## Requirements

### R1. Low-Resource Textbook Ingestion & Syllabus Mapping
Implement an efficient, memory-safe ingestion pipeline that extracts and structures content from the course textbooks (`books/` directory) and maps them directly to the units of both the theory and laboratory syllabi (`plan_global/` directory). The pipeline must operate in bounded memory (suitable for low-spec machines) without loading multi-hundred-megabyte files into memory all at once.

### R2. Bring-Your-Own-Key (BYOK) Web Portal & Chatbot
Create a lightweight, responsive web application (Python backend e.g. FastAPI/Streamlit with modern UI) that requires zero server-side LLM operating budget by allowing students to input their own free Google AI Studio (Gemini Flash) API key stored securely in client session. The UI must include a syllabus topic navigator, interactive chat interface, dynamic exam simulator mode, and a textbook library view.

### R3. Citation-Grounded RAG & Syllabus-Guided Tutor
Develop the retrieval and prompt-orchestration engine that combines course syllabus context with relevant book chunks. Responses must cite exact source references (book title, author, edition, chapter, and page/section). In tutoring mode, the assistant guides the student through syllabus topics step-by-step; in exam simulator mode, it generates dynamic, personalized evaluation questions with feedback based on the student's answers and syllabus objectives.

### R4. Textbook Showcase & WhatsApp Request Integration
Provide a dedicated textbook catalog displaying book titles, editions, authors, cover previews, and direct access buttons: either cloud/direct links or a one-click WhatsApp redirection link with a pre-configured, URL-encoded message (e.g., "Hola, me gustaría solicitar el libro [Título del Libro] para la materia de Química Analítica").

### R5. Replicable Multi-Subject Standardization Guide
Create comprehensive, step-by-step documentation (`REPLICATION_GUIDE.md`) explaining the exact workflow to duplicate this portal for any other subject in the Chemical Engineering curriculum (e.g., Fisicoquímica, Termodinámica, Operaciones Unitarias) using their respective study plans and bibliographies.

## Acceptance Criteria

### Ingestion & Resource Efficiency
- [ ] Ingestion script processes all course textbooks into indexed chunks with metadata (source book, author, edition, syllabus unit, page number) without exceeding 2 GB RAM usage.
- [ ] Syllabi for both theory (9 units) and lab (8 units / 13 practices) are parsed and accessible as structured curriculum guides.

### BYOK & Zero-Cost Architecture
- [ ] Web application runs locally or deploys to free tiers (e.g., Render/HuggingFace/Streamlit Cloud) without requiring any paid backend API key from the host.
- [ ] Students can enter and validate their free Google AI Studio API key in the UI; invalid keys display clear, friendly guidance on how to get a free key.

### RAG Retrieval & Exact Citations
- [ ] Chatbot answers curriculum-specific questions (covering both theory such as error analysis, gravimetry, acid-base, redox, complexometry, and lab such as standardizations, sulfate gravimetry, permanganometry, water hardness) and includes verifiable book name, chapter, and page number citations in its answers.
- [ ] Prompts and retrieval gracefully handle queries outside the syllabus by grounding answers in the verified course material.

### Exam Simulator & Tutoring Modes
- [ ] Exam simulator mode generates interactive questions based on selected syllabus units and evaluates student answers with detailed explanations and textbook citations.
- [ ] Guided study mode suggests syllabus-ordered topics and concepts for students to review progressively.

### Books Portal & WhatsApp Action
- [ ] Book section displays cards for each organized textbook with title, edition, authors, and cover image.
- [ ] Each book card includes a working WhatsApp button formatted as `https://wa.me/<PHONE>?text=<MESSAGE>` with customizable phone number and pre-filled message requesting that specific book.

### Subject Replication Documentation
- [ ] `REPLICATION_GUIDE.md` exists with clear instructions, folder conventions, script commands, and configuration steps to add a new subject in under 30 minutes.

## 2026-09-16T13:44:47Z

User quota has reset. Please resume monitoring and orchestration. Inspect the current workspace state (Milestone 1 and Milestone 2 passed and documented in .agents/teamwork_preview_orchestrator_1/GATE_STATUS.md; Milestone 3 Web UI & WhatsApp is next, followed by Milestone 4 Replication Guide and Milestone 5 final victory audit). Revive or re-spawn the Project Orchestrator to continue execution and drive the project to completion.

## 2026-09-16T17:16:58Z

User quota is reset and active. Please resume execution to finalize Milestone 4 verification and Milestone 5 (Final E2E 100% Pass, Hardening, and Victory Claim).

## 2026-09-16T22:18:26Z

User quota is now active and reset. Please resume the independent victory audit (Phase A, B, and C) to finalize and declare project completion.


