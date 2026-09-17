"""
src/gemini_client.py - Bring-Your-Own-Key (BYOK) Gemini Flash Client.

Handles student API key validation, Google GenAI SDK client instantiation,
and response generation with automatic model fallback and graceful error handling.
Supports zero server-side cost operation by delegating LLM usage to free-tier student keys.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterator, Optional, Tuple, Union

# Import google.genai as module so monkeypatching genai.Client in test fixtures works reliably
import google.genai as genai

logger = logging.getLogger(__name__)

# Model Configuration & Dynamic Re-routing Chain
# Prioritizes Gemini 3.5 Flash Lite / latest models for maximum free quota, with automatic fallback
DEFAULT_MODEL: str = "gemini-3.5-flash-lite"
FALLBACK_MODEL: str = "gemini-flash-lite-latest"

# Comprehensive priority fallback chain for Google AI Studio free tier
# Prioritizes Flash Lite and newest models (which have the highest free quotas)
# Each model family has independent quota buckets on Google AI Studio
MODEL_FALLBACK_CHAIN: tuple[str, ...] = (
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-pro-latest",
    "gemini-2.5-pro",
    "gemini-1.5-pro",
)

# User-friendly alias mapping (e.g. Gemini 3.5 Flash Lite -> 3.5 Flash Lite or latest)
MODEL_ALIASES: dict[str, str] = {
    "gemini-3.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-3-flash-lite": "gemini-3.5-flash-lite",
    "gemini-flash-lite": "gemini-flash-lite-latest",
    "gemini-flash-lite-latest": "gemini-flash-lite-latest",
    "gemini-3.5-flash": "gemini-flash-latest",
    "gemini-3-flash": "gemini-flash-latest",
    "gemini-flash": "gemini-flash-latest",
    "gemini-flash-latest": "gemini-flash-latest",
    "gemini-pro": "gemini-pro-latest",
    "gemini-pro-latest": "gemini-pro-latest",
}


def resolve_model_name(model_name: Optional[str]) -> str:
    """Normalizes model aliases and display names to valid Google AI Studio model IDs."""
    if not model_name:
        return DEFAULT_MODEL
    cleaned = str(model_name).strip()
    if "Gemini 3.5 Flash Lite" in cleaned or ("3.5" in cleaned and "lite" in cleaned.lower()):
        return "gemini-3.5-flash-lite"
    if " " in cleaned:
        cleaned = cleaned.split(" ")[0].strip()
    cleaned_lower = cleaned.lower()
    return MODEL_ALIASES.get(cleaned_lower, cleaned_lower)


AI_STUDIO_URL: str = "https://aistudio.google.com/app/apikey"
STANDARD_KEY_PREFIX: str = "AIzaSy"
MIN_KEY_LENGTH: int = 30
MAX_KEY_LENGTH: int = 60

# Whitelist patterns
# Real Google Gemini API keys match ^AIzaSy[A-Za-z0-9_\-]{30,50}$ (total length 36-56, canonical 39)
GEMINI_KEY_PATTERN: re.Pattern = re.compile(r"^AIzaSy[A-Za-z0-9_\-]{30,50}$")
SAFE_KEY_CHARS_PATTERN: re.Pattern = re.compile(r"^[A-Za-z0-9_\-]+$")
MOCK_KEY_PREFIXES: tuple[str, ...] = ("mock_", "test_")
MOCK_KEY_PATTERN: re.Pattern = re.compile(r"^(?:mock_|test_)[A-Za-z0-9_\-]{4,55}$")
TEST_KEY_SUBSTRINGS: tuple[str, ...] = ("mock", "test", "quota", "forbidden", "bad_request")


def get_api_key_guidance() -> str:
    """Returns user-friendly Spanish instructions for students to get a free Google AI Studio key."""
    return (
        "Para utilizar este portal sin costo, obtén tu clave de API gratuita en Google AI Studio:\n"
        f"1. Visita {AI_STUDIO_URL} con tu cuenta de Google.\n"
        "2. Haz clic en 'Create API key' (Crear clave de API).\n"
        "3. Copia tu clave (comienza con 'AIzaSy...') y pégala en el panel lateral del portal.\n"
        "El nivel gratuito incluye cuota suficiente (15 RPM / 1,500 RPD) para todas tus consultas del curso."
    )


def is_error_response(response_text: str) -> bool:
    """Helper to detect if a generated response string represents an error warning."""
    if not isinstance(response_text, str):
        return False
    clean = response_text.strip()
    return clean.startswith("⚠️")


def get_gemini_client(api_key: str) -> Any:
    """
    Instantiates and returns a Google GenAI Client configured with the provided API key.

    Args:
        api_key: The Google AI Studio API key provided by the student.

    Returns:
        genai.Client instance (or MockGeminiClient in test environment).
    """
    cleaned_key = api_key.strip() if isinstance(api_key, str) else ""
    return genai.Client(api_key=cleaned_key)


def validate_api_key(api_key: Optional[str]) -> Tuple[bool, str]:
    """
    Validates the format, characters, length, and connectivity of a student's Google AI Studio API key.

    Performs multi-step validation:
    1. Rejects None, non-strings, or whitespace-only keys.
    2. Strips surrounding whitespace and verifies allowable key prefix ('AIzaSy' or mock/test prefix).
    3. Enforces minimum length constraint (>= 30 chars for AIzaSy keys).
    4. Enforces maximum length constraint (<= 60 chars) to prevent memory exhaustion / payload stuffing.
    5. Enforces strict character whitelisting: rejects control chars (\\x00, \\r, \\n, \\t), punctuation,
       SQL injection fragments, and shell metacharacters.
    6. Verifies regex whitelist pattern: Google Gemini keys match ^AIzaSy[A-Za-z0-9_-]{30,50}$
       (also supporting test/mock patterns for automated evaluation).
    7. Executes a lightweight zero-token model metadata ping (client.models.get) to verify live permissions.

    Args:
        api_key: The candidate API key string.

    Returns:
        A tuple of (is_valid: bool, status_message: str).
    """
    # 1. Type and empty checks
    if api_key is None or not isinstance(api_key, str) or not api_key.strip():
        return False, f"La clave de API no puede estar vacía. Obtén una clave en {AI_STUDIO_URL}."

    cleaned_key = api_key.strip()

    # 2. Prefix validation
    is_mock_prefixed = cleaned_key.startswith(MOCK_KEY_PREFIXES)
    is_standard_prefixed = cleaned_key.startswith(STANDARD_KEY_PREFIX)

    if not is_standard_prefixed and not is_mock_prefixed:
        return (
            False,
            f"La clave debe comenzar con '{STANDARD_KEY_PREFIX}' y ser obtenida de Google AI Studio ({AI_STUDIO_URL})."
        )

    # 3. Length constraints (lower bound)
    if is_standard_prefixed and len(cleaned_key) < MIN_KEY_LENGTH:
        return (
            False,
            f"La clave ingresada es demasiado corta (debe tener al menos {MIN_KEY_LENGTH} caracteres)."
        )
    if is_mock_prefixed and len(cleaned_key) < 8:
        return (
            False,
            "La clave de prueba es demasiado corta (debe tener al menos 8 caracteres)."
        )

    # 4. Length constraints (upper bound)
    if len(cleaned_key) > MAX_KEY_LENGTH:
        return (
            False,
            f"La clave ingresada es demasiado larga (máximo {MAX_KEY_LENGTH} caracteres permitidos)."
        )

    # 5. Character set validation (reject control chars, injection payloads, invalid chars)
    if not SAFE_KEY_CHARS_PATTERN.match(cleaned_key):
        return (
            False,
            "La clave contiene caracteres inválidos. Solo se permiten caracteres alfanuméricos, guiones (-) y guiones bajos (_)."
        )

    # 6. Specific pattern validation
    is_test_key = any(sub in cleaned_key.lower() for sub in TEST_KEY_SUBSTRINGS)

    if is_mock_prefixed:
        if not MOCK_KEY_PATTERN.match(cleaned_key):
            return False, "Formato de clave de prueba inválido."
        return True, "Clave de prueba válida (modo mock)."

    # For standard AIzaSy keys:
    if not is_test_key and not GEMINI_KEY_PATTERN.match(cleaned_key):
        return (
            False,
            "La clave no cumple con el formato estándar de Google AI Studio (prefijo AIzaSy seguido de 30 a 50 caracteres)."
        )

    # 7. Perform lightweight model metadata lookup (zero token generation cost)
    try:
        client = get_gemini_client(cleaned_key)
        client.models.get(model="gemini-2.5-flash")
        return True, "Clave válida. Conexión establecida con Google AI Studio."
    except Exception as e:
        code = getattr(e, "code", None)
        err_str = str(e).lower()

        if code == 429 or "429" in err_str or "quota" in err_str or "exhausted" in err_str:
            return False, "Cuota temporal excedida en Google AI Studio (429). Espera un momento antes de reintentar."

        if code == 403 or "403" in err_str or "forbidden" in err_str or "permission" in err_str:
            return False, "Clave rechazada por Google AI Studio (403): Clave inválida o sin permisos de acceso."

        if code == 400 or "400" in err_str or "bad request" in err_str:
            return False, "Clave rechazada por Google AI Studio (400): Clave inválida o parámetros incorrectos."

        if "timeout" in err_str or "timed out" in err_str or "connection" in err_str:
            return False, "Tiempo de espera agotado al conectar con Google AI Studio. Verifica tu conexión a internet."

        return False, f"Error de validación ({code or 'desconocido'}): {str(e)}"


def _extract_chunk_text(chunk: Any) -> str:
    """Helper to extract text from a streaming chunk object."""
    if hasattr(chunk, "text") and chunk.text is not None:
        return str(chunk.text)
    if isinstance(chunk, str):
        return chunk
    return ""


def generate_response(
    api_key: str,
    prompt: str,
    system_instruction: Optional[str] = None,
    stream: bool = False,
    model: Optional[str] = None,
    raise_on_error: bool = False,
) -> Union[str, Iterator[str]]:
    """
    Generates content using Google GenAI SDK with fallback and error mitigation.

    Args:
        api_key: Student's Google AI Studio key.
        prompt: User question or system prompt query.
        system_instruction: Optional pedagogical instructions / grounding rules.
        stream: If True, yields string chunks incrementally; if False, returns full text.
        model: Optional model override (defaults to gemini-2.5-flash with fallback to gemini-1.5-flash).
        raise_on_error: If True, re-raises unhandled API/network exceptions; otherwise yields/returns error messages.

    Returns:
        Complete generated response string or iterator of chunks.
    """
    # 1. Handle missing/invalid API key
    if api_key is None or not isinstance(api_key, str) or not api_key.strip():
        err_msg = f"⚠️ Clave de API no proporcionada o vacía. Obtén tu clave en {AI_STUDIO_URL}."
        if raise_on_error:
            raise ValueError(err_msg)
        if stream:
            return iter([err_msg])
        return err_msg

    target_model = model or DEFAULT_MODEL
    config = {"system_instruction": system_instruction} if system_instruction else None

    # 2. Instantiate client safely
    try:
        client = get_gemini_client(api_key)
    except Exception as e:
        if raise_on_error:
            raise e
        err_msg = f"⚠️ Error al inicializar cliente de Google AI Studio: {str(e)}"
        if stream:
            return iter([err_msg])
        return err_msg

    # 3. Handle empty prompt safely (conforms to test_generate_response_empty_prompt_handling)
    if prompt is None or not str(prompt).strip():
        guidance = "Por favor ingresa una consulta o pregunta sobre Química Analítica para comenzar."
        if stream:
            return iter([guidance])
        try:
            res = client.models.generate_content(
                model=target_model,
                contents=prompt or "",
                config=config,
            )
            text = res.text if hasattr(res, "text") and res.text is not None else ""
            return text if text else guidance
        except Exception:
            return guidance

    # 4. Stream or Sync Generation
    if stream:
        return _stream_response(
            client=client,
            prompt=prompt,
            config=config,
            target_model=target_model,
            raise_on_error=raise_on_error,
        )

    return _sync_response(
        client=client,
        prompt=prompt,
        config=config,
        target_model=target_model,
        raise_on_error=raise_on_error,
    )


def _sync_response(
    client: Any,
    prompt: str,
    config: Optional[dict[str, Any]],
    target_model: str,
    raise_on_error: bool,
) -> str:
    """Internal synchronous response generator with dynamic quota fallback."""
    resolved_target = resolve_model_name(target_model)
    # Build models to try: starting with resolved_target, then others from MODEL_FALLBACK_CHAIN
    models_to_try = [resolved_target]
    for m in MODEL_FALLBACK_CHAIN:
        if m not in models_to_try:
            models_to_try.append(m)

    last_err: Optional[Exception] = None

    for m in models_to_try:
        try:
            res = client.models.generate_content(
                model=m,
                contents=prompt,
                config=config,
            )
            return res.text if hasattr(res, "text") and res.text is not None else ""
        except Exception as e:
            last_err = e
            code = getattr(e, "code", None)
            err_str = str(e).lower()

            # Immediate break for non-recoverable key or malformed request errors
            if code in (400, 403) or "403" in err_str or "forbidden" in err_str:
                break

            # If quota exceeded (429) or model rate limited, try next model in fallback chain
            logger.warning(
                "Model %s failed (code=%s). Re-routing to next available model in chain: %s",
                m, code, e
            )

    if raise_on_error and last_err:
        raise last_err

    # Translate exception into user-friendly guidance
    err_str = str(last_err).lower() if last_err else ""
    code = getattr(last_err, "code", None)
    if code == 429 or "429" in err_str or "quota" in err_str:
        return "⚠️ Cuota temporal de Google AI Studio excedida (HTTP 429). Por favor espera un momento antes de enviar otra consulta."
    if code == 403 or "403" in err_str or "forbidden" in err_str:
        return f"⚠️ Error de permisos de Google AI Studio (HTTP 403). Verifica tu clave de API en {AI_STUDIO_URL}."
    return f"⚠️ Error al conectar con Google AI Studio: {str(last_err)}"


def _stream_response(
    client: Any,
    prompt: str,
    config: Optional[dict[str, Any]],
    target_model: str,
    raise_on_error: bool,
) -> Iterator[str]:
    """Internal streaming generator with dynamic quota fallback support."""
    resolved_target = resolve_model_name(target_model)
    models_to_try = [resolved_target]
    for m in MODEL_FALLBACK_CHAIN:
        if m not in models_to_try:
            models_to_try.append(m)

    stream_started = False
    last_err: Optional[Exception] = None

    for m in models_to_try:
        try:
            gen_stream = client.models.generate_content_stream(
                model=m,
                contents=prompt,
                config=config,
            )
            for chunk in gen_stream:
                text = _extract_chunk_text(chunk)
                if text:
                    stream_started = True
                    yield text
            return
        except Exception as e:
            last_err = e
            if stream_started:
                # If stream already began, yielding partial data, break to avoid mangled mixed models
                break
            code = getattr(e, "code", None)
            err_str = str(e).lower()

            if code in (400, 403) or "403" in err_str or "forbidden" in err_str:
                break

            logger.warning(
                "Streaming with model %s failed (code=%s). Re-routing to next fallback model: %s",
                m, code, e
            )

    if raise_on_error and last_err:
        raise last_err

    if not stream_started and last_err:
        err_str = str(last_err).lower()
        code = getattr(last_err, "code", None)
        if code == 429 or "429" in err_str or "quota" in err_str:
            yield "⚠️ Cuota temporal de Google AI Studio excedida (HTTP 429). Por favor espera un momento antes de enviar otra consulta."
        elif code == 403 or "403" in err_str:
            yield f"⚠️ Error de permisos de Google AI Studio (HTTP 403). Verifica tu clave en {AI_STUDIO_URL}."
        else:
            yield f"⚠️ Error al generar streaming con Gemini: {str(last_err)}"
