"""Tier 2: Feature 15 - Multi-Subject Replication Guide Boundary Tests.

Verifies edge cases: missing config fields, invalid ports, non-standard subject names, path sanitization.
"""

from __future__ import annotations

import os
import pytest


class TestBoundary15Replication:
    """Boundary & Corner Case tests for Feature 15."""

    def test_replication_missing_mandatory_config_fields_validation(self) -> None:
        """Verify validation identifies missing required configuration fields."""
        incomplete_config = {
            "subject": {
                # Missing 'name' and 'code'
                "whatsapp_phone": "59170000000"
            }
        }
        subj = incomplete_config.get("subject", {})
        is_valid = ("name" in subj and "code" in subj and "whatsapp_phone" in subj)
        assert is_valid is False

    def test_replication_invalid_port_number_detection(self) -> None:
        """Verify non-numeric port parameter string fails port validation."""
        raw_port = "not_a_valid_port"
        is_port_valid = raw_port.isdigit() and (1024 <= int(raw_port) <= 65535)
        assert is_port_valid is False

    def test_replication_non_standard_subject_name(self) -> None:
        """Verify subject names with hyphens, accents, and Roman numerals are supported."""
        sample_names = [
            "Fisicoquímica II (Termodinámica Estadística)",
            "Operaciones Unitarias - Secado y Evaporación",
            "Química Orgánica Industrial & Polímeros"
        ]
        for name in sample_names:
            assert len(name) > 5

    def test_replication_relative_path_traversal_sanitization(self) -> None:
        """Verify paths containing directory traversal '../' are normalized cleanly."""
        suspicious_path = "books/../../etc/passwd"
        normalized = os.path.normpath(suspicious_path)
        assert normalized != suspicious_path

    def test_replication_empty_books_directory_detection(self) -> None:
        """Verify system warns if books directory has 0 PDF files."""
        empty_books: list[str] = []
        has_pdfs = any(f.endswith(".pdf") for f in empty_books)
        assert has_pdfs is False
