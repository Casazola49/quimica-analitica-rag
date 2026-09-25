"""
src/ui.py - User Interface Components, Session State Management, Textbook Catalog,
WhatsApp Integration, and Pedagogical Views for Química Analítica Educational Portal.

Provides:
1. Pure Python Helpers (Headless-safe, 100% testable without Streamlit context):
   - WhatsApp URL generator & message formatter (generate_whatsapp_url, format_book_request_message, build_whatsapp_request_url)
   - Textbook catalog metadata provider (get_course_catalog, get_catalog_cards, get_book_by_id)
   - Dual-candidate cover resolver (resolve_cover_image_path, get_cover_image_path)
   - KaTeX chemical formula formatter & sanitizer (format_chemical_formula)
   - Scorecard badge formatter (format_score_badge)
   - Navigation action payload builders (create_tutor_navigation_payload, create_exam_navigation_payload)
   - Session state managers (init_session_state, clear_session_state, disconnect_api_key)

2. Streamlit View Renderers (Guarded by STREAMLIT_AVAILABLE):
   - render_sidebar_byok / render_sidebar
   - render_library_tab
   - render_syllabus_tab
   - render_tutor_tab
   - render_exam_tab
"""

from __future__ import annotations

import html
import logging
import os
import re
import textwrap
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Defensive Streamlit import for headless test safety
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    st = None  # type: ignore
    STREAMLIT_AVAILABLE = False


# ==============================================================================
# Constants & Canonical Views
# ==============================================================================
DEFAULT_DEPARTMENT_PHONE: str = os.environ.get("WHATSAPP_PHONE", "59176932485")

CANONICAL_VIEWS: List[str] = [
    "Syllabus Navigator / Temario",
    "Tutor Chat / Tutor Inteligente",
    "Exam Simulator / Simulador de Exámenes",
    "Textbook Library / Biblioteca & WhatsApp",
]


def get_canonical_views() -> List[str]:
    """Returns the 4 canonical portal view identifiers required by R2."""
    return list(CANONICAL_VIEWS)


# ==============================================================================
# 1. WhatsApp Request Integration (Pure Python, Headless Safe)
# ==============================================================================
def generate_whatsapp_url(phone_number: str, message: str) -> str:
    """
    Generates a standard WhatsApp click-to-chat URL:
    https://wa.me/<PHONE>?text=<ENCODED_MESSAGE>

    Cleans phone digits and percent-encodes spaces to %20 and newlines to %0A.
    Automatically prepends country code 591 for 8-digit Bolivian numbers.
    """
    clean_phone = re.sub(r"[^\d]", "", str(phone_number or ""))
    if not clean_phone:
        clean_phone = re.sub(r"[^\d]", "", DEFAULT_DEPARTMENT_PHONE)
    elif len(clean_phone) == 8 and clean_phone.startswith(("6", "7")):
        clean_phone = f"591{clean_phone}"

    encoded_msg = urllib.parse.quote(str(message or ""))
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"



def format_book_request_message(
    book_title: str = "",
    edition: str = "",
    author: str = "",
    **kwargs: Any,
) -> str:
    """
    Formats a pre-filled student book request message in Spanish.
    Incorporates book title, edition, and author.
    """
    title = kwargs.get("title", book_title) or "Química Analítica"
    ed_part = f" ({edition})" if edition else ""
    aut_part = f", de {author}" if author else ""

    return (
        f"Hola, soy estudiante de Química Analítica. "
        f"Me gustaría solicitar acceso o copia del libro '{title}'{ed_part}{aut_part}. "
        f"¡Muchas gracias!"
    )


def build_whatsapp_request_url(
    book: Dict[str, Any],
    phone: Optional[str] = None,
) -> str:
    """
    High-level modular builder generating a WhatsApp request URL from a book dictionary.
    """
    phone_number = phone or book.get("phone") or DEFAULT_DEPARTMENT_PHONE
    title = book.get("title") or book.get("book_title") or "Texto de Química Analítica"
    edition = book.get("edition") or ""
    author = book.get("authors") or book.get("author") or ""

    msg = book.get("whatsapp_message") or format_book_request_message(
        book_title=title,
        edition=edition,
        author=author,
    )
    return generate_whatsapp_url(phone_number=phone_number, message=msg)


# ==============================================================================
# 2. Textbook Catalog & Asset Resolution
# ==============================================================================
COURSE_TEXTBOOK_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "skoog_9ed_es",
        "title": "Fundamentos de Química Analítica",
        "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "author": "Douglas A. Skoog et al.",
        "edition": "9ª Edición (2015)",
        "year": "2015",
        "language": "Español",
        "total_pages": 1090,
        "cover_image": "assets/covers/skoog_9ed_es.png",
        "syllabus_units": ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9"],
        "syllabus_units_label": "U1 a U9 (Texto Base Teórico)",
        "description": "Texto guía principal de Química Analítica Cuantitativa. Cubre desde metrología y gravimetría hasta volumetrías de neutralización, complejos y redox.",
    },
    {
        "id": "aguilar_2ed_es",
        "title": "Introducción a los Equilibrios Iónicos",
        "authors": "Manuel Aguilar San Juan",
        "author": "Manuel Aguilar San Juan",
        "edition": "2ª Edición (2000)",
        "year": "2000",
        "language": "Español",
        "total_pages": 538,
        "cover_image": "assets/covers/aguilar_2ed_es.png",
        "syllabus_units": ["U4", "U6", "U7"],
        "syllabus_units_label": "U4, U6, U7 (Equilibrios Iónicos)",
        "description": "Referencia esencial para balances de masa y carga, diagramas logarítmicos de concentración y equilibrios ácido-base y complejométricos.",
    },
    {
        "id": "day_underwood_5ed_es",
        "title": "Química Analítica Cuantitativa",
        "authors": "R. A. Day, Jr., A. L. Underwood",
        "author": "R. A. Day & A. L. Underwood",
        "edition": "5ª Edición (1989)",
        "year": "1989",
        "language": "Español",
        "total_pages": 870,
        "cover_image": "assets/covers/day_underwood_5ed_es.png",
        "syllabus_units": ["U1", "U3", "U5", "U6", "U7", "U8", "U9", "L4", "L5"],
        "syllabus_units_label": "U1-U9, L4-L5 (Clásico de Volumetría)",
        "description": "Tratado tradicional de química cuantitativa con gran profundidad en aplicaciones prácticas de precipitación, neutralización y permanganometría.",
    },
    {
        "id": "day_underwood_6ed_en",
        "title": "Quantitative Analysis",
        "authors": "R. A. Day, Jr., A. L. Underwood",
        "author": "R. A. Day & A. L. Underwood",
        "edition": "6th Edition (1991)",
        "year": "1991",
        "language": "English",
        "total_pages": 712,
        "cover_image": "assets/covers/day_underwood_6ed_en.png",
        "syllabus_units": ["U1", "U2", "U3", "U5", "U6", "U7", "U8", "U9"],
        "syllabus_units_label": "U1 a U9 (English Reference)",
        "description": "Modern English edition with enhanced treatment of statistical data handling and titrimetric methods.",
    },
    {
        "id": "skoog_10ed_en",
        "title": "Fundamentals of Analytical Chemistry",
        "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "author": "Douglas A. Skoog et al.",
        "edition": "10th Edition (2022)",
        "year": "2022",
        "language": "English",
        "total_pages": 1165,
        "cover_image": "assets/covers/skoog_10ed_en.png",
        "syllabus_units": ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9"],
        "syllabus_units_label": "U1 a U9 (Edición Más Reciente)",
        "description": "Latest international reference edition with updated spreadsheet applications and modern error analysis.",
    },
    {
        "id": "skoog_solutions_10ed_en",
        "title": "Student Solutions Manual: Fundamentals of Analytical Chemistry",
        "authors": "Douglas A. Skoog, Donald M. West, F. James Holler, Stanley R. Crouch",
        "author": "Douglas A. Skoog et al.",
        "edition": "10th Edition (2022)",
        "year": "2022",
        "language": "English",
        "total_pages": 233,
        "cover_image": "assets/covers/skoog_solutions_10ed_en.png",
        "syllabus_units": ["U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9"],
        "syllabus_units_label": "U2 a U9 (Manual de Problemas)",
        "description": "Solucionario oficial paso a paso con desarrollos numéricos completos de problemas de equilibrio y valoración.",
    },
    {
        "id": "skoog_instrumental_7ed_es",
        "title": "Principios de Análisis Instrumental",
        "authors": "Douglas A. Skoog, F. James Holler, Stanley R. Crouch",
        "author": "Douglas A. Skoog et al.",
        "edition": "7ª Edición (2019)",
        "year": "2019",
        "language": "Español",
        "total_pages": 888,
        "cover_image": "assets/covers/skoog_instrumental_7ed_es.png",
        "syllabus_units": ["L6", "L7", "L8"],
        "syllabus_units_label": "L6, L7, L8 (Métodos Instrumentales)",
        "description": "Texto de apoyo para prácticas de laboratorio de electrodeposición (L6), espectrofotometría UV-Vis (L7) y fotometría de llama (L8).",
    },
    {
        "id": "kolthoff_vol1_2ed_en",
        "title": "Treatise on Analytical Chemistry: Theory and Practice (Part 1, Vol. 1)",
        "authors": "I. M. Kolthoff, Philip J. Elving, Edward J. Meehan",
        "author": "I. M. Kolthoff & P. J. Elving",
        "edition": "2nd Edition (1978)",
        "year": "1978",
        "language": "English",
        "total_pages": 920,
        "cover_image": "assets/covers/kolthoff_vol1_2ed_en.png",
        "syllabus_units": ["U1", "U2", "U4"],
        "syllabus_units_label": "U1, U2, U4 (Tratado Avanzado)",
        "description": "Monografía de referencia avanzada sobre metodología general de errores, muestreo y principios termodinámicos de soluciones.",
    },
    {
        "id": "kolthoff_vol2_en",
        "title": "Treatise on Analytical Chemistry: Part 1, Vol. 2",
        "authors": "I. M. Kolthoff, Philip J. Elving",
        "author": "I. M. Kolthoff & P. J. Elving",
        "edition": "1st Edition (1979)",
        "year": "1979",
        "language": "English",
        "total_pages": 1322,
        "cover_image": "assets/covers/kolthoff_vol2_en.png",
        "syllabus_units": ["U3", "U4", "L2"],
        "syllabus_units_label": "U3, U4, L2 (Precipitación y Disolución)",
        "description": "Tratamiento riguroso de mecanismos de nucleación, crecimiento cristalino de Von Weimarn y fenómenos de coprecipitación.",
    },
    {
        "id": "kolthoff_vol3_2ed_en",
        "title": "Treatise on Analytical Chemistry: Part 1, Vol. 3",
        "authors": "I. M. Kolthoff, Philip J. Elving",
        "author": "I. M. Kolthoff & P. J. Elving",
        "edition": "2nd Edition (1983)",
        "year": "1983",
        "language": "English",
        "total_pages": 613,
        "cover_image": "assets/covers/kolthoff_vol3_2ed_en.png",
        "syllabus_units": ["U8", "U9", "L5"],
        "syllabus_units_label": "U8, U9, L5 (Teoría y Cinética Redox)",
        "description": "Fundamento exhaustivo de potenciales formales, cinética de transferencia de electrones y catalizadores redox.",
    },
    {
        "id": "kolthoff_vol5_en",
        "title": "Treatise on Analytical Chemistry: Optical Methods (Part 1, Vol. 5)",
        "authors": "I. M. Kolthoff, Philip J. Elving, Ernest B. Sandell",
        "author": "I. M. Kolthoff et al.",
        "edition": "1st Edition (1982)",
        "year": "1982",
        "language": "English",
        "total_pages": 672,
        "cover_image": "assets/covers/kolthoff_vol5_en.png",
        "syllabus_units": ["L7", "L8"],
        "syllabus_units_label": "L7, L8 (Métodos Ópticos)",
        "description": "Fundamentos físicos de la ley de Beer-Lambert, desviaciones espectrales y absorción/emisión atómica.",
    },
]


def get_course_catalog() -> List[Dict[str, Any]]:
    """
    Returns the 11-textbook course catalog metadata with book IDs, titles,
    authors, editions, relevant units, and pre-computed WhatsApp request URLs.
    """
    catalog = []
    for item in COURSE_TEXTBOOK_CATALOG:
        book = dict(item)
        msg = format_book_request_message(
            book_title=book["title"],
            edition=book["edition"],
            author=book["author"],
        )
        book["whatsapp_message"] = msg
        book["whatsapp_url"] = generate_whatsapp_url(DEFAULT_DEPARTMENT_PHONE, msg)
        catalog.append(book)
    return catalog


def get_catalog_cards(db_path: str = "data/quimica_analitica.db") -> List[Dict[str, Any]]:
    """
    Returns enriched textbook catalog cards.
    """
    return get_course_catalog()


def get_book_by_id(book_id: str) -> Optional[Dict[str, Any]]:
    """Finds a textbook in the catalog by book_id."""
    clean_id = str(book_id or "").strip().lower()
    for book in get_course_catalog():
        if book["id"].lower() == clean_id:
            return book
    return None


def resolve_cover_image_path(book_id: str, assets_dir: str = "assets/covers") -> str:
    """
    Dual-candidate cover resolver: checks <book_id>_cover.png, <book_id>.png,
    and returns absolute/relative path if found, or empty string on fallback.
    """
    clean_id = str(book_id or "").strip()
    base_dir = Path(assets_dir)
    candidates = [
        base_dir / f"{clean_id}_cover.png",
        base_dir / f"{clean_id}.png",
        base_dir / f"{clean_id}.jpg",
        base_dir / f"{clean_id.lower()}_cover.png",
        base_dir / f"{clean_id.lower()}.png",
    ]
    for p in candidates:
        if p.is_file() and p.stat().st_size > 0:
            return str(p)
    return ""


# Alias for backward compatibility
get_cover_image_path = resolve_cover_image_path


# ==============================================================================
# 3. Chemical Formula & KaTeX Formatter
# ==============================================================================
def format_chemical_formula(text: str) -> str:
    """
    KaTeX chemical formula formatter ($H_2SO_4$, $BaSO_4$, $pH = -\\log[H^+]$, $K_{ps}$, $Ca^{2+}$, $EDTA^{4-}$).
    Sanitizes HTML/XSS outside math blocks while preserving LaTeX math and balancing
    unclosed delimiters to prevent rendering breaks.
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Escape unsafe HTML tags outside of math blocks ($$...$$ and $...$)
    parts: List[str] = []
    math_pattern = re.compile(r"(\$\$.*?\$\$|\$[^\$]+?\$)", re.DOTALL)
    last_end = 0
    for match in math_pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            non_math = text[last_end:start]
            parts.append(html.escape(non_math))
        parts.append(match.group(0))
        last_end = end
    if last_end < len(text):
        parts.append(html.escape(text[last_end:]))

    sanitized = "".join(parts)

    # 2. Delimiter balancing for display math $$
    if sanitized.count("$$") % 2 != 0:
        sanitized += "$$"

    # 3. Delimiter balancing for inline math $ (excluding $$)
    temp = sanitized.replace("$$", "\x00\x00")
    if temp.count("$") % 2 != 0:
        sanitized += "$"

    return sanitized


def format_score_badge(score: float) -> str:
    """Formats score percentage into standard test-compliant badge string."""
    return f"Puntaje Obtenido: {score}%"


# ==============================================================================
# 4. Navigation Action Payload Builders
# ==============================================================================
def create_tutor_navigation_payload(unit_id: str, unit_title: str = "") -> Dict[str, Any]:
    """Builds navigation action payload to transition to the Tutor tab."""
    u_id = unit_id.strip().upper()
    title_part = f" ({unit_title.strip()})" if unit_title and unit_title.strip() else ""
    return {
        "action": "open_tutor",
        "target_unit": u_id,
        "prefill_prompt": f"Hola, quiero repasar los conceptos de la {u_id}{title_part}.",
    }


def create_exam_navigation_payload(unit_id: str, default_count: int = 3) -> Dict[str, Any]:
    """Builds navigation action payload to transition to the Exam Simulator tab."""
    return {
        "action": "start_exam",
        "target_unit": unit_id.strip().upper(),
        "default_count": max(1, default_count),
    }


# ==============================================================================
# 5. Session State Management (Headless Safe)
# ==============================================================================
_HEADLESS_SESSION: Dict[str, Any] = {}


def get_session(session: Optional[Dict[str, Any]] = None) -> Any:
    """
    Returns the target session dictionary:
    - If explicit dict is passed: returns that dict.
    - If Streamlit runtime is active: returns st.session_state.
    - Otherwise: returns the headless fallback dictionary.
    """
    if session is not None:
        return session
    if STREAMLIT_AVAILABLE and st is not None:
        try:
            if hasattr(st, "runtime") and hasattr(st.runtime, "exists") and st.runtime.exists():
                return st.session_state
        except Exception:
            pass
    return _HEADLESS_SESSION


def init_session_state(session: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Initializes api_key, gemini_api_key, api_key_valid, messages, current_unit,
    exam_state, active_tab, and other essential session keys idempotently.
    """
    s = get_session(session)
    defaults: Dict[str, Any] = {
        "api_key": None,
        "gemini_api_key": None,
        "api_key_valid": False,
        "authenticated": False,
        "api_key_message": "",
        "_last_checked_key": None,
        "selected_model": "gemini-2.5-flash",
        "current_unit": "U1",
        "tutor_unit": "U1",
        "active_tab": "Syllabus Navigator",
        "messages": [],
        "prefill_prompt": None,
        "completed_topics": [],
        "exam_status": "idle",
        "exam_unit": "U3",
        "exam_difficulty": "media",
        "exam_count": 3,
        "exam_questions": [],
        "exam_answers": {},
        "exam_student_answers": {},
        "exam_submitted": False,
        "exam_results": None,
        "exam_evaluation": None,
        "theme_mode": "sumie_dark",
    }
    for k, v in defaults.items():
        if k not in s:
            s[k] = v
    return s


def clear_session_state(session: Optional[Dict[str, Any]] = None) -> None:
    """Purges student session state, resetting credentials, chat history, and exam state."""
    s = get_session(session)
    s["api_key"] = None
    s["gemini_api_key"] = None
    s["api_key_valid"] = False
    s["authenticated"] = False
    s["api_key_message"] = ""
    s["_last_checked_key"] = None
    s["messages"] = []
    s["prefill_prompt"] = None
    s["completed_topics"] = []
    s["exam_status"] = "idle"
    s["exam_questions"] = []
    s["exam_answers"] = {}
    s["exam_student_answers"] = {}
    s["exam_submitted"] = False
    s["exam_results"] = None
    s["exam_evaluation"] = None
    s["current_unit"] = "U1"
    s["tutor_unit"] = "U1"


def disconnect_api_key(session: Optional[Dict[str, Any]] = None) -> None:
    """Disconnects and purges only the API key from memory."""
    s = get_session(session)
    s.pop("api_key", None)
    s.pop("gemini_api_key", None)
    s["api_key"] = None
    s["gemini_api_key"] = None
    s["api_key_valid"] = False
    s["authenticated"] = False
    s["api_key_message"] = ""
    s["_last_checked_key"] = None


# ==============================================================================
# 5b. Visual Design System & Themes (Alquímica-33: Sumi-e & Washi Paper)
# ==============================================================================
def get_theme_css(theme_mode: str = "sumie_dark") -> str:
    """
    Generates dynamic CSS adhering strictly to the 'Alquímica-33' Sumi-e & Washi design system.
    Features:
    - GPU-accelerated hardware animations (0% CPU cost):
      * Sun radiance breathing pulse (Hinomaru)
      * Soaring crane silhouette flight
      * Drifting Momiji / Sakura leaf particles
      * Interactive Hanko stamp imprint on hover/click
      * Dynamic glowing crimson borders for cards, inputs, and tabs
    - 'sumie_dark': Deep ink black (#0a0a0a), charcoal cards (#141414), vermilion red (#dc2626) accents.
    - 'washi_light': Warm ivory rice paper (#f9f8f4), dark ink typography (#111111), vermilion red (#dc2626) stamps.
    """
    is_dark = (theme_mode == "sumie_dark")

    if is_dark:
        bg_app = "#0a0a0a"
        bg_radial = "radial-gradient(circle at 85% 15%, rgba(220, 38, 38, 0.08) 0%, transparent 45%), linear-gradient(180deg, #0d0d0d 0%, #080808 100%)"
        bg_sidebar = "#0e0e0e"
        border_sidebar = "#222222"
        text_primary = "#f5f5f5"
        text_secondary = "#a3a3a3"
        card_bg = "#141414"
        card_border = "#262626"
        card_border_hover = "#dc2626"
        btn_bg = "#181818"
        btn_text = "#f0f0f0"
        btn_border = "#333333"
        input_bg = "#141414"
        input_border = "#333333"
        input_text = "#f0f0f0"
        tab_text = "#888888"
        tab_active_text = "#ffffff"
        tab_active_bg = "linear-gradient(180deg, transparent 0%, rgba(220, 38, 38, 0.14) 100%)"
        tab_border = "#222222"
        chat_user_bg = "#1c1c1c"
        chat_user_border = "#333333"
        chat_ai_bg = "#121212"
        chat_ai_border = "#262626"
        alert_info_bg = "#161616"
        alert_info_border = "#2e2e2e"
        alert_info_text = "#d4d4d4"
        leaf_color = "rgba(220, 38, 38, 0.65)"
        leaf_glow = "rgba(239, 68, 68, 0.8)"
    else:
        bg_app = "#f9f8f4"
        bg_radial = "radial-gradient(circle at 85% 15%, rgba(220, 38, 38, 0.05) 0%, transparent 45%), linear-gradient(180deg, #fdfbf7 0%, #f3efe6 100%)"
        bg_sidebar = "#f2ede3"
        border_sidebar = "#dfd7c9"
        text_primary = "#141414"
        text_secondary = "#555555"
        card_bg = "#ffffff"
        card_border = "#e2dcd0"
        card_border_hover = "#dc2626"
        btn_bg = "#ffffff"
        btn_text = "#141414"
        btn_border = "#d8cfbf"
        input_bg = "#ffffff"
        input_border = "#d4cbba"
        input_text = "#141414"
        tab_text = "#666666"
        tab_active_text = "#111111"
        tab_active_bg = "linear-gradient(180deg, transparent 0%, rgba(220, 38, 38, 0.08) 100%)"
        tab_border = "#dfd7c9"
        chat_user_bg = "#eae3d4"
        chat_user_border = "#d8cdb8"
        chat_ai_bg = "#ffffff"
        chat_ai_border = "#e0d8c8"
        alert_info_bg = "#f5f0e6"
        alert_info_border = "#e2dacb"
        alert_info_text = "#2c2c2c"
        leaf_color = "rgba(185, 28, 28, 0.55)"
        leaf_glow = "rgba(220, 38, 38, 0.5)"

    raw_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&family=Inter:wght@300;400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap');

    /* Header transparente pero con botón de menú/sidebar SIEMPRE visible y accesible en móviles */
    header[data-testid="stHeader"] {{
        background: transparent !important;
        pointer-events: none !important;
    }}
    [data-testid="stToolbar"] {{
        background: transparent !important;
        pointer-events: none !important;
    }}
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"] {{
        visibility: visible !important;
        display: flex !important;
        pointer-events: auto !important;
        z-index: 999999 !important;
    }}
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stSidebarCollapsedControl"] button {{
        background: #dc2626 !important;
        color: #ffffff !important;
        border: 1px solid #b91c1c !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        box-shadow: 0 4px 14px rgba(220, 38, 38, 0.55) !important;
        pointer-events: auto !important;
        cursor: pointer !important;
    }}
    [data-testid="stExpandSidebarButton"] button:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover {{
        background: #ef4444 !important;
        transform: scale(1.08) !important;
    }}
    [data-testid="stExpandSidebarButton"] button * {{
        color: #ffffff !important;
    }}
    [data-testid="stAppDeployButton"] {{
        visibility: hidden !important;
        display: none !important;
    }}
    #MainMenu, [data-testid="stMainMenu"] {{
        visibility: hidden !important;
        display: none !important;
    }}
    footer {{
        visibility: hidden !important;
        display: none !important;
    }}
    [data-testid="stDecoration"] {{
        visibility: hidden !important;
        display: none !important;
    }}
    [data-testid="stStatusWidget"] {{
        visibility: hidden !important;
        display: none !important;
    }}
    .viewerBadge_container__1QSob, .viewerBadge_link__1QSob {{display: none !important;}}
    a[href*="github.com"] {{display: none !important;}}

    /* Fondo principal y tipografía */
    .stApp {{
        background-color: {bg_app} !important;
        background-image: {bg_radial} !important;
        color: {text_primary} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        overflow-x: hidden !important;
    }}

    /* Títulos editoriales estilo Sumi-e */
    h1, h2, h3, .stHeading {{
        font-family: 'Cinzel', 'Newsreader', Georgia, serif !important;
        color: {text_primary} !important;
        letter-spacing: 0.02em !important;
    }}

    /* Barra lateral con textura y sombra */
    [data-testid="stSidebar"] {{
        background-color: {bg_sidebar} !important;
        border-right: 1px solid {border_sidebar} !important;
        box-shadow: 2px 0 15px rgba(0, 0, 0, {'0.4' if is_dark else '0.04'}) !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {text_primary} !important;
    }}

    /* Botones interactivos con acento Vermilion y transición suave */
    .stButton > button, div[data-testid="stLinkButton"] > a {{
        background-color: {btn_bg} !important;
        color: {btn_text} !important;
        border: 1px solid {btn_border} !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    .stButton > button:hover, div[data-testid="stLinkButton"] > a:hover {{
        background-color: #dc2626 !important;
        color: #ffffff !important;
        border-color: #dc2626 !important;
        box-shadow: 0 4px 18px rgba(220, 38, 38, 0.4) !important;
        transform: translateY(-2px);
    }}
    .stButton > button[kind="primary"] {{
        background-color: #dc2626 !important;
        color: #ffffff !important;
        border-color: #b91c1c !important;
        box-shadow: 0 2px 10px rgba(220, 38, 38, 0.3) !important;
    }}

    /* Pestañas de Navegación con resplandor en acento */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        border-bottom: 1px solid {tab_border} !important;
        gap: 6px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {tab_text} !important;
        background-color: transparent !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 8px 18px !important;
        font-weight: 500 !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.2s ease !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {tab_active_text} !important;
        border-bottom: 2px solid #dc2626 !important;
        background: {tab_active_bg} !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.15) !important;
    }}

    /* Tarjetas y Contenedores Desplegables con elevación en hover */
    [data-testid="stExpander"], details {{
        background-color: {card_bg} !important;
        border: 1px solid {card_border} !important;
        border-radius: 8px !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    [data-testid="stExpander"]:hover, details:hover {{
        border-color: {card_border_hover} !important;
        box-shadow: 0 6px 20px rgba(220, 38, 38, 0.18) !important;
        transform: translateY(-1px);
    }}

    /* Campos de Entrada de Texto y Selectores */
    input, select, textarea, [data-baseweb="select"] {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        transition: border-color 0.2s ease !important;
    }}
    input:focus, textarea:focus {{
        border-color: #dc2626 !important;
        box-shadow: 0 0 0 1px #dc2626 !important;
    }}

    /* Burbujas del Chat RAG */
    [data-testid="stChatMessage"]:nth-child(odd) {{
        background-color: {chat_user_bg} !important;
        border: 1px solid {chat_user_border} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stChatMessage"]:nth-child(even) {{
        background-color: {chat_ai_bg} !important;
        border: 1px solid {chat_ai_border} !important;
        border-left: 3px solid #dc2626 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08) !important;
    }}

    /* Cajas de Información y Alertas */
    [data-testid="stAlert"] {{
        background-color: {alert_info_bg} !important;
        border: 1px solid {alert_info_border} !important;
        border-radius: 8px !important;
        color: {alert_info_text} !important;
    }}

    /* =========================================================================
       ANIMACIONES Y EFECTOS DINÁMICOS SUMI-E (0% CPU, 100% GPU ACCELERATED)
       ========================================================================= */

    /* 1. Sol Carmín Pulsante con Resplandor */
    @keyframes sunRadiance {{
        0% {{
            transform: scale(1) translateY(0);
            filter: drop-shadow(0 0 20px rgba(220, 38, 38, 0.45));
        }}
        50% {{
            transform: scale(1.08) translateY(-4px);
            filter: drop-shadow(0 0 45px rgba(239, 68, 68, 0.8));
        }}
        100% {{
            transform: scale(1) translateY(0);
            filter: drop-shadow(0 0 20px rgba(220, 38, 38, 0.45));
        }}
    }}
    .sumie-sun {{
        animation: sunRadiance 6s ease-in-out infinite alternate !important;
        will-change: transform, filter;
    }}

    /* 2. Grullas en Vuelo a través de la Bruma */
    @keyframes craneFlight {{
        0% {{
            transform: translateX(30px) translateY(4px);
            opacity: 0.3;
        }}
        50% {{
            transform: translateX(-40px) translateY(-4px);
            opacity: 0.85;
        }}
        100% {{
            transform: translateX(-110px) translateY(-8px);
            opacity: 0.2;
        }}
    }}
    .crane-flight {{
        animation: craneFlight 16s ease-in-out infinite alternate !important;
        will-change: transform, opacity;
    }}

    /* 3. Sello Hanko Alquímica-33 con Impronta Táctil */
    .hanko-interactive {{
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
    }}
    .hanko-interactive:hover {{
        transform: scale(1.1) rotate(-3deg) !important;
        box-shadow: 0 0 22px rgba(220, 38, 38, 0.8) !important;
    }}
    .hanko-interactive:active {{
        transform: scale(0.95) rotate(0deg) !important;
    }}

    /* 4. Lluvia de Hojas de Arce / Chispas Momiji flotantes */
    @keyframes leafDrift1 {{
        0% {{ transform: translate3d(0, -10px, 0) rotate(0deg); opacity: 0; }}
        15% {{ opacity: 0.75; }}
        85% {{ opacity: 0.75; }}
        100% {{ transform: translate3d(45px, 105vh, 0) rotate(360deg); opacity: 0; }}
    }}
    @keyframes leafDrift2 {{
        0% {{ transform: translate3d(0, -10px, 0) rotate(45deg); opacity: 0; }}
        20% {{ opacity: 0.65; }}
        80% {{ opacity: 0.65; }}
        100% {{ transform: translate3d(-55px, 105vh, 0) rotate(420deg); opacity: 0; }}
    }}
    .momiji-particle {{
        position: fixed;
        top: -15px;
        pointer-events: none;
        z-index: 99999;
        width: 10px;
        height: 14px;
        background: {leaf_color};
        border-radius: 60% 0 60% 60%;
        box-shadow: 0 0 8px {leaf_glow};
        will-change: transform, opacity;
    }}
    .momiji-p1 {{ left: 12%; animation: leafDrift1 14s linear infinite; animation-delay: 0s; }}
    .momiji-p2 {{ left: 28%; animation: leafDrift2 18s linear infinite; animation-delay: 3s; }}
    .momiji-p3 {{ left: 52%; animation: leafDrift1 16s linear infinite; animation-delay: 7s; }}
    .momiji-p4 {{ left: 74%; animation: leafDrift2 15s linear infinite; animation-delay: 2s; }}
    .momiji-p5 {{ left: 88%; animation: leafDrift1 20s linear infinite; animation-delay: 5s; }}
    .momiji-p6 {{ left: 40%; animation: leafDrift2 17s linear infinite; animation-delay: 9s; }}
    </style>

    <!-- Partículas Momiji Flotantes (Lluvia Carmesí) -->
    <div class="momiji-particle momiji-p1"></div>
    <div class="momiji-particle momiji-p2"></div>
    <div class="momiji-particle momiji-p3"></div>
    <div class="momiji-particle momiji-p4"></div>
    <div class="momiji-particle momiji-p5"></div>
    <div class="momiji-particle momiji-p6"></div>
    """
    return textwrap.dedent(raw_css).strip()


def render_portal_header(st_ctx: Any = None, theme_mode: str = "sumie_dark") -> None:
    """
    Renders the Alquímica-33 Sumi-e & Washi Banner Header,
    incorporating the traditional vermilion Hanko seal [錬],
    calligraphy kanji [水墨画 • 錬金術三十三], the animated Rising Sun, and soaring cranes.
    Guaranteed clean HTML mounting without Markdown code-block parsing artifacts.
    """
    ctx = _get_st(st_ctx)
    is_dark = (theme_mode == "sumie_dark")
    bg_banner = "rgba(18, 18, 18, 0.95)" if is_dark else "rgba(255, 255, 255, 0.95)"
    border_banner = "#262626" if is_dark else "#e5dfd5"
    title_color = "#ffffff" if is_dark else "#111111"
    subtitle_color = "#a0a0a0" if is_dark else "#666666"
    sun_glow = "rgba(220, 38, 38, 0.45)" if is_dark else "rgba(220, 38, 38, 0.22)"

    raw_html = f"""
    <div style="position: relative; background: {bg_banner}; border: 1px solid {border_banner}; border-radius: 12px; padding: 1.25rem 1.75rem; margin-bottom: 1.25rem; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, {'0.35' if is_dark else '0.06'});">
        <!-- Red Sun Emblem (Hinomaru con Pulso Radiante Dinámico) -->
        <div class="sumie-sun" style="position: absolute; top: -25px; right: 25px; width: 125px; height: 125px; border-radius: 50%; background: radial-gradient(circle, #ef4444 0%, #dc2626 40%, #991b1b 80%, transparent 100%); opacity: 0.88; box-shadow: 0 0 35px {sun_glow}; pointer-events: none; z-index: 1;"></div>
        <!-- Grullas y Caligrafía Tradicional en la Bruma -->
        <div class="crane-flight" style="position: absolute; top: 16px; right: 135px; font-family: 'Newsreader', serif; font-size: 13px; color: #ef4444; letter-spacing: 6px; pointer-events: none; z-index: 1; text-shadow: 0 0 8px rgba(220, 38, 38, 0.5);">
            鶴 • 墨 • 錬
        </div>
        <!-- Banner Content -->
        <div style="position: relative; z-index: 2; display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;">
            <!-- Square Hanko Seal (Alquimia / 錬) con Impronta Táctil -->
            <div class="hanko-interactive" title="Alquímica-33 • Sello de Transmutación" style="width: 48px; height: 48px; background-color: #dc2626; border: 2px solid #b91c1c; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #ffffff; font-family: serif; font-weight: 900; font-size: 24px; box-shadow: 0 2px 14px rgba(220, 38, 38, 0.55); flex-shrink: 0;">
                錬
            </div>
            <div>
                <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.2rem;">
                    <span style="font-family: 'Cinzel', 'Newsreader', serif; font-size: 1.4rem; font-weight: 700; color: {title_color}; letter-spacing: 0.02em;">
                        Portal Educativo de Química Analítica
                    </span>
                    <span style="font-size: 10px; padding: 2px 8px; background-color: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.6); color: #ef4444; border-radius: 12px; font-family: monospace; font-weight: bold; letter-spacing: 0.05em;">
                        水墨画 • ALQUÍMICA-33
                    </span>
                </div>
                <div style="font-size: 0.82rem; color: {subtitle_color}; font-family: 'Inter', sans-serif;">
                    Ingeniería Química | Universidad Mayor de San Simón (UMSS) | Código: 2004061
                </div>
            </div>
        </div>
    </div>
    """
    clean_html = textwrap.dedent(raw_html).strip()
    if hasattr(ctx, "html"):
        ctx.html(clean_html)
    else:
        ctx.markdown(clean_html, unsafe_allow_html=True)


# ==============================================================================
# 6. Streamlit View Renderers (Guarded by STREAMLIT_AVAILABLE)
# ==============================================================================

def _get_st(st_ctx: Any = None) -> Any:
    """Returns active Streamlit module or passed context."""
    if st_ctx is not None:
        return st_ctx
    if STREAMLIT_AVAILABLE:
        return st
    raise RuntimeError("Streamlit is not available in this environment.")


def render_sidebar_byok(st_ctx: Any = None) -> Dict[str, Any]:
    """
    Renders BYOK sidebar: password text input for Gemini API key, calls validate_api_key,
    visual validation badge (Valid key / Missing key / Invalid key), direct link to
    https://aistudio.google.com/app/apikey for free key creation, model selector (gemini-2.5-flash),
    and clear session button.
    """
    ctx = _get_st(st_ctx)
    from src import gemini_client

    ctx.sidebar.markdown("## ⚛️ Química Analítica")
    ctx.sidebar.caption("Portal Educativo & Tutor RAG | Ing. Química (UMSS)")
    ctx.sidebar.markdown("---")

    # API Key Input
    ctx.sidebar.subheader("🔑 Clave Google AI Studio")
    current_key = ctx.session_state.get("api_key") or ctx.session_state.get("gemini_api_key") or ""
    new_key = ctx.sidebar.text_input(
        "Ingresa tu clave de API gratuita:",
        value=current_key,
        type="password",
        help="Tu clave se almacena exclusivamente en la memoria efímera de tu sesión de navegador.",
    )

    # Real-time Key Validation
    if new_key != ctx.session_state.get("_last_checked_key"):
        ctx.session_state["_last_checked_key"] = new_key
        if new_key and new_key.strip():
            clean_k = new_key.strip()
            is_valid, msg = gemini_client.validate_api_key(clean_k)
            ctx.session_state["api_key"] = clean_k
            ctx.session_state["gemini_api_key"] = clean_k
            ctx.session_state["api_key_valid"] = is_valid
            ctx.session_state["authenticated"] = is_valid
            ctx.session_state["api_key_message"] = msg
        else:
            ctx.session_state["api_key"] = None
            ctx.session_state["gemini_api_key"] = None
            ctx.session_state["api_key_valid"] = False
            ctx.session_state["authenticated"] = False
            ctx.session_state["api_key_message"] = ""

    # Visual Validation Badge
    if ctx.session_state.get("api_key_valid"):
        ctx.sidebar.success(f"🟢 {ctx.session_state.get('api_key_message')}")
    elif ctx.session_state.get("api_key"):
        ctx.sidebar.error(f"🔴 {ctx.session_state.get('api_key_message')}")
    else:
        ctx.sidebar.info("🟡 Modo local / sin conexión activo (sin clave configurada).")

    # Direct Free Key Creation Link
    ctx.sidebar.markdown(
        "👉 [Crear clave gratuita en Google AI Studio](https://aistudio.google.com/app/apikey)"
    )
    with ctx.sidebar.expander("ℹ️ ¿Cómo obtener tu clave gratis?"):
        ctx.sidebar.write(
            "Obtén tu clave de API 100% gratuita en Google AI Studio: "
            "https://aistudio.google.com/app/apikey\n\n"
            "1. Inicia sesión con tu cuenta Google.\n"
            "2. Haz clic en 'Create API key'.\n"
            "3. Pega tu clave en este panel (formato moderno AQ.... o clásico AIzaSy...). Cuota sin costo: 15 RPM / 1,500 RPD."
        )

    ctx.sidebar.markdown("---")
    # Model Selector with Gemini 3.5 Flash Lite & Auto-Reroute
    ctx.sidebar.subheader("⚙️ Configuración del Modelo")
    model_options = [
        "Gemini 3.5 Flash Lite (Mayor cuota gratuita)",
        "gemini-flash-lite-latest (Último Flash Lite)",
        "gemini-flash-latest (Último Flash)",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-pro-latest (Último Pro)",
    ]
    current_selected = ctx.session_state.get("selected_model") or model_options[0]
    selected_idx = model_options.index(current_selected) if current_selected in model_options else 0

    model_choice = ctx.sidebar.selectbox(
        "Modelo Gemini Principal:",
        model_options,
        index=selected_idx,
    )
    ctx.session_state["selected_model"] = model_choice
    ctx.sidebar.caption("🔄 *Auto-Reenrutamiento activo:* Si se agota la cuota (429), conmuta automáticamente a los modelos Flash Lite / Flash / Pro restantes.")



    # Visual Theme Selector (Alquímica-33)
    ctx.sidebar.markdown("---")
    ctx.sidebar.subheader("🎨 Estilo Visual (Alquímica-33)")
    theme_options = [
        "🌑 Sumi-e (Tinta Carbón / Noche)",
        "📜 Washi (Papel de Arroz / Día)",
    ]
    current_theme = ctx.session_state.get("theme_mode", "sumie_dark")
    theme_idx = 0 if current_theme == "sumie_dark" else 1
    selected_theme_label = ctx.sidebar.radio(
        "Modo de Interfaz:",
        theme_options,
        index=theme_idx,
        key="theme_radio_selector",
        help="Alterna entre el tema Sumi-e nocturno (tinta negra carbón) y el tema Washi diurno (papel de arroz marfil).",
    )
    new_theme_mode = "sumie_dark" if "Sumi-e" in selected_theme_label else "washi_light"
    if ctx.session_state.get("theme_mode") != new_theme_mode:
        ctx.session_state["theme_mode"] = new_theme_mode
        if hasattr(ctx, "rerun"):
            ctx.rerun()

    # Clear Session Button
    ctx.sidebar.markdown("---")
    if ctx.sidebar.button("🗑️ Desconectar Clave / Reiniciar Sesión", use_container_width=True):
        clear_session_state()
        ctx.rerun()

    return {
        "api_key": ctx.session_state.get("api_key"),
        "model": model_choice,
        "is_valid": ctx.session_state.get("api_key_valid", False),
        "theme_mode": ctx.session_state.get("theme_mode", "sumie_dark"),
    }


# Alias for sidebar renderer
render_sidebar = render_sidebar_byok


def render_quick_key_widget(st_ctx: Any = None) -> None:
    """
    Renders an accessible mobile-friendly Key Configuration widget on the main view.
    Ensures smartphone users who have collapsed sidebars can easily paste and validate
    their Google AI Studio API key directly from the main view.
    """
    ctx = _get_st(st_ctx)
    from src import gemini_client

    is_valid = ctx.session_state.get("api_key_valid", False)
    current_key = ctx.session_state.get("api_key") or ctx.session_state.get("gemini_api_key") or ""

    if is_valid:
        with ctx.expander("🟢 Clave de API Activa (Google AI Studio) — Toca para cambiar o desconectar", expanded=False):
            ctx.success(f"Conexión activa: {ctx.session_state.get('api_key_message', 'Google AI Studio')}")
            col1, col2 = ctx.columns([3, 1])
            with col1:
                ctx.caption("Tu clave está cargada en la memoria efímera de tu navegador.")
            with col2:
                if ctx.button("🗑️ Desconectar", key="quick_disconnect_key_btn", use_container_width=True):
                    clear_session_state()
                    if hasattr(ctx, "rerun"):
                        ctx.rerun()
    else:
        with ctx.expander("📱🔑 ¿Estás desde el celular? Toca aquí para ingresar tu clave Google AI Studio", expanded=False):
            ctx.markdown(
                "Para consultar el **Tutor Inteligente** o generar exámenes con IA en tiempo real sin costo, "
                "ingresa tu clave gratuita obtenida en [Google AI Studio](https://aistudio.google.com/app/apikey):"
            )
            with ctx.form("mobile_quick_key_form", clear_on_submit=False):
                quick_k = ctx.text_input(
                    "Clave de API de Google (formato AQ.... o AIzaSy...):",
                    value=current_key,
                    type="password",
                    help="Se almacena únicamente en tu navegador para esta sesión.",
                )
                submitted = ctx.form_submit_button("💾 Guardar y Conectar Clave", use_container_width=True)
                if submitted:
                    if quick_k and quick_k.strip():
                        clean_k = quick_k.strip()
                        ok, msg = gemini_client.validate_api_key(clean_k)
                        ctx.session_state["api_key"] = clean_k
                        ctx.session_state["gemini_api_key"] = clean_k
                        ctx.session_state["api_key_valid"] = ok
                        ctx.session_state["authenticated"] = ok
                        ctx.session_state["api_key_message"] = msg
                        if ok:
                            ctx.success(f"🟢 {msg}")
                        else:
                            ctx.error(f"🔴 {msg}")
                        if hasattr(ctx, "rerun"):
                            ctx.rerun()
                    else:
                        ctx.warning("Por favor ingresa una clave de API.")
            ctx.markdown("👉 [Crear clave gratis en Google AI Studio](https://aistudio.google.com/app/apikey)")


def render_library_tab(
    st_ctx: Any = None,
    catalog: Optional[List[Dict[str, Any]]] = None,
    assets_dir: str = "assets/covers",
) -> None:
    """
    Renders 3-column card grid of 11 textbooks, cover preview thumbnails,
    metadata badges, and direct WhatsApp request link buttons (st.link_button).
    """
    ctx = _get_st(st_ctx)
    books = catalog if catalog is not None else get_course_catalog()

    ctx.header("📚 Biblioteca & Catálogo de Libros de Referencia")
    ctx.markdown(
        "Consulta la bibliografía oficial del curso de **Química Analítica**. "
        "Solicita acceso digital o consulta a la coordinación mediante mensaje directo de WhatsApp."
    )

    # Search & Unit Filtering Controls
    c_search, c_filter = ctx.columns([2, 1])
    with c_search:
        search_query = ctx.text_input("🔍 Buscar por título o autor:", "").strip().lower()
    with c_filter:
        unit_filter = ctx.selectbox(
            "🎯 Filtrar por Unidad:",
            ["Todas"] + [f"U{i}" for i in range(1, 10)] + [f"L{i}" for i in range(1, 9)],
        )

    # Filter books
    filtered_books = []
    for b in books:
        title_match = search_query in b["title"].lower() or search_query in b["authors"].lower()
        if not title_match:
            continue
        if unit_filter != "Todas" and unit_filter not in b.get("syllabus_units", []):
            continue
        filtered_books.append(b)

    ctx.markdown(f"*Mostrando {len(filtered_books)} de {len(books)} libros disponibles*")

    if not filtered_books:
        ctx.info("No se encontraron libros que coincidan con los criterios de búsqueda.")
        return

    # 3-Column Card Grid
    cols_per_row = 3
    for i in range(0, len(filtered_books), cols_per_row):
        cols = ctx.columns(cols_per_row)
        for j in range(cols_per_row):
            idx = i + j
            if idx < len(filtered_books):
                b = filtered_books[idx]
                with cols[j]:
                    with ctx.container(border=True):
                        # Cover Thumbnail Preview
                        cover_path = resolve_cover_image_path(b["id"], assets_dir=assets_dir)
                        if cover_path and os.path.isfile(cover_path):
                            ctx.image(cover_path, use_container_width=True)
                        else:
                            ctx.markdown(
                                """
                                <div style="background:#f1f5f9; border:1px dashed #cbd5e1; border-radius:8px;
                                            padding:35px 10px; text-align:center; color:#64748b; margin-bottom:10px;">
                                    <div style="font-size: 32px;">📖</div>
                                    <div style="font-size: 13px; font-weight:600; margin-top:6px;">Portada no disponible</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        ctx.subheader(b["title"])
                        ctx.caption(f"✍️ **Autores:** {b['authors']}")
                        ctx.markdown(f"🏷️ **Edición:** `{b['edition']}` | 🌐 `{b.get('language', 'Español')}`")
                        if "syllabus_units_label" in b:
                            ctx.markdown(f"🎯 **Temario:** `{b['syllabus_units_label']}`")
                        if "description" in b:
                            ctx.write(f"_{b['description']}_")

                        ctx.divider()

                        # Direct WhatsApp Request Button
                        wa_url = b.get("whatsapp_url") or build_whatsapp_request_url(b)
                        ctx.link_button(
                            "📲 Solicitar por WhatsApp",
                            wa_url,
                            use_container_width=True,
                            help="Genera un enlace con mensaje prellenado para solicitar el texto a la cátedra.",
                        )


def render_syllabus_tab(
    st_ctx: Any = None,
    curriculum_path: str = "data/curriculum_spec.json",
) -> None:
    """
    Renders 3 sub-tabs (Theory Units, Lab Units / 13 Practicals, Thematic Axes),
    expandable unit view with learning objectives, topics, mapped books, and
    cross-tab navigation buttons.
    """
    ctx = _get_st(st_ctx)
    from src import syllabus

    theory_units = syllabus.get_theory_units()
    lab_units = syllabus.get_lab_units()
    cross_mappings = syllabus.get_cross_curriculum_mappings()

    ctx.header("📋 Plan Global & Navegador del Temario")
    ctx.markdown(
        "Explora el contenido oficial de **Química Analítica (Teoría y Laboratorio)**. "
        "Consulta objetivos de aprendizaje, temas detallados y bibliografía recomendada para cada unidad."
    )

    tab_th, tab_lb, tab_ax = ctx.tabs([
        f"📖 Unidades de Teoría ({len(theory_units)})",
        f"🧪 Prácticas de Laboratorio ({len(lab_units)} Unidades / 13 Prácticas)",
        "🔗 Ejes Temáticos Integrados",
    ])

    # 1. Theory Units Sub-Tab
    with tab_th:
        for idx, u in enumerate(theory_units):
            u_id = u.get("id", f"U{idx + 1}")
            u_title = u.get("title", f"Unidad {idx + 1}")
            with ctx.expander(f"📘 {u_id}: {u_title}", expanded=(idx == 0)):
                if "description" in u:
                    ctx.markdown(f"**Descripción General:** {u['description']}")

                # Learning Objectives
                objectives = u.get("learning_objectives", [])
                if objectives:
                    ctx.markdown("#### 🎯 Objetivos de Aprendizaje")
                    for obj in objectives:
                        ctx.markdown(f"- {obj}")

                # Topics
                topics = u.get("topics", [])
                if topics:
                    ctx.markdown("#### 📑 Temas Detallados")
                    for t in topics:
                        if isinstance(t, dict):
                            t_title = t.get("title", "")
                            t_code = t.get("topic_code", "")
                            kws = t.get("keywords", [])
                            kw_str = f" _(Conceptos: {', '.join(kws)})_" if kws else ""
                            ctx.markdown(f"- **{t_code} {t_title}**{kw_str}")
                        else:
                            ctx.markdown(f"- {t}")

                # Mapped Textbook Chapters
                mapped_books = u.get("mapped_textbook_chapters", {})
                if mapped_books:
                    ctx.markdown("#### 📚 Capítulos Recomendados")
                    for b_key, ch_list in mapped_books.items():
                        ctx.markdown(f"**{b_key}:**")
                        for ch in ch_list:
                            ctx.markdown(f"  - {ch}")

                ctx.divider()

                # Cross-Tab Navigation Buttons
                b_col1, b_col2 = ctx.columns(2)
                with b_col1:
                    if ctx.button(f"💬 Abrir en Tutor ({u_id})", key=f"nav_tut_{u_id}"):
                        ctx.session_state["current_unit"] = u_id
                        ctx.session_state["tutor_unit"] = u_id
                        ctx.session_state["prefill_prompt"] = (
                            f"Hola Tutor, quiero repasar los conceptos de la {u_id} ({u_title})."
                        )
                        ctx.success(f"Unidad {u_id} seleccionada para el Tutor Inteligente.")
                with b_col2:
                    if ctx.button(f"📝 Practicar en Examen ({u_id})", key=f"nav_exm_{u_id}"):
                        ctx.session_state["current_unit"] = u_id
                        ctx.session_state["exam_unit"] = u_id
                        ctx.session_state["exam_status"] = "idle"
                        ctx.session_state["exam_questions"] = []
                        ctx.session_state["exam_answers"] = {}
                        ctx.session_state["exam_student_answers"] = {}
                        ctx.session_state["exam_submitted"] = False
                        ctx.session_state["exam_results"] = None
                        ctx.session_state["exam_evaluation"] = None
                        ctx.success(f"Unidad {u_id} configurada para el Simulador de Exámenes.")

    # 2. Laboratory Units Sub-Tab
    with tab_lb:
        for idx, lu in enumerate(lab_units):
            l_id = lu.get("id", f"L{idx + 1}")
            l_title = lu.get("title", f"Unidad Lab {idx + 1}")
            practicals = lu.get("practices", lu.get("practicals", []))

            with ctx.expander(f"🧪 {l_id}: {l_title} ({len(practicals)} Prácticas)", expanded=(idx == 0)):
                if "description" in lu:
                    ctx.markdown(f"**Descripción:** {lu['description']}")

                for p in practicals:
                    p_num = p.get("practice_num", p.get("practical_number", 1))
                    p_title = p.get("title", f"Práctica {p_num}")
                    ctx.markdown(f"##### 🥼 Práctica {p_num}: {p_title}")

                    reagents = p.get("reagents", [])
                    if reagents:
                        ctx.markdown(f"🧪 **Reactivos:** {', '.join(reagents)}")

                    techniques = p.get("techniques", [])
                    if techniques:
                        ctx.markdown(f"🔬 **Técnicas:** {', '.join(techniques)}")

    # 3. Thematic Axes Sub-Tab
    with tab_ax:
        ctx.markdown("#### 🔗 Ejes Temáticos Integrados (Teoría ↔ Laboratorio)")
        ctx.markdown(
            "Articulación curricular entre los fundamentos teóricos y las aplicaciones experimentales."
        )
        for axis in cross_mappings:
            axis_name = axis.get("thematic_axis", "Eje Temático")
            with ctx.container(border=True):
                ctx.markdown(f"### 🌐 {axis_name}")
                tu_str = ", ".join(axis.get("theory_units", []))
                lp_str = ", ".join(axis.get("laboratory_practicals", []))
                ctx.markdown(f"📘 **Unidades Teóricas:** `{tu_str}`")
                ctx.markdown(f"🧪 **Prácticas Experimentales:** `{lp_str}`")

                concepts = axis.get("core_concepts", [])
                if concepts:
                    ctx.markdown(f"🔑 **Conceptos Clave:** {', '.join(concepts)}")

                chapters = axis.get("primary_textbook_chapters", [])
                if chapters:
                    ctx.markdown(f"📚 **Capítulos Guía:** {', '.join(chapters)}")


def render_tutor_tab(
    st_ctx: Any = None,
    db_path: str = "data/quimica_analitica.db",
) -> None:
    """
    Renders unit selector, 'Guided Study Mode' button calling suggest_next_topic,
    chat history rendering with KaTeX formula support, chat input, calls get_tutor_response,
    expandable citation drawer (📖 {book_title} (Pág. {page_num})), and offline fallback notice.
    """
    ctx = _get_st(st_ctx)
    from src import rag, syllabus, tutor

    ctx.header("💬 Tutor Inteligente — Química Analítica")
    ctx.caption("Acompañamiento socrático, deducción de fórmulas y resolución de dudas curriculares.")

    api_key = ctx.session_state.get("api_key") or ctx.session_state.get("gemini_api_key") or ""
    is_valid = bool(ctx.session_state.get("api_key_valid"))

    # Offline Fallback Notice
    if not is_valid:
        ctx.info(
            "ℹ️ **Modo Sin Conexión Activo**: No se ha detectado una clave válida de Google AI Studio. "
            "Las consultas se resolverán consultando directamente los libros de texto locales mediante búsqueda "
            "BM25/FTS5 con citas bibliográficas exactas. Para explicaciones generativas socráticas en tiempo real, "
            "ingresa tu clave gratuita en la barra lateral."
        )
    else:
        ctx.success("🟢 **Tutor Gemini Activo**: Conexión establecida. Respuestas socráticas, KaTeX y citas de libros.")

    # Controls: Unit Selector, Guided Study Button, Clear Chat
    theory_units = syllabus.get_theory_units()
    unit_ids = [u["id"] for u in theory_units]
    curr_unit = ctx.session_state.get("current_unit") or ctx.session_state.get("tutor_unit") or "U1"
    curr_idx = unit_ids.index(curr_unit) if curr_unit in unit_ids else 0

    c_unit, c_guided, c_clear = ctx.columns([5, 4, 2])
    with c_unit:
        selected_unit = ctx.selectbox(
            "Unidad Didáctica de Referencia:",
            options=unit_ids,
            index=curr_idx,
            format_func=lambda uid: f"{uid} — {next((u['title'] for u in theory_units if u['id'] == uid), '')}",
            key="tutor_unit_selector",
        )
        ctx.session_state["current_unit"] = selected_unit
        ctx.session_state["tutor_unit"] = selected_unit

    with c_guided:
        ctx.write("")
        ctx.write("")
        if ctx.button("🎯 Modo de Estudio Guiado", use_container_width=True):
            completed = ctx.session_state.get("completed_topics", [])
            rec = tutor.suggest_next_topic(selected_unit, completed)
            next_topic = rec.get("next_topic", "Conceptos Fundamentales")
            rec_status = rec.get("status", "in_progress")

            if rec_status == "completed":
                notice = (
                    f"🎉 ¡Felicidades! Has completado la revisión de todos los temas oficiales de la **{selected_unit}**. "
                    "Te recomendamos pasar a la pestaña **📝 Simulador de Exámenes** para poner a prueba tus conocimientos."
                )
                ctx.session_state["messages"].append({"role": "assistant", "content": notice, "citations": []})
            else:
                ctx.session_state["completed_topics"].append(next_topic)
                inquiry = f"Explícame los fundamentos teóricos, ecuaciones y aplicaciones de: {next_topic}."
                ctx.session_state["messages"].append({"role": "user", "content": inquiry})
                with ctx.spinner("Consultando libros de texto y generando explicación guiada..."):
                    reply = tutor.get_tutor_response(
                        student_message=inquiry,
                        history=ctx.session_state["messages"][:-1],
                        current_unit_id=selected_unit,
                        api_key=api_key,
                    )
                    rag_res = rag.query_rag(query=inquiry, api_key=api_key, syllabus_unit=selected_unit, db_path=db_path)
                    citations = rag_res.get("citations", [])
                    ctx.session_state["messages"].append({
                        "role": "assistant",
                        "content": str(reply),
                        "citations": citations,
                    })
            ctx.rerun()

    with c_clear:
        ctx.write("")
        ctx.write("")
        if ctx.button("🗑️ Limpiar", use_container_width=True):
            ctx.session_state["messages"] = []
            ctx.rerun()

    ctx.divider()

    # Render Chat History
    messages = ctx.session_state.get("messages", [])
    if not messages:
        ctx.chat_message("assistant").markdown(
            f"Hola, soy tu tutor especializado de **Química Analítica**. Actualmente estamos enfocados en "
            f"**{selected_unit}**. ¿Qué concepto, cálculo estequiométrico o técnica de laboratorio deseas consultar hoy?"
        )
    else:
        for msg in messages:
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
            with ctx.chat_message(role):
                ctx.markdown(format_chemical_formula(content))
                citations = msg.get("citations", [])
                if citations and role == "assistant":
                    with ctx.expander(f"📚 Fuentes Bibliográficas Consultadas ({len(citations)})"):
                        for c in citations:
                            b_title = c.get("book_title", "Libro Oficial")
                            author = c.get("author", "")
                            edition = c.get("edition", "")
                            chapter = c.get("chapter", "Capítulo")
                            page_num = c.get("page_num", "")
                            excerpt = c.get("excerpt", "")

                            card_label = f"📖 {b_title} (Pág. {page_num})"
                            ctx.markdown(f"- **{card_label}** — *{chapter}*, {author} ({edition})")
                            if excerpt:
                                ctx.caption(f"> \"{excerpt}\"")

    # Chat Input
    prompt_prefill = ctx.session_state.pop("prefill_prompt", None)
    user_input = ctx.chat_input(prompt_prefill or "Escribe tu duda sobre Química Analítica...")

    if user_input:
        clean_input = user_input.strip()
        if not clean_input:
            ctx.rerun()

        safe_input = html.escape(clean_input)
        ctx.session_state["messages"].append({"role": "user", "content": safe_input})

        with ctx.chat_message("user"):
            ctx.markdown(format_chemical_formula(safe_input))

        with ctx.chat_message("assistant"):
            with ctx.spinner("Consultando bibliografía oficial y generando respuesta..."):
                reply = tutor.get_tutor_response(
                    student_message=clean_input,
                    history=ctx.session_state["messages"][:-1],
                    current_unit_id=selected_unit,
                    api_key=api_key,
                )
                reply_str = str(reply)
                rag_res = rag.query_rag(
                    query=clean_input,
                    api_key=api_key,
                    syllabus_unit=selected_unit,
                    db_path=db_path,
                )
                citations = rag_res.get("citations", [])

                ctx.markdown(format_chemical_formula(reply_str))
                if citations:
                    with ctx.expander(f"📚 Fuentes Bibliográficas Consultadas ({len(citations)})"):
                        for c in citations:
                            b_title = c.get("book_title", "Libro Oficial")
                            author = c.get("author", "")
                            edition = c.get("edition", "")
                            chapter = c.get("chapter", "")
                            page_num = c.get("page_num", "")
                            excerpt = c.get("excerpt", "")

                            card_label = f"📖 {b_title} (Pág. {page_num})"
                            ctx.markdown(f"- **{card_label}** — *{chapter}*, {author} ({edition})")
                            if excerpt:
                                ctx.caption(f"> \"{excerpt}\"")

        ctx.session_state["messages"].append({
            "role": "assistant",
            "content": reply_str,
            "citations": citations,
        })
        ctx.rerun()


def render_exam_tab(st_ctx: Any = None) -> None:
    """
    Renders unit selector, difficulty selector, question count slider (1-10, default 3),
    'Generar Examen' button calling generate_exam_questions, options radio buttons
    formatted with prefixes 'A) ', 'B) ', 'C) ', 'D) ', 'Calificar Examen' button calling
    evaluate_exam_submission, scorecard metric badge (f"Puntaje Obtenido: {score_val}%"),
    pass/fail indicator (passing grade >= 51.0%), detailed explanations and citations,
    and reset/retake button.
    """
    ctx = _get_st(st_ctx)
    from src import exam, syllabus

    ctx.header("📝 Simulador de Exámenes — Práctica y Autoevaluación")
    ctx.caption("Evaluaciones dinámicas objetivas alineadas con los exámenes parciales y de laboratorio.")

    status = ctx.session_state.get("exam_status", "idle")
    api_key = ctx.session_state.get("api_key") or ctx.session_state.get("gemini_api_key") or "AIzaSy_MockExamKey_For_Evaluation_12345"

    theory_units = syllabus.get_theory_units()
    unit_ids = [u["id"] for u in theory_units]
    active_unit = ctx.session_state.get("exam_unit") or ctx.session_state.get("current_unit") or "U3"
    unit_idx = unit_ids.index(active_unit) if active_unit in unit_ids else 0

    # ==========================================================================
    # State 1: Configurator (status == "idle")
    # ==========================================================================
    if status == "idle":
        ctx.subheader("⚙️ Configurar Nueva Evaluación")
        ctx.markdown(
            "Selecciona la unidad didáctica, el nivel de dificultad y la cantidad de preguntas. "
            "Las preguntas se generan dinámicamente según el banco curricular oficial."
        )

        c1, c2, c3, c4 = ctx.columns([4, 3, 3, 3])
        with c1:
            sel_unit = ctx.selectbox(
                "Unidad a Evaluar:",
                unit_ids,
                index=unit_idx,
                format_func=lambda uid: f"{uid} — {next((u['title'] for u in theory_units if u['id'] == uid), '')}",
                key="exam_unit_select",
            )
            ctx.session_state["exam_unit"] = sel_unit

        with c2:
            diff_options = ["fácil", "media", "difícil"]
            curr_diff = ctx.session_state.get("exam_difficulty", "media")
            diff_idx = diff_options.index(curr_diff) if curr_diff in diff_options else 1
            difficulty = ctx.selectbox(
                "Dificultad:",
                diff_options,
                index=diff_idx,
                key="exam_diff_select",
            )
            ctx.session_state["exam_difficulty"] = difficulty

        with c3:
            q_count = ctx.slider(
                "Cantidad de Preguntas:",
                min_value=1,
                max_value=10,
                value=int(ctx.session_state.get("exam_count") or 3),
                step=1,
                key="exam_count_slider",
            )
            ctx.session_state["exam_count"] = q_count

        with c4:
            ctx.write("")
            ctx.write("")
            gen_btn = ctx.button("🚀 Generar Examen", type="primary", use_container_width=True)

        if gen_btn:
            with ctx.spinner(f"Generando preguntas para la unidad {sel_unit}..."):
                questions = exam.generate_exam_questions(
                    unit_id=sel_unit,
                    count=q_count,
                    difficulty=difficulty,
                    api_key=api_key,
                )
                ctx.session_state["exam_questions"] = questions
                ctx.session_state["exam_answers"] = {}
                ctx.session_state["exam_student_answers"] = {}
                ctx.session_state["exam_submitted"] = False
                ctx.session_state["exam_results"] = None
                ctx.session_state["exam_evaluation"] = None
                ctx.session_state["exam_status"] = "in_progress"
            ctx.rerun()

    # ==========================================================================
    # State 2: Active Quiz (status == "in_progress")
    # ==========================================================================
    elif status == "in_progress":
        questions = ctx.session_state.get("exam_questions", [])
        total_q = len(questions)

        ctx.info(
            f"📋 **Evaluación en Curso**: Unidad **{ctx.session_state.get('exam_unit')}** | "
            f"**{total_q}** preguntas | Dificultad: **{str(ctx.session_state.get('exam_difficulty')).capitalize()}**"
        )

        for idx, q in enumerate(questions, 1):
            q_id = q.get("id", idx)
            ctx.markdown(f"### Pregunta {idx} de {total_q}")
            ctx.markdown(f"**{format_chemical_formula(q.get('question', ''))}**")

            options = q.get("options", [])
            curr_sel = ctx.session_state["exam_student_answers"].get(q_id, None)
            sel_idx = options.index(curr_sel) if curr_sel in options else None

            chosen = ctx.radio(
                f"Selecciona tu respuesta para la pregunta {idx}:",
                options=options,
                index=sel_idx,
                key=f"q_radio_{q_id}",
                label_visibility="collapsed",
            )
            if chosen:
                ctx.session_state["exam_student_answers"][q_id] = chosen
                # Extract first character for letter compatibility
                ctx.session_state["exam_answers"][q_id] = chosen[0]

            ctx.divider()

        c_sub, c_can = ctx.columns([3, 1])
        with c_sub:
            if ctx.button("✅ Calificar Examen", type="primary", use_container_width=True):
                # Compile ordered answers
                ordered_answers = []
                for q in questions:
                    qid = q.get("id", 1)
                    ans = ctx.session_state["exam_student_answers"].get(qid, "")
                    ordered_answers.append(ans)

                with ctx.spinner("Calificando respuestas y generando retroalimentación con citas..."):
                    eval_res = exam.evaluate_exam_submission(
                        questions=questions,
                        student_answers=ordered_answers,
                        api_key=api_key,
                    )
                    ctx.session_state["exam_results"] = eval_res
                    ctx.session_state["exam_evaluation"] = eval_res
                    ctx.session_state["exam_submitted"] = True
                    ctx.session_state["exam_status"] = "evaluated"
                ctx.rerun()

        with c_can:
            if ctx.button("🔄 Cancelar", use_container_width=True):
                ctx.session_state["exam_status"] = "idle"
                ctx.session_state["exam_questions"] = []
                ctx.session_state["exam_answers"] = {}
                ctx.session_state["exam_student_answers"] = {}
                ctx.session_state["exam_submitted"] = False
                ctx.session_state["exam_results"] = None
                ctx.session_state["exam_evaluation"] = None
                ctx.rerun()

    # ==========================================================================
    # State 3: Evaluation Scorecard (status == "evaluated")
    # ==========================================================================
    elif status == "evaluated":
        eval_res = ctx.session_state.get("exam_results") or ctx.session_state.get("exam_evaluation") or {}
        score = float(eval_res.get("score", 0.0))
        total_q = eval_res.get("total_questions", 0)
        correct_q = eval_res.get("correct_answers", 0)
        passed = bool(eval_res.get("passed", score >= 51.0))

        ctx.subheader("📊 Resultado de la Evaluación")

        # Scorecard Metrics
        m1, m2, m3 = ctx.columns(3)
        with m1:
            badge_text = f"Puntaje Obtenido: {score}%"
            ctx.metric("Puntaje Obtenido", f"{score}%")
        with m2:
            ctx.metric("Respuestas Correctas", f"{correct_q} / {total_q}")
        with m3:
            ctx.metric("Estado Final", "APROBADO" if passed else "REPROBADO", delta="≥ 51%" if passed else "< 51%")

        # Pass / Fail Announcement
        if score == 100.0:
            ctx.balloons()
            ctx.success("🎉 **¡Puntaje Perfecto (100%)!** Dominas con excelencia los conceptos evaluados en esta unidad.")
        elif passed:
            ctx.success(f"✅ **¡Evaluación Aprobada!** Has obtenido {score}% (nota mínima de aprobación: 51.0%).")
        else:
            ctx.error(
                f"⚠️ **Calificación Insuficiente ({score}%)**. No se alcanzó la nota mínima de aprobación (51.0%). "
                "Te recomendamos repasar los temas señalados a continuación con ayuda del Tutor Inteligente."
            )

        ctx.divider()

        # Detailed Question Breakdown
        ctx.markdown("### 📋 Desglose Detallado por Pregunta")
        feedback_list = eval_res.get("feedback", [])

        for idx, item in enumerate(feedback_list, 1):
            is_corr = item.get("is_correct", False)
            icon = "✅" if is_corr else "❌"
            card_title = f"{icon} Pregunta {idx}: {'Correcta' if is_corr else 'Incorrecta'}"

            with ctx.expander(card_title, expanded=not is_corr):
                ctx.markdown(f"- **Tu respuesta:** `{item.get('student_answer') or 'Sin responder'}`")
                ctx.markdown(f"- **Respuesta correcta:** `{item.get('correct_answer')}`")
                ctx.markdown(f"- **Explicación pedagógica:** {item.get('feedback')}")
                cit = item.get("citation")
                if cit and cit.get("book_title"):
                    ctx.info(
                        f"📖 **Referencia:** {cit.get('book_title')} ({cit.get('edition', '')}) — "
                        f"*{cit.get('chapter', '')}*, Pág. **{cit.get('page_num', '')}**"
                    )

        # Consolidated Citations
        exam_cits = eval_res.get("citations", [])
        if exam_cits:
            with ctx.expander(f"📚 Bibliografía Oficial del Examen ({len(exam_cits)})"):
                for c in exam_cits:
                    ctx.markdown(
                        f"- 📖 **{c.get('book_title')}** ({c.get('edition', '')}) — "
                        f"*{c.get('chapter', '')}*, Pág. **{c.get('page_num', '')}**"
                    )

        # Remediation & Retake Action Buttons
        ctx.write("")
        c_retake, c_remediate = ctx.columns([1, 1])
        with c_retake:
            if ctx.button("🔄 Intentar Otro Examen", type="primary", use_container_width=True):
                ctx.session_state["exam_status"] = "idle"
                ctx.session_state["exam_questions"] = []
                ctx.session_state["exam_answers"] = {}
                ctx.session_state["exam_student_answers"] = {}
                ctx.session_state["exam_submitted"] = False
                ctx.session_state["exam_results"] = None
                ctx.session_state["exam_evaluation"] = None
                ctx.rerun()

        with c_remediate:
            if not passed:
                if ctx.button("💬 Repasar Conceptos Fallidos con el Tutor", use_container_width=True):
                    failed_items = [fb for fb in feedback_list if not fb.get("is_correct")]
                    summary = "; ".join([f"Pregunta {fb.get('question_id')}: {fb.get('feedback')}" for fb in failed_items[:2]])
                    remediation_prompt = (
                        f"Hola Tutor, rendí el examen de la unidad {ctx.session_state.get('exam_unit')} y obtuve {score}%. "
                        f"Necesito reforzar estos conceptos: {summary}"
                    )
                    ctx.session_state["messages"].append({"role": "user", "content": remediation_prompt})
                    ctx.info("Mensaje de refuerzo agregado al Tutor. Dirígete a la pestaña '💬 Tutor Inteligente'.")


def render_simulator_tab(st_ctx=None) -> None:
    """Renders the 2D Interactive Virtual Laboratory Simulator tab."""
    ctx = st_ctx or st
    if not ctx:
        return

    ctx.subheader("🔬 Laboratorio Virtual Interactivo — Química Analítica")
    ctx.markdown(
        """
        Simulador 2D interactivo con instrumental volumétrico analítico, gravimetría,
        espectrofotometría UV-Vis y libreta digital de laboratorio con detección procedural de defectos de técnica.
        Desarrollado para la carrera de Ingeniería Química (UMSS).
        """
    )

    c1, c2 = ctx.columns([3, 1])
    with c1:
        ctx.info(
            "💡 **Modo Embebido**: Puedes interactuar con la mesada de laboratorio directamente aquí abajo, "
            "o abrir la versión completa en una nueva pestaña para trabajar con mayor comodidad."
        )
    with c2:
        ctx.link_button(
            "🚀 Abrir a Pantalla Completa ↗",
            "https://casazola49.github.io/quimica-analitica-lab-sim/",
            use_container_width=True,
        )

    # Render iframe component
    try:
        import streamlit.components.v1 as components
        components.iframe(
            "https://casazola49.github.io/quimica-analitica-lab-sim/",
            height=850,
            scrolling=True,
        )
    except Exception as e:
        ctx.error(f"No se pudo cargar el marco del simulador: {e}")
        ctx.markdown("[Haz clic aquí para abrir el simulador en GitHub Pages](https://casazola49.github.io/quimica-analitica-lab-sim/)")

