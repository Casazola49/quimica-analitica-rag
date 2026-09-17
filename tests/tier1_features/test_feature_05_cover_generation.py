"""Tier 1: Feature 5 - Textbook Cover Generation Tests.

Verifies thumbnail extraction from PDF first pages using pdftoppm or fallback.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from tests.helpers import get_covers_module


class TestFeature05CoverGeneration:
    """Feature 5: Textbook Cover Generation verification."""

    def test_generate_cover_single_book(self, books_path: str) -> None:
        """Verify generating cover image for a single textbook PDF."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "aguilar_cover.png")
            result_path = covers.generate_cover(target_pdf, out_file, scale_width=300)
            assert os.path.exists(result_path), f"Cover file was not created at {result_path}"
            assert os.path.getsize(result_path) > 0, "Cover file must not be empty"

    def test_generate_cover_creates_valid_png_magic_bytes(self, books_path: str) -> None:
        """Verify generated file starts with PNG magic header bytes."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_magic.png")
            covers.generate_cover(target_pdf, out_file)
            with open(out_file, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"\x89PNG"), f"Expected PNG magic bytes, got {header}"

    def test_generate_cover_bounded_file_size(self, books_path: str) -> None:
        """Verify generated thumbnail file size is reasonable (< 2 MB)."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "test_size.png")
            covers.generate_cover(target_pdf, out_file, scale_width=300)
            size_mb = os.path.getsize(out_file) / (1024 * 1024)
            assert size_mb < 2.0, f"Cover image size is {size_mb:.2f} MB, exceeding 2.0 MB budget"

    def test_generate_all_covers_batch(self, books_path: str) -> None:
        """Verify batch generation runs across multiple books."""
        covers = get_covers_module()
        if not os.path.exists(books_path):
            pytest.skip("Books directory not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            generated = covers.generate_all_covers(books_dir=books_path, output_dir=tmpdir)
            assert len(generated) >= 1, "At least one cover should be generated from books directory"
            for p in generated:
                assert os.path.exists(p)
                assert p.endswith(".png")

    def test_generate_cover_missing_input_raises_error(self) -> None:
        """Verify attempting to generate a cover for a non-existent PDF raises FileNotFoundError."""
        covers = get_covers_module()
        with pytest.raises(FileNotFoundError):
            covers.generate_cover("/invalid/path/to/nonexistent_book.pdf", "/tmp/out.png")
