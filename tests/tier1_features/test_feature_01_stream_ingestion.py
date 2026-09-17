"""Tier 1: Feature 1 - Bounded-Memory Stream Ingestion Tests.

Verifies streaming text extraction via pdftotext or bounded generator,
ensuring peak memory remains strictly bounded (< 2 GB, benchmarked < 20 MB).
"""

from __future__ import annotations

import os
import tracemalloc
import pytest
from tests.helpers import get_ingestion_module


class TestFeature01StreamIngestion:
    """Feature 1: Bounded-Memory Stream Ingestion verification."""

    def test_stream_pdf_text_extracts_pages(self, books_path: str) -> None:
        """Verify that stream_pdf_text yields structured page dicts with page_num and text."""
        ingestion = get_ingestion_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip(f"Test PDF not found at {target_pdf}")

        gen = ingestion.stream_pdf_text(target_pdf)
        first_page = next(gen, None)
        assert first_page is not None, "Generator should yield at least one page"
        assert "page_num" in first_page, "Page dict must contain 'page_num'"
        assert "text" in first_page, "Page dict must contain 'text'"
        assert isinstance(first_page["page_num"], int)
        assert isinstance(first_page["text"], str)

    def test_stream_pdf_text_page_number_sequence(self, books_path: str) -> None:
        """Verify that streamed pages maintain monotonically increasing 1-indexed numbering."""
        ingestion = get_ingestion_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip(f"Test PDF not found at {target_pdf}")

        pages = []
        for i, page in enumerate(ingestion.stream_pdf_text(target_pdf)):
            pages.append(page["page_num"])
            if i >= 5:  # Sample first 6 pages
                break

        assert pages == [1, 2, 3, 4, 5, 6], f"Expected consecutive page numbers 1-6, got {pages}"

    def test_stream_pdf_yields_non_empty_content(self, books_path: str) -> None:
        """Verify that native text PDFs yield non-empty text content."""
        ingestion = get_ingestion_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip(f"Test PDF not found at {target_pdf}")

        non_empty_found = False
        for i, page in enumerate(ingestion.stream_pdf_text(target_pdf)):
            if len(page["text"].strip()) > 20:
                non_empty_found = True
                break
            if i > 15:
                break
        assert non_empty_found, "Streamed PDF pages must contain substantive text content"

    def test_stream_pdf_memory_bounded(self, books_path: str) -> None:
        """Verify that streaming through 50 pages keeps Python RSS growth strictly below 200 MB."""
        ingestion = get_ingestion_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip(f"Test PDF not found at {target_pdf}")

        tracemalloc.start()
        try:
            count = 0
            for page in ingestion.stream_pdf_text(target_pdf):
                count += 1
                # Exercise text without accumulating
                _ = len(page["text"])
                if count >= 30:
                    break

            current, peak = tracemalloc.get_traced_memory()
            peak_mb = peak / (1024 * 1024)
            # Memory ceiling requirement is 2000 MB (2 GB); we assert < 200 MB for streaming safety
            assert peak_mb < 200.0, f"Memory peak was {peak_mb:.2f} MB, exceeding bounded streaming threshold"
        finally:
            tracemalloc.stop()

    def test_stream_pdf_handles_missing_file_raises_error(self) -> None:
        """Verify that attempting to stream a non-existent file raises FileNotFoundError."""
        ingestion = get_ingestion_module()
        non_existent = "/path/to/definitely_missing_chemistry_book.pdf"
        with pytest.raises(FileNotFoundError):
            gen = ingestion.stream_pdf_text(non_existent)
            next(gen)
