"""Shared Pytest Fixtures and Global Test Configuration.

Ensures deterministic, zero-cost test execution using mock Gemini clients,
in-memory/temporary SQLite FTS5 databases, and standard chemical engineering test data.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from typing import Generator

import pytest

# Add project root to sys.path so tests can import src and tests modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.mock_gemini import MockGeminiClient
from tests.mock_services import MockDbModule, MockSyllabusModule


@pytest.fixture(scope="session")
def valid_api_key() -> str:
    """Returns a valid Google AI Studio mock API key."""
    return "AIzaSyTestMockDeterministicKey1234567890"


@pytest.fixture(scope="session")
def invalid_api_key() -> str:
    """Returns an invalid API key lacking proper prefix."""
    return "invalid_key_without_aizasy_prefix"


@pytest.fixture(scope="session")
def quota_exceeded_key() -> str:
    """Returns an API key simulating HTTP 429 quota exhaustion."""
    return "AIzaSy_QUOTA_429_EXCEEDED_MOCK_KEY"


@pytest.fixture(scope="session")
def forbidden_api_key() -> str:
    """Returns an API key simulating HTTP 403 forbidden permissions."""
    return "AIzaSy_FORBIDDEN_403_MOCK_KEY_123456789012"


@pytest.fixture
def mock_gemini(valid_api_key: str) -> MockGeminiClient:
    """Returns a fresh MockGeminiClient instance."""
    return MockGeminiClient(api_key=valid_api_key)


@pytest.fixture(autouse=True)
def patch_google_genai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Safeguard: Monkeypatches google.genai.Client to prevent accidental real API calls."""
    try:
        import google.genai as genai
        monkeypatch.setattr(genai, "Client", MockGeminiClient)
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def sample_curriculum() -> dict:
    """Provides complete 9 Theory units and 8 Lab units specification."""
    return MockSyllabusModule._default_spec()


@pytest.fixture
def seeded_db() -> Generator[tuple[sqlite3.Connection, str], None, None]:
    """Provides an isolated SQLite FTS5 database pre-seeded with textbook chunks."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_quimica.db")
    conn = MockDbModule.init_db(db_path)

    # Seed with representative textbook chunks
    chunks_to_seed = [
        (
            "skoog_9ed_es",
            "Fundamentos de Química Analítica",
            "Douglas A. Skoog et al.",
            "9ª Edición",
            "Capítulo 12: Métodos Gravimétricos de Análisis",
            315,
            "U3",
            "La formación de precipitados depende de la sobresaturación relativa RSS = (Q - S) / S de Von Weimarn. La digestión en caliente favorece la maduración de Ostwald, obteniendo partículas cristalinas de BaSO4 fácilmente filtrables."
        ),
        (
            "skoog_9ed_es",
            "Fundamentos de Química Analítica",
            "Douglas A. Skoog et al.",
            "9ª Edición",
            "Capítulo 17: Valoraciones de Precipitación",
            412,
            "U5",
            "El método de Mohr utiliza cromato de potasio K2CrO4 como indicador en la titulación de cloruros con nitrato de plata AgNO3 a pH neutro (6.5 a 10.0), formando un precipitado rojo de Ag2CrO4 en el punto final."
        ),
        (
            "aguilar_2ed_es",
            "Introducción a los Equilibrios Iónicos",
            "Manuel Aguilar San Juan",
            "2ª Edición",
            "Capítulo 3: Disoluciones tampón y valoraciones ácido-base",
            115,
            "U6",
            "La ecuación de Henderson-Hasselbalch pH = pKa + log([A-]/[HA]) describe el comportamiento de una solución amortiguadora. La capacidad reguladora beta es máxima cuando el pH es exactamente igual al pKa."
        ),
        (
            "aguilar_2ed_es",
            "Introducción a los Equilibrios Iónicos",
            "Manuel Aguilar San Juan",
            "2ª Edición",
            "Capítulo 8: Volumetrías de formación de complejos",
            418,
            "U7",
            "El EDTA forma complejos quelato estables 1:1 con iones calcio y magnesio. La constante condicional K'f se calcula multiplicando Kf por la fracción molar alpha4. La dureza total del agua se titula a pH 10 con Negro de Eriocromo T."
        ),
        (
            "day_underwood_6ed_en",
            "Quantitative Analysis",
            "R. A. Day, Jr., A. L. Underwood",
            "6th Edition",
            "Chapter 11: Oxidation-Reduction Titrations",
            345,
            "U9",
            "La permanganometría utiliza KMnO4 como autoindicador en medio ácido sulfúrico. El reactivo se estandariza con oxalato de sodio a 70-80 grados Celsius para acelerar la cinética de reacción antes de que el ion Mn2+ actúe como autocatalizador."
        ),
    ]

    for item in chunks_to_seed:
        MockDbModule.insert_chunk(
            conn=conn,
            book_id=item[0],
            title=item[1],
            author=item[2],
            edition=item[3],
            chapter=item[4],
            page_num=item[5],
            syllabus_unit=item[6],
            content=item[7],
        )

    yield conn, db_path

    conn.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def books_path() -> str:
    """Returns absolute path to books directory."""
    return os.path.join(PROJECT_ROOT, "books")


@pytest.fixture
def plan_global_path() -> str:
    """Returns absolute path to plan_global directory."""
    return os.path.join(PROJECT_ROOT, "plan_global")
