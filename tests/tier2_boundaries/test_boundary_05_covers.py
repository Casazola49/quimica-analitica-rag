"""Tier 2: Feature 5 - Textbook Cover Generation Boundary Tests.

Verifies edge cases: missing input, zero scale width, non-existent directories, empty books dir, overwriting.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from tests.helpers import get_covers_module


class TestBoundary05Covers:
    """Boundary & Corner Case tests for Feature 5."""

    def test_cover_missing_input_raises_filenotfound(self) -> None:
        """Verify non-existent input PDF raises FileNotFoundError."""
        covers = get_covers_module()
        with pytest.raises(FileNotFoundError):
            covers.generate_cover("/path/definitely_not_found.pdf", "/tmp/out.png")

    def test_cover_creates_nested_output_directory(self, books_path: str) -> None:
        """Verify output directory is created recursively if it does not exist."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            deep_output = os.path.join(tmpdir, "deeply", "nested", "covers", "test_cover.png")
            result = covers.generate_cover(target_pdf, deep_output)
            assert os.path.exists(result)
            assert os.path.exists(os.path.dirname(deep_output))

    def test_cover_empty_books_directory_yields_empty_list(self) -> None:
        """Verify batch generation on empty folder returns [] without error."""
        covers = get_covers_module()
        with tempfile.TemporaryDirectory() as empty_dir:
            out_dir = os.path.join(empty_dir, "out")
            res = covers.generate_all_covers(books_dir=empty_dir, output_dir=out_dir)
            assert res == []

    def test_cover_overwrite_existing_file_cleanly(self, books_path: str) -> None:
        """Verify generating over an existing cover replaces it safely."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_out = os.path.join(tmpdir, "cover.png")
            # Write dummy data first
            with open(target_out, "w") as f:
                f.write("old data")
            res = covers.generate_cover(target_pdf, target_out)
            assert os.path.exists(res)
            # Must now be a real binary PNG
            with open(res, "rb") as f:
                head = f.read(8)
            assert head.startswith(b"\x89PNG")

    def test_cover_zero_scale_width_fallback(self, books_path: str) -> None:
        """Verify scale_width parameter boundary values do not crash."""
        covers = get_covers_module()
        target_pdf = os.path.join(books_path, "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf")
        if not os.path.exists(target_pdf):
            pytest.skip("Target PDF not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_out = os.path.join(tmpdir, "small_cover.png")
            # scale_width=100
            res = covers.generate_cover(target_pdf, target_out, scale_width=100)
            assert os.path.exists(res)
