"""
Química Analítica Educational Portal & RAG Chatbot.

Package initialization for core backend modules:
- db: SQLite FTS5 database and BM25 search
- syllabus: Curriculum specification parser and topic matcher
- covers: Textbook cover extraction via pdftoppm
- ingestion: Bounded-memory streaming PDF ingestion and chunking
"""

__version__ = "1.0.0"

from . import ui
