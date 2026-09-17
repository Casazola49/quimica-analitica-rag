"""Helper loader functions that bridge tests to real src/ modules or contract mocks.

Enables progressive testability: tests verify real implementation modules when present,
or contract mocks during pre-implementation phases.
"""

from __future__ import annotations

import importlib
from typing import Any
from tests import mock_services


def get_db_module() -> Any:
    """Returns src.db if available, else mock_db."""
    try:
        mod = importlib.import_module("src.db")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_db


def get_syllabus_module() -> Any:
    """Returns src.syllabus if available, else mock_syllabus."""
    try:
        mod = importlib.import_module("src.syllabus")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_syllabus


def get_gemini_module() -> Any:
    """Returns src.gemini_client if available, else mock_gemini_client."""
    try:
        mod = importlib.import_module("src.gemini_client")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_gemini_client


def get_rag_module() -> Any:
    """Returns src.rag if available, else mock_rag."""
    try:
        mod = importlib.import_module("src.rag")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_rag


def get_tutor_module() -> Any:
    """Returns src.tutor if available, else mock_tutor."""
    try:
        mod = importlib.import_module("src.tutor")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_tutor


def get_exam_module() -> Any:
    """Returns src.exam if available, else mock_exam."""
    try:
        mod = importlib.import_module("src.exam")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_exam


def get_covers_module() -> Any:
    """Returns src.covers if available, else mock_covers."""
    try:
        mod = importlib.import_module("src.covers")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_covers


def get_ingestion_module() -> Any:
    """Returns src.ingestion if available, else mock_ingestion."""
    try:
        mod = importlib.import_module("src.ingestion")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_ingestion


def get_ui_module() -> Any:
    """Returns UI helpers from app / src.ui if available, else mock_ui."""
    try:
        mod = importlib.import_module("src.ui")
        return mod
    except (ImportError, ModuleNotFoundError):
        return mock_services.mock_ui
