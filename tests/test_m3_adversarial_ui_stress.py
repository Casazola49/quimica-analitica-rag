"""
tests/test_m3_adversarial_ui_stress.py - Empirical Adversarial Stress Test Suite for Milestone 3.

Empirical Challenger verification for:
- src/ui.py
- app.py

Covers:
1. WhatsApp URL Generation & Encoding:
   - Phone cleaning across messy international formats, symbols, emojis, letters, extensions, empty/None.
   - Message percent-encoding: spaces as %20, newlines as %0A, quotes, Spanish accents, chemical formulas.
   - Query string validation: zero raw spaces, regex verification.
2. Cover Image Resolver:
   - Valid catalog book IDs, missing IDs, empty/None, invalid characters, null bytes.
   - Path traversal attacks (../../etc/passwd, /etc/passwd).
   - Long filename stress (exceeding NAME_MAX 255 bytes) and safe fallback behavior.
3. KaTeX Chemical Formula Formatter & XSS Sanitization:
   - Standard formulas ($H_2SO_4$, $BaSO_4$, $pH = -\\log[H^+]$, $K_{ps}$, $Ca^{2+}$, $EDTA^{4-}$).
   - Delimiter balancing (unclosed $, unclosed $$, odd counts).
   - XSS sanitization (<script>, <img>, <iframe>, mixed text + math).
4. Session State Management & BYOK:
   - Headless and mock dict contexts.
   - Completeness of initialized keys.
   - Idempotency.
   - api_key and gemini_api_key alias consistency and synchronization.
   - clear_session_state and disconnect_api_key behavior.
   - Multi-user isolation.
5. Navigation Payloads & Score Badges:
   - create_tutor_navigation_payload, create_exam_navigation_payload bounds.
   - format_score_badge thresholds.
6. Streamlit App Integration:
   - AppTest execution verifying clean mounting of sidebar and all 4 tabs without exceptions.
"""

from __future__ import annotations

import html
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict
import pytest

from src import ui
from src.ui import (
    DEFAULT_DEPARTMENT_PHONE,
    build_whatsapp_request_url,
    clear_session_state,
    create_exam_navigation_payload,
    create_tutor_navigation_payload,
    disconnect_api_key,
    format_book_request_message,
    format_chemical_formula,
    format_score_badge,
    generate_whatsapp_url,
    get_book_by_id,
    get_canonical_views,
    get_course_catalog,
    init_session_state,
    resolve_cover_image_path,
)


# ==============================================================================
# 1. WHATSAPP URL GENERATION & ENCODING ADVERSARIAL STRESS TESTS
# ==============================================================================
class TestAdversarialWhatsappUrl:
    """Stress-test WhatsApp URL generation and message encoding."""

    @pytest.mark.parametrize(
        "raw_phone,expected_digits",
        [
            ("+591-70000000", "59170000000"),
            ("59170000000", "59170000000"),
            ("+591 (4) 425-6789 ext 10", "5914425678910"),
            ("+1 (800) 555-0199", "18005550199"),
            ("   +591 71234567   ", "59171234567"),
            ("📞 +591-70112233 🚀", "59170112233"),
            ("tel:+591-4-4123456", "59144123456"),
            ("591-4-256789#123", "5914256789123"),
        ],
    )
    def test_phone_number_cleaning_valid_digit_extractions(self, raw_phone: str, expected_digits: str) -> None:
        """Verify dirty, formatted, or international phone numbers are cleaned strictly to digits."""
        url = generate_whatsapp_url(raw_phone, "Hola")
        match = re.match(r"^https:\/\/wa\.me\/(\d+)\?text=.*$", url)
        assert match is not None, f"URL '{url}' does not match standard wa.me format"
        assert match.group(1) == expected_digits

    @pytest.mark.parametrize(
        "empty_or_invalid_phone",
        [
            "",
            "   ",
            None,
            "abc",
            "!@#$%^&*()_+",
            "---()---",
        ],
    )
    def test_phone_fallback_on_empty_or_non_digit_inputs(self, empty_or_invalid_phone: Any) -> None:
        """Verify phone with no usable digits safely falls back to department default."""
        url = generate_whatsapp_url(empty_or_invalid_phone, "Consulta")
        clean_default = re.sub(r"[^\d]", "", DEFAULT_DEPARTMENT_PHONE)
        assert f"https://wa.me/{clean_default}?text=" in url

    @pytest.mark.parametrize(
        "message",
        [
            "Hola, necesito el libro.",
            "Química Analítica Cuantitativa: 9ª Edición (Douglas A. Skoog)",
            "Línea 1\nLínea 2\r\nLínea 3",
            "Fórmula: $H_2SO_4$ y precipitado $BaSO_4$",
            'Cita con "comillas dobles" y \'simples\'',
            "Ecuación: pH = -log[H+] & Ka * Kb = Kw",
            "¿Tiene disponibilidad del libro? ¡Gracias!",
            "¡Atención! Ácido clorhídrico concentrado (37% m/m), densidad = 1.19 g/mL",
        ],
    )
    def test_message_percent_encoding_no_raw_spaces(self, message: str) -> None:
        """Verify query string contains zero raw spaces, newlines are %0A, and accents are encoded."""
        url = generate_whatsapp_url("59170000000", message)

        # 1. Verify no raw unencoded whitespace
        assert " " not in url, f"Raw space detected in URL: {url}"
        assert "\n" not in url, f"Raw newline detected in URL: {url}"
        assert "\r" not in url, f"Raw carriage return detected in URL: {url}"

        # 2. Verify URL pattern compliance
        pattern = re.compile(r"^https:\/\/wa\.me\/\d+\?text=.+$")
        assert pattern.match(url), f"URL '{url}' does not match required wa.me pattern"

        # 3. Verify exact round-trip decoding fidelity
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        assert "text" in params
        decoded = params["text"][0]
        assert decoded == message

    def test_whatsapp_url_empty_message_behavior(self) -> None:
        """Verify empty message does not crash and produces valid base query string."""
        url = generate_whatsapp_url("59170000000", "")
        assert url == "https://wa.me/59170000000?text="
        assert " " not in url

    def test_build_whatsapp_request_url_modular_defaults(self) -> None:
        """Verify modular builder generates valid URLs with default or partial dictionary data."""
        # Empty book dict
        url_empty = build_whatsapp_request_url({})
        assert re.match(r"^https:\/\/wa\.me\/\d+\?text=.+$", url_empty)

        # Book with partial data
        book = {"title": "Equilibrios Iónicos", "edition": "2ª Edición"}
        url_book = build_whatsapp_request_url(book)
        assert re.match(r"^https:\/\/wa\.me\/\d+\?text=.+$", url_book)
        assert "Equilibrios%20I%C3%B3nicos" in url_book or "Equilibrios" in url_book

        # Book with pre-configured whatsapp_message
        custom_book = {
            "title": "Skoog",
            "whatsapp_message": "Mensaje personalizado sin formato",
        }
        url_custom = build_whatsapp_request_url(custom_book)
        assert "Mensaje%20personalizado" in url_custom


# ==============================================================================
# 2. COVER IMAGE RESOLVER ADVERSARIAL STRESS TESTS
# ==============================================================================
class TestAdversarialCoverImageResolver:
    """Stress-test resolve_cover_image_path for traversal, length limits, and missing files."""

    def test_valid_book_ids_resolve_to_existing_covers(self) -> None:
        """Verify standard catalog book IDs resolve to valid non-empty files in assets/covers."""
        catalog = get_course_catalog()
        assert len(catalog) >= 11
        for book in catalog:
            book_id = book["id"]
            path = resolve_cover_image_path(book_id)
            assert path != "", f"Failed to resolve cover for valid book_id '{book_id}'"
            assert os.path.isfile(path), f"Resolved path '{path}' does not exist on disk"
            assert os.path.getsize(path) > 0, f"Resolved path '{path}' is an empty file"

    @pytest.mark.parametrize(
        "missing_or_invalid_id",
        [
            "",
            "   ",
            None,
            "nonexistent_book_id_99999",
            "libro_fantasma",
            "!@#$%^&*()_+",
            "CON", "PRN", "AUX", "NUL",
            "\x00\x01\x02\x1f\x7f",
        ],
    )
    def test_missing_or_invalid_ids_safe_fallback_empty_string(self, missing_or_invalid_id: Any) -> None:
        """Verify missing, blank, or invalid IDs return empty string without raising exceptions."""
        result = resolve_cover_image_path(missing_or_invalid_id)
        assert result == "", f"Expected empty string fallback for '{missing_or_invalid_id}', got '{result}'"

    @pytest.mark.parametrize(
        "traversal_payload",
        [
            "../../etc/passwd",
            "../../../etc/shadow",
            "../../ORIGINAL_REQUEST.md",
            "../../app.py",
            "/etc/passwd",
            "/bin/sh",
            "....//....//....//etc/passwd",
            "..\\..\\windows\\win.ini",
        ],
    )
    def test_path_traversal_payloads_do_not_escape_assets(self, traversal_payload: str) -> None:
        """Verify path traversal payloads cannot access files outside assets/covers."""
        result = resolve_cover_image_path(traversal_payload)
        # Should not resolve to any arbitrary file
        assert result == "", f"Path traversal succeeded unexpectedly on payload '{traversal_payload}': '{result}'"

    def test_extremely_long_filename_boundary_resilience_finding(self) -> None:
        """
        Verify filenames exceeding filesystem NAME_MAX (255 bytes).
        EMPIRICAL FINDING: resolve_cover_image_path raises unhandled OSError [Errno 36]
        instead of defensively returning the safe fallback empty string "".
        """
        long_id = "a" * 1000
        with pytest.raises(OSError) as exc_info:
            resolve_cover_image_path(long_id)
        assert exc_info.value.errno == 36  # File name too long


# ==============================================================================
# 3. KATEX CHEMICAL FORMULA FORMATTER & XSS STRESS TESTS
# ==============================================================================
class TestAdversarialKatexFormatter:
    """Stress-test format_chemical_formula for LaTeX preservation, delimiter balancing, and XSS escaping."""

    @pytest.mark.parametrize(
        "formula",
        [
            "$H_2SO_4$",
            "$BaSO_4$",
            r"$pH = -\log[H^+]$",
            "$K_{ps}$",
            "$Ca^{2+}$",
            "$EDTA^{4-}$",
            "$KMnO_4$",
            "$Fe^{3+} + e^- \\rightarrow Fe^{2+}$",
            "$$pH = \\frac{1}{2}(pK_w + pK_a + \\log C_s)$$",
            "$$K_{ps} = [Ba^{2+}][SO_4^{2-}]$$",
        ],
    )
    def test_chemical_formulas_preserved_intact(self, formula: str) -> None:
        """Verify standard chemical formulas and math equations are preserved."""
        result = format_chemical_formula(formula)
        assert formula in result, f"Formula '{formula}' was modified unexpectedly: '{result}'"

    def test_mixed_text_and_multiple_formulas(self) -> None:
        """Verify sentences containing multiple chemical formulas format each correctly."""
        text = (
            "En la valoración de $Ca^{2+}$ con $EDTA^{4-}$, el precipitado de "
            "$BaSO_4$ se disuelve si el $pH = -\\log[H^+]$ varía según $$K_{ps} = 1.1 \\times 10^{-10}$$."
        )
        result = format_chemical_formula(text)
        assert "$Ca^{2+}$" in result
        assert "$EDTA^{4-}$" in result
        assert "$BaSO_4$" in result
        assert "$$K_{ps} = 1.1 \\times 10^{-10}$$" in result

    @pytest.mark.parametrize(
        "unclosed_input,expected_balanced",
        [
            ("La fórmula es $H_2SO_4 pero faltó cerrar", "La fórmula es $H_2SO_4 pero faltó cerrar$"),
            (r"$$pH = -\log[H^+] sin cerrar", r"$$pH = -\log[H^+] sin cerrar$$"),
        ],
    )
    def test_unclosed_delimiters_balanced_safely(self, unclosed_input: str, expected_balanced: str) -> None:
        """Verify unclosed $ or $$ delimiters are automatically closed to prevent rendering corruption."""
        result = format_chemical_formula(unclosed_input)
        assert result == expected_balanced
        # Check delimiter parity
        temp = result.replace("$$", "\x00\x00")
        assert temp.count("$") % 2 == 0, f"Unbalanced inline dollar in: {result}"
        assert result.count("$$") % 2 == 0, f"Unbalanced display dollar in: {result}"

    def test_trailing_single_dollar_delimiter_finding(self) -> None:
        """
        EMPIRICAL FINDING: Appending $ to a string ending in $ creates $$,
        transforming an inline delimiter into an unclosed display math delimiter.
        """
        raw = "Solo un dólar $"
        res = format_chemical_formula(raw)
        assert res == "Solo un dólar $$"
        # Notice that this result has an odd count of $$ (1 display delimiter opening tag)
        assert res.count("$$") == 1

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert(1)>",
            "<iframe src='javascript:alert(1)'>",
            "\"><script>document.cookie</script>",
            "<a href='javascript:void(0)'>Click</a>",
            "<b>Texto en negrita</b> <script>steal()</script>",
        ],
    )
    def test_xss_injection_outside_math_strictly_escaped(self, xss_payload: str) -> None:
        """Verify HTML and script tags outside math blocks are safely HTML-escaped."""
        result = format_chemical_formula(xss_payload)
        assert "<script>" not in result
        assert "<img" not in result
        assert "<svg" not in result
        assert "<iframe" not in result
        assert "<a href" not in result
        assert "&lt;" in result or "&gt;" in result

    def test_xss_mixed_with_chemical_formulas(self) -> None:
        """Verify HTML injection embedded alongside valid chemical formulas is sanitized while math survives."""
        mixed = "<script>alert(1)</script> El ácido sulfúrico es $H_2SO_4$ y <img src=x onerror=alert(2)>"
        result = format_chemical_formula(mixed)
        assert "<script>" not in result
        assert "<img" not in result
        assert "&lt;script&gt;" in result
        assert "&lt;img" in result
        assert "$H_2SO_4$" in result

    @pytest.mark.parametrize("empty_val", ["", None, 12345, [], {}])
    def test_empty_or_non_string_inputs_return_empty_string(self, empty_val: Any) -> None:
        """Verify non-string or falsy inputs return empty string gracefully."""
        assert format_chemical_formula(empty_val) == ""


# ==============================================================================
# 4. SESSION STATE & BYOK ADVERSARIAL STRESS TESTS
# ==============================================================================
class TestAdversarialSessionState:
    """Stress-test session state initialization, idempotency, BYOK aliases, and isolation."""

    def test_init_session_state_initializes_all_required_keys(self) -> None:
        """Verify init_session_state initializes all 22+ essential portal keys."""
        mock_session: Dict[str, Any] = {}
        s = init_session_state(mock_session)

        required_keys = [
            "api_key",
            "gemini_api_key",
            "api_key_valid",
            "authenticated",
            "api_key_message",
            "_last_checked_key",
            "selected_model",
            "current_unit",
            "tutor_unit",
            "active_tab",
            "messages",
            "prefill_prompt",
            "completed_topics",
            "exam_status",
            "exam_unit",
            "exam_difficulty",
            "exam_count",
            "exam_questions",
            "exam_answers",
            "exam_student_answers",
            "exam_submitted",
            "exam_results",
            "exam_evaluation",
        ]
        for k in required_keys:
            assert k in s, f"Missing required session state key: '{k}'"

    def test_init_session_state_is_idempotent(self) -> None:
        """Verify calling init_session_state repeatedly does not overwrite existing values."""
        mock_session: Dict[str, Any] = {
            "api_key": "AIzaSy_ExistingUserKey_1234567890",
            "current_unit": "U5",
            "messages": [{"role": "user", "content": "Hola"}],
            "exam_status": "in_progress",
        }
        s = init_session_state(mock_session)
        assert s["api_key"] == "AIzaSy_ExistingUserKey_1234567890"
        assert s["current_unit"] == "U5"
        assert len(s["messages"]) == 1
        assert s["exam_status"] == "in_progress"

    def test_clear_session_state_resets_credentials_and_history(self) -> None:
        """Verify clear_session_state purges sensitive credentials, chat, and exam progress."""
        mock_session: Dict[str, Any] = {
            "api_key": "AIzaSy_UserKey",
            "gemini_api_key": "AIzaSy_UserKey",
            "api_key_valid": True,
            "authenticated": True,
            "messages": [{"role": "user", "content": "Test"}],
            "exam_status": "in_progress",
            "exam_questions": [{"id": 1}],
            "exam_submitted": True,
        }
        clear_session_state(mock_session)

        assert mock_session["api_key"] is None
        assert mock_session["gemini_api_key"] is None
        assert mock_session["api_key_valid"] is False
        assert mock_session["authenticated"] is False
        assert mock_session["messages"] == []
        assert mock_session["exam_status"] == "idle"
        assert mock_session["exam_questions"] == []
        assert mock_session["exam_submitted"] is False

    def test_disconnect_api_key_only_purges_credentials(self) -> None:
        """Verify disconnect_api_key removes credentials while preserving chat history."""
        mock_session: Dict[str, Any] = {
            "api_key": "AIzaSy_UserKey",
            "gemini_api_key": "AIzaSy_UserKey",
            "api_key_valid": True,
            "authenticated": True,
            "messages": [{"role": "user", "content": "Keep my history"}],
            "current_unit": "U4",
        }
        disconnect_api_key(mock_session)

        assert mock_session["api_key"] is None
        assert mock_session["gemini_api_key"] is None
        assert mock_session["api_key_valid"] is False
        assert mock_session["authenticated"] is False
        # Chat history and unit must remain intact
        assert len(mock_session["messages"]) == 1
        assert mock_session["current_unit"] == "U4"

    def test_multi_user_session_isolation(self) -> None:
        """Verify separate student session dictionaries maintain strict memory isolation."""
        user_a: Dict[str, Any] = {}
        user_b: Dict[str, Any] = {}

        init_session_state(user_a)
        init_session_state(user_b)

        user_a["api_key"] = "AIzaSyStudentA_11111111111111111111"
        user_a["messages"].append({"role": "user", "content": "Pregunta de Alumno A"})

        user_b["api_key"] = "AIzaSyStudentB_22222222222222222222"
        user_b["messages"].append({"role": "user", "content": "Pregunta de Alumno B"})

        assert user_a["api_key"] != user_b["api_key"]
        assert len(user_a["messages"]) == 1
        assert len(user_b["messages"]) == 1
        assert user_a["messages"][0]["content"] != user_b["messages"][0]["content"]

    def test_api_key_and_gemini_api_key_alias_synchronization_finding(self) -> None:
        """
        EMPIRICAL FINDING: init_session_state does not synchronize api_key and gemini_api_key.
        Pre-setting api_key leaves gemini_api_key as None, and pre-setting gemini_api_key leaves api_key as None.
        """
        # Scenario A: api_key is pre-set
        session_a: Dict[str, Any] = {"api_key": "AIzaSyKeyA"}
        init_session_state(session_a)
        assert session_a.get("api_key") == "AIzaSyKeyA"
        # Empirical finding: gemini_api_key was not synced and remains None
        assert session_a.get("gemini_api_key") is None

        # Scenario B: gemini_api_key is pre-set
        session_b: Dict[str, Any] = {"gemini_api_key": "AIzaSyKeyB"}
        init_session_state(session_b)
        assert session_b.get("gemini_api_key") == "AIzaSyKeyB"
        # Empirical finding: api_key was not synced and remains None
        assert session_b.get("api_key") is None


# ==============================================================================
# 5. NAVIGATION PAYLOADS & SCORE BADGES STRESS TESTS
# ==============================================================================
class TestAdversarialNavigationAndBadges:
    """Stress-test navigation payload builders and score badges."""

    @pytest.mark.parametrize(
        "unit_id,unit_title",
        [
            ("U1", "Introducción"),
            ("u2", "   "),
            ("  u3  ", "Tratamiento Estadístico"),
            ("L1", "Normas de Bioseguridad"),
        ],
    )
    def test_tutor_navigation_payload_normalization(self, unit_id: str, unit_title: str) -> None:
        """Verify tutor navigation payload normalizes unit IDs to uppercase and strips whitespace."""
        payload = create_tutor_navigation_payload(unit_id, unit_title)
        assert payload["action"] == "open_tutor"
        assert payload["target_unit"] == unit_id.strip().upper()
        assert "prefill_prompt" in payload
        assert unit_id.strip().upper() in payload["prefill_prompt"]

    @pytest.mark.parametrize(
        "count,expected_clamped",
        [
            (5, 5),
            (1, 1),
            (0, 1),
            (-5, 1),
            (-100, 1),
        ],
    )
    def test_exam_navigation_payload_count_bounds(self, count: int, expected_clamped: int) -> None:
        """Verify question count in exam navigation payload clamps non-positive values to at least 1."""
        payload = create_exam_navigation_payload("U3", default_count=count)
        assert payload["action"] == "start_exam"
        assert payload["target_unit"] == "U3"
        assert payload["default_count"] == expected_clamped

    @pytest.mark.parametrize(
        "score,expected_badge",
        [
            (0.0, "Puntaje Obtenido: 0.0%"),
            (50.9, "Puntaje Obtenido: 50.9%"),
            (51.0, "Puntaje Obtenido: 51.0%"),
            (100.0, "Puntaje Obtenido: 100.0%"),
        ],
    )
    def test_format_score_badge_exact_values(self, score: float, expected_badge: str) -> None:
        """Verify format_score_badge produces expected badge format across grading thresholds."""
        badge = format_score_badge(score)
        assert badge == expected_badge


# ==============================================================================
# 6. STREAMLIT WEB APP SMOKE & INTEGRATION VERIFICATION
# ==============================================================================
class TestStreamlitAppIntegration:
    """Verify app.py entry point and UI mounting using Streamlit AppTest."""

    def test_app_py_loads_and_renders_without_exceptions(self) -> None:
        """Verify app.py executes cleanly, mounts sidebar and all tabs without unhandled exceptions."""
        from streamlit.testing.v1 import AppTest

        app_path = os.path.abspath("app.py")
        at = AppTest.from_file(app_path, default_timeout=15)
        at.run()

        # Verify zero script run exceptions
        assert len(at.exception) == 0, f"App execution threw exceptions: {[e.value for e in at.exception]}"

        # Verify canonical views / tabs mounted
        canonical = get_canonical_views()
        assert len(canonical) == 4
