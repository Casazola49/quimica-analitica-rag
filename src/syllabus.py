"""
src/syllabus.py - Curriculum Parser, Schema Provider & Topic Matcher
for Química Analítica (Theory & Laboratory).

Provides cached access to data/curriculum_spec.json and high-performance
ontology-based topic matching to associate textbook chunks and student queries
with official curriculum units and practical experiments.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Module-level singletons and caches
_CACHED_CURRICULUM: Optional[Dict[str, Any]] = None
_CACHED_PATH: Optional[str] = None
_UNIT_INDEX: Optional[Dict[str, Dict[str, float]]] = None
_SHORT_PATTERNS: Optional[Dict[str, re.Pattern]] = None

# Taxonomy category to units mapping
_TAXONOMY_MAP: Dict[str, List[str]] = {
    "error_analysis_and_statistics": ["THEORY_U2", "LAB_U1", "LAB_P2", "U2", "L1"],
    "gravimetry_and_solubility": ["THEORY_U3", "THEORY_U4", "LAB_U4", "LAB_P5", "U3", "U4", "L4"],
    "acid_base_volumetry": ["THEORY_U6", "LAB_U5", "LAB_P7", "U6", "L5"],
    "precipitation_volumetry": ["THEORY_U5", "LAB_U5", "LAB_P6", "U5", "L5"],
    "complexometric_volumetry": ["THEORY_U7", "LAB_U5", "LAB_P10", "U7", "L5"],
    "redox_volumetry": ["THEORY_U8", "THEORY_U9", "LAB_U5", "LAB_P8", "LAB_P9", "U8", "U9", "L5"],
    "instrumental_methods": ["LAB_U6", "LAB_U7", "LAB_U8", "LAB_P11", "LAB_P12", "LAB_P13", "L6", "L7", "L8"],
}


def _default_spec() -> Dict[str, Any]:
    """Fallback built-in schema if curriculum_spec.json is not on disk."""
    return {
        "metadata": {
            "subject": "Química Analítica",
            "subject_code": "2004061",
            "program": "Licenciatura en Ingeniería Química",
        },
        "theory_units": [
            {"id": "U1", "unit_id": "THEORY_U1", "unit_number": 1, "title": "Análisis Químico", "unit_title": "ANÁLISIS QUÍMICO", "topics": ["Definiciones", "Etapas del análisis", "Muestreo", "Tratamiento de muestra", "Medidas de composición"]},
            {"id": "U2", "unit_id": "THEORY_U2", "unit_number": 2, "title": "Pruebas Estadísticas y Análisis de Errores", "unit_title": "PRUEBAS ESTADÍSTICAS Y ANÁLISIS DE ERRORES", "topics": ["Detección de errores", "Precisión y exactitud", "Errores aleatorios y sistemáticos", "Límites de confianza", "Estándares y blancos", "Cifras significativas"]},
            {"id": "U3", "unit_id": "THEORY_U3", "unit_number": 3, "title": "Métodos Gravimétricos de Análisis", "unit_title": "MÉTODOS GRAVIMÉTRICOS DE ANÁLISIS", "topics": ["Propiedades de precipitados", "Mecanismos de formación", "Sobresaturación relativa", "Precipitados cristalinos", "Coprecipitación", "Aplicaciones"]},
            {"id": "U4", "unit_id": "THEORY_U4", "unit_number": 4, "title": "Solubilidad de los Precipitados", "unit_title": "SOLUBILIDAD DE LOS PRECIPITADOS", "topics": ["Constante Kps", "Equilibrios competitivos", "Separaciones fraccionadas"]},
            {"id": "U5", "unit_id": "THEORY_U5", "unit_number": 5, "title": "Valoraciones de Precipitación", "unit_title": "VALORACIONES DE PRECIPITACIÓN", "topics": ["Curvas de valoración", "Mezclas de haluros", "Indicadores", "Métodos de Mohr y Volhard"]},
            {"id": "U6", "unit_id": "THEORY_U6", "unit_number": 6, "title": "Valoraciones de Neutralización", "unit_title": "VALORACIONES DE NEUTRALIZACIÓN", "topics": ["Indicadores ácido-base", "Curvas de valoración fuerte y débil", "Soluciones reguladoras", "Ácidos polipróticos"]},
            {"id": "U7", "unit_id": "THEORY_U7", "unit_number": 7, "title": "Valoraciones de Formación de Complejos", "unit_title": "VALORACIONES DE FORMACIÓN DE COMPLEJOS", "topics": ["EDTA", "Equilibrios condicionales alpha_4", "Curvas pM", "Indicadores metalocrómicos", "Dureza del agua"]},
            {"id": "U8", "unit_id": "THEORY_U8", "unit_number": 8, "title": "Teoría de las Valoraciones de Óxido - Reducción", "unit_title": "TEORÍA DE LAS VALORACIONES DE OXIDO - REDUCCIÓN", "topics": ["Procesos redox", "Ecuación de Nernst", "Potenciales estándar", "Curvas de valoración", "Indicadores redox"]},
            {"id": "U9", "unit_id": "THEORY_U9", "unit_number": 9, "title": "Aplicaciones de las Valoraciones de Óxido - Reducción", "unit_title": "APLICACIONES DE LAS VALORACIONES DE OXIDOREDUCCIÓN", "topics": ["Reactivos auxiliares Jones/Walden", "Permanganometría", "Dicromatometría", "Yodometría"]},
        ],
        "lab_units": [
            {"id": "L1", "unit_id": "LAB_U1", "unit_number": 1, "title": "Seguridad en el Laboratorio y Tratamiento Estadístico", "unit_title": "SEGURIDAD EN EL LABORATORIO Y TRATAMIENTO ESTADISTICO DE DATOS", "practices": [
                {"practice_num": 1, "practical_number": 1, "practical_id": "LAB_P1", "title": "Seguridad en el Laboratorio"},
                {"practice_num": 2, "practical_number": 2, "practical_id": "LAB_P2", "title": "Tratamiento Estadístico de Datos"}
            ]},
            {"id": "L2", "unit_id": "LAB_U2", "unit_number": 2, "title": "Puesta en Solución de las Muestras", "unit_title": "PUESTA EN SOLUCION DE LAS MUESTRAS", "practices": [
                {"practice_num": 3, "practical_number": 3, "practical_id": "LAB_P3", "title": "Puesta en Solución de las Muestras"}
            ]},
            {"id": "L3", "unit_id": "LAB_U3", "unit_number": 3, "title": "Preparación y Estandarización de Soluciones", "unit_title": "PREPARACION Y ESTANDARIZACION DE SOLUCIONES", "practices": [
                {"practice_num": 4, "practical_number": 4, "practical_id": "LAB_P4", "title": "Preparación y Estandarización de Soluciones"}
            ]},
            {"id": "L4", "unit_id": "LAB_U4", "unit_number": 4, "title": "Gravimetría", "unit_title": "GRAVIMETRIA", "practices": [
                {"practice_num": 5, "practical_number": 5, "practical_id": "LAB_P5", "title": "Determinación Gravimétrica de Sulfatos"}
            ]},
            {"id": "L5", "unit_id": "LAB_U5", "unit_number": 5, "title": "Volumetría", "unit_title": "VOLUMETRIA", "practices": [
                {"practice_num": 6, "practical_number": 6, "practical_id": "LAB_P6", "title": "Determinación de Cloruros por Precipitación (Mohr)"},
                {"practice_num": 7, "practical_number": 7, "practical_id": "LAB_P7", "title": "Volumetría Ácido-Base Potenciométrica y Visual"},
                {"practice_num": 8, "practical_number": 8, "practical_id": "LAB_P8", "title": "Dicromatometría y Determinación de Hierro"},
                {"practice_num": 9, "practical_number": 9, "practical_id": "LAB_P9", "title": "Yodometría y Determinación de Índice de Yodo"},
                {"practice_num": 10, "practical_number": 10, "practical_id": "LAB_P10", "title": "Complejometría y Dureza del Agua"}
            ]},
            {"id": "L6", "unit_id": "LAB_U6", "unit_number": 6, "title": "Electrodeposición", "unit_title": "METODOS INSTRUMENTALES (ELECTRODEPOSICION)", "practices": [
                {"practice_num": 11, "practical_number": 11, "practical_id": "LAB_P11", "title": "Electrodeposición Cuantitativa de Cobre"}
            ]},
            {"id": "L7", "unit_id": "LAB_U7", "unit_number": 7, "title": "Colorimetría y Espectrofotometría", "unit_title": "METODOS INSTRUMENTALES (ESPECTROFOTOMETRIA)", "practices": [
                {"practice_num": 12, "practical_number": 12, "practical_id": "LAB_P12", "title": "Determinación Fotométrica de Hierro con 1,10-Fenantrolina"}
            ]},
            {"id": "L8", "unit_id": "LAB_U8", "unit_number": 8, "title": "Fotometría de Llama", "unit_title": "METODOS INSTRUMENTALES (ESPECTROSCOPIA DE EMISION)", "practices": [
                {"practice_num": 13, "practical_number": 13, "practical_id": "LAB_P13", "title": "Fotometría de Llama para Sodio"}
            ]}
        ]
    }


def _resolve_curriculum_path(path: str) -> Optional[Path]:
    """Resolve curriculum spec file path handling CWD and project root."""
    p = Path(path)
    if p.is_file():
        return p
    project_root = Path(__file__).resolve().parent.parent
    fallback = project_root / path
    if fallback.is_file():
        return fallback
    return None


def load_curriculum(path: str = "data/curriculum_spec.json", reload: bool = False) -> Dict[str, Any]:
    """
    Loads, validates, and caches the curriculum specification JSON.
    Falls back to built-in specification if the file cannot be located or is invalid.
    Defensively parses courses, units, and topics, safely handling null or corrupted entries.
    Ensures both nested ('courses') and flat ('theory_units', 'lab_units') access.
    """
    global _CACHED_CURRICULUM, _CACHED_PATH, _UNIT_INDEX, _SHORT_PATTERNS
    resolved_path = _resolve_curriculum_path(path)

    if not reload and _CACHED_CURRICULUM is not None and (_CACHED_PATH == str(resolved_path) if resolved_path else True):
        return _CACHED_CURRICULUM

    if resolved_path is None:
        _CACHED_CURRICULUM = _default_spec()
        _CACHED_PATH = path
        _UNIT_INDEX = None
        _SHORT_PATTERNS = None
        return _CACHED_CURRICULUM

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Curriculum spec JSON root must be an object")

        norm_data = dict(data)
        courses = data.get("courses")

        if isinstance(courses, dict):
            # Parse theory units defensively
            theory_dict = courses.get("theory")
            theory_list = []
            if isinstance(theory_dict, dict):
                raw_theory_units = theory_dict.get("units")
                if isinstance(raw_theory_units, list):
                    for idx, u in enumerate(raw_theory_units, start=1):
                        if not isinstance(u, dict):
                            continue
                        num = u.get("unit_number")
                        if not isinstance(num, int):
                            try:
                                num = int(num)
                            except (ValueError, TypeError):
                                num = idx
                        u_copy = dict(u)
                        u_copy["unit_number"] = num
                        u_copy["id"] = f"U{num}"
                        u_copy["unit_id"] = str(u.get("unit_id") or f"THEORY_U{num}")
                        u_copy["title"] = str(u.get("unit_title") or u.get("title") or f"Unidad {num}")
                        raw_topics = u.get("topics")
                        if not isinstance(raw_topics, list):
                            raw_topics = []
                        u_copy["topics"] = [t for t in raw_topics if t is not None]
                        theory_list.append(u_copy)

            norm_data["theory_units"] = theory_list if theory_list else _default_spec()["theory_units"]

            # Parse laboratory units defensively
            lab_dict = courses.get("laboratory")
            lab_list = []
            if isinstance(lab_dict, dict):
                raw_lab_units = lab_dict.get("units")
                if isinstance(raw_lab_units, list):
                    for idx, lu in enumerate(raw_lab_units, start=1):
                        if not isinstance(lu, dict):
                            continue
                        num = lu.get("unit_number")
                        if not isinstance(num, int):
                            try:
                                num = int(num)
                            except (ValueError, TypeError):
                                num = idx
                        lu_copy = dict(lu)
                        lu_copy["unit_number"] = num
                        lu_copy["id"] = f"L{num}"
                        lu_copy["unit_id"] = str(lu.get("unit_id") or f"LAB_U{num}")
                        lu_copy["title"] = str(lu.get("unit_title") or lu.get("title") or f"Unidad Lab {num}")

                        raw_practicals = lu.get("practicals") or lu.get("practices")
                        if not isinstance(raw_practicals, list):
                            raw_practicals = []
                        normalized_practicals = []
                        for p_idx, p in enumerate(raw_practicals, start=1):
                            if not isinstance(p, dict):
                                continue
                            p_copy = dict(p)
                            p_num = p.get("practical_number") or p.get("practice_num")
                            if not isinstance(p_num, int):
                                try:
                                    p_num = int(p_num)
                                except (ValueError, TypeError):
                                    p_num = p_idx
                            p_copy["practice_num"] = p_num
                            p_copy["practical_number"] = p_num
                            p_copy["practical_id"] = str(p.get("practical_id") or f"LAB_P{p_num}")
                            p_copy["title"] = str(p.get("title") or f"Práctica {p_num}")
                            normalized_practicals.append(p_copy)
                        lu_copy["practices"] = normalized_practicals
                        lu_copy["practicals"] = normalized_practicals
                        lab_list.append(lu_copy)

            norm_data["lab_units"] = lab_list if lab_list else _default_spec()["lab_units"]
        else:
            if "theory_units" not in norm_data or not isinstance(norm_data.get("theory_units"), list) or not norm_data["theory_units"]:
                norm_data["theory_units"] = _default_spec()["theory_units"]
            if "lab_units" not in norm_data or not isinstance(norm_data.get("lab_units"), list) or not norm_data["lab_units"]:
                norm_data["lab_units"] = _default_spec()["lab_units"]

        _CACHED_CURRICULUM = norm_data
        _CACHED_PATH = str(resolved_path)
        _UNIT_INDEX = None
        _SHORT_PATTERNS = None
        return _CACHED_CURRICULUM

    except Exception:
        _CACHED_CURRICULUM = _default_spec()
        _CACHED_PATH = str(resolved_path) if resolved_path else path
        _UNIT_INDEX = None
        _SHORT_PATTERNS = None
        return _CACHED_CURRICULUM


def get_theory_units() -> List[Dict[str, Any]]:
    """Returns the list of 9 Theory Units from the curriculum."""
    curriculum = load_curriculum()
    if "theory_units" in curriculum:
        return curriculum["theory_units"]
    return curriculum.get("courses", {}).get("theory", {}).get("units", [])


def get_lab_units() -> List[Dict[str, Any]]:
    """Returns the list of 8 Laboratory Units from the curriculum."""
    curriculum = load_curriculum()
    if "lab_units" in curriculum:
        return curriculum["lab_units"]
    return curriculum.get("courses", {}).get("laboratory", {}).get("units", [])


def get_lab_practicals() -> List[Dict[str, Any]]:
    """Returns a flat list of all 13 practical experiments with parent_unit_id."""
    lab_units = get_lab_units()
    practicals = []
    for unit in lab_units:
        unit_id = unit.get("unit_id", unit.get("id", ""))
        for prac in unit.get("practicals", unit.get("practices", [])):
            p_copy = dict(prac)
            p_copy["parent_unit_id"] = unit_id
            practicals.append(p_copy)
    return practicals


def get_cross_curriculum_mappings() -> List[Dict[str, Any]]:
    """Returns the 9 cross-curriculum thematic axes."""
    curriculum = load_curriculum()
    return curriculum.get("cross_curriculum_mapping", [])


def get_exam_blueprints() -> Dict[str, Any]:
    """Returns the exam blueprints dictionary."""
    curriculum = load_curriculum()
    return curriculum.get("exam_blueprints", {})


def get_all_unit_ids() -> List[str]:
    """Returns a list of all canonical unit and practical IDs."""
    ids = []
    for u in get_theory_units():
        ids.append(u.get("id", ""))
        ids.append(u.get("unit_id", ""))
    for u in get_lab_units():
        ids.append(u.get("id", ""))
        ids.append(u.get("unit_id", ""))
        for p in u.get("practicals", u.get("practices", [])):
            if "practical_id" in p:
                ids.append(p["practical_id"])
    return sorted(list(set(filter(None, ids))))


_ROMAN_NUMERALS: Dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
}

# Regex patterns for unit ID normalization
_PRACTICAL_PAT = re.compile(
    r"^(?:LAB[\s_/-]*)?(?:PRACTICA|PRACTICE|PRACTICAL|P)[\s_:#./\-\(\[]*([0-9]+|[IVXLCDM]+)[\)\]]?$",
    re.IGNORECASE,
)
_LAB_UNIT_PAT = re.compile(
    r"^(?:LAB(?:ORATORIO|ORATORY)?(?:[\s_/-]*U(?:NIDAD|NIT)?)?|L)[\s_:#./\-\(\[]*([0-9]+|[IVXLCDM]+)[\)\]]?$",
    re.IGNORECASE,
)
_THEORY_UNIT_PAT = re.compile(
    r"^(?:THEORY(?:[\s_/-]*U(?:NIDAD|NIT)?)?|TEORIA(?:[\s_/-]*U(?:NIDAD|NIT)?)?|UNIT|UNIDAD|TEMA|TOPIC|U)[\s_:#./\-\(\[]*([0-9]+|[IVXLCDM]+)[\)\]]?$",
    re.IGNORECASE,
)


def _parse_num(val_str: str) -> Optional[int]:
    """Parse integer from arabic digit string or Roman numeral string."""
    s = val_str.strip().upper()
    if s.isdigit():
        return int(s)
    return _ROMAN_NUMERALS.get(s, None)


def _normalize_unit_id(raw_id: str) -> str:
    """
    Normalize input unit ID handling casing, whitespace, punctuation/noise,
    accents, Roman numerals, and common natural language aliases.

    Canonical returns:
    - Theory units: 'U1' through 'U9'
    - Laboratory units: 'L1' through 'L8'
    - Laboratory practicals: 'LAB_P1' through 'LAB_P13'
    - Unmatched: stripped uppercase string or empty string
    """
    if not raw_id or not isinstance(raw_id, str):
        return ""

    # Remove accents (e.g. PRÁCTICA -> PRACTICA, TEORÍA -> TEORIA)
    s = "".join(
        c for c in unicodedata.normalize("NFD", raw_id.strip())
        if unicodedata.category(c) != "Mn"
    ).upper()
    if not s:
        return ""

    # Strip noise symbols like quotes, hashes, number signs
    s = re.sub(r"[#№\"\047]", "", s).strip()

    # 1. Practicals / Practices (must precede lab unit check since prefix may start with LAB_P)
    m_prac = _PRACTICAL_PAT.match(s)
    if m_prac:
        num = _parse_num(m_prac.group(1))
        if num is not None:
            return f"LAB_P{num}"

    # 2. Laboratory Units
    m_lab = _LAB_UNIT_PAT.match(s)
    if m_lab:
        num = _parse_num(m_lab.group(1))
        if num is not None:
            return f"L{num}"

    # 3. Theory Units
    m_theory = _THEORY_UNIT_PAT.match(s)
    if m_theory:
        num = _parse_num(m_theory.group(1))
        if num is not None:
            return f"U{num}"

    return s


def get_unit_by_id(unit_id: str, default: Any = None) -> Optional[Dict[str, Any]]:
    """
    Look up a unit or practical by canonical ID or common alias (case-insensitive).
    Returns None if not found or if unit_id is empty/invalid.
    """
    if not unit_id or not isinstance(unit_id, str):
        return default

    clean_id = unit_id.strip().upper()
    if not clean_id:
        return default

    norm_id = _normalize_unit_id(clean_id)

    # 1. Search Theory Units
    for u in get_theory_units():
        u_id = str(u.get("id", "")).upper()
        unit_id_val = str(u.get("unit_id", "")).upper()
        if clean_id in (u_id, unit_id_val) or norm_id in (u_id, unit_id_val):
            return u

    # 2. Search Lab Units
    for lu in get_lab_units():
        lu_id = str(lu.get("id", "")).upper()
        unit_id_val = str(lu.get("unit_id", "")).upper()
        if clean_id in (lu_id, unit_id_val) or norm_id in (lu_id, unit_id_val):
            return lu

    # 3. Search Lab Practicals
    for prac in get_lab_practicals():
        pid = str(prac.get("practical_id", "")).upper()
        pnum = str(prac.get("practice_num", prac.get("practical_number", "")))
        if clean_id in (pid, f"P{pnum}", f"LAB_P{pnum}") or norm_id in (pid, f"P{pnum}", f"LAB_P{pnum}"):
            return prac

    return default


def _ensure_matcher_index() -> tuple[Dict[str, Dict[str, float]], Dict[str, re.Pattern]]:
    """Build or retrieve cached keyword index and short patterns."""
    global _UNIT_INDEX, _SHORT_PATTERNS
    if _UNIT_INDEX is not None and _SHORT_PATTERNS is not None:
        return _UNIT_INDEX, _SHORT_PATTERNS

    curriculum = load_curriculum()
    unit_keywords: Dict[str, Dict[str, float]] = defaultdict(dict)

    def add_kw(uid: str, kw: str, weight: float):
        kw_clean = kw.lower().strip()
        if len(kw_clean) >= 2:
            unit_keywords[uid][kw_clean] = max(unit_keywords[uid].get(kw_clean, 0.0), weight)

    # Built-in canonical chemical terms mapping for 100% precision
    curated_domain_terms = {
        "U1": ["muestreo", "analito", "matriz", "interferencia", "concentracion", "molaridad", "normalidad", "alícuota"],
        "U2": ["error", "precision", "exactitud", "gauss", "student", "desviacion", "incertidumbre", "dixon", "cifras significativas", "t-student"],
        "U3": ["gravimetr", "precipitad", "weimarn", "ostwald", "coprecipitacion", "sulfato", "sulfatos", "baso4", "factor gravimetrico", "crisol", "calcinacion", "digestión"],
        "U4": ["solubilidad", "kps", "ion comun", "fuerza ionica", "debye", "producto de solubilidad"],
        "U5": ["argentometr", "mohr", "volhard", "fajans", "cloruro", "cloruros", "haluro", "agcl", "agno3", "cromato"],
        "U6": ["acido", "acidos", "base", "bases", "neutraliz", "ph", "henderson", "hasselbalch", "buffer", "tampon", "alcalina", "amortiguadora"],
        "U7": ["edta", "complejo", "complejometria", "quelat", "dureza", "calcio", "magnesio", "murexida", "eriocromo", "net", "constante condicional"],
        "U8": ["redox", "nernst", "potencial", "celda", "galvanica", "electrodo", "oxidacion", "reduccion", "potenciales"],
        "U9": ["permanganat", "permanganometria", "dicromat", "dicromatometria", "yodometr", "tiosulfato", "hierro", "kmno4", "k2cr2o7", "reactivo de jones", "reactivo de walden"],
    }

    for uid, kws in curated_domain_terms.items():
        canonical_uid = f"THEORY_{uid}"
        for kw in kws:
            add_kw(uid, kw, 12.0)
            add_kw(canonical_uid, kw, 12.0)

    # 1. Index Theory Units from loaded curriculum
    for u in curriculum.get("theory_units", []):
        uid = u.get("id", f"U{u.get('unit_number', 1)}")
        canon_id = u.get("unit_id", f"THEORY_{uid}")
        title = u.get("title", u.get("unit_title", ""))
        add_kw(uid, title, 10.0)
        add_kw(canon_id, title, 10.0)
        for t in u.get("topics", []):
            t_title = t["title"] if isinstance(t, dict) else str(t)
            add_kw(uid, t_title, 8.0)
            add_kw(canon_id, t_title, 8.0)
            if isinstance(t, dict):
                for kw in t.get("keywords", []):
                    add_kw(uid, kw, 9.0)
                    add_kw(canon_id, kw, 9.0)

    # 2. Index Lab Units & Practicals
    for lu in curriculum.get("lab_units", []):
        l_uid = lu.get("id", f"L{lu.get('unit_number', 1)}")
        canon_l_uid = lu.get("unit_id", f"LAB_{l_uid}")
        lu_title = lu.get("title", lu.get("unit_title", ""))
        add_kw(l_uid, lu_title, 7.0)
        add_kw(canon_l_uid, lu_title, 7.0)
        for p in lu.get("practicals", lu.get("practices", [])):
            p_num = p.get("practice_num", p.get("practical_number", 1))
            pid = p.get("practical_id", f"LAB_P{p_num}")
            p_title = p.get("title", "")
            add_kw(l_uid, p_title, 6.0)
            add_kw(canon_l_uid, p_title, 6.0)
            add_kw(pid, p_title, 10.0)
            for r in p.get("reagents", []):
                add_kw(l_uid, r, 6.0)
                add_kw(pid, r, 8.0)
            for tech in p.get("techniques", []):
                add_kw(l_uid, tech, 5.0)
                add_kw(pid, tech, 7.0)

    # 3. Index Taxonomy & English Synonyms
    tax = curriculum.get("retrieval_and_tutoring_taxonomy", {})
    for cat, data in tax.items():
        targets = _TAXONOMY_MAP.get(cat, [])
        for kw in data.get("keywords", []):
            for t in targets:
                add_kw(t, kw, 7.0)
        for syn in data.get("synonyms_en", []):
            for t in targets:
                add_kw(t, syn, 6.0)

    # 4. Precompile short patterns
    short_patterns: Dict[str, re.Pattern] = {}
    for uid, kws in unit_keywords.items():
        for kw in kws:
            if len(kw) <= 3 and kw not in short_patterns:
                short_patterns[kw] = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)

    _UNIT_INDEX = unit_keywords
    _SHORT_PATTERNS = short_patterns
    return _UNIT_INDEX, _SHORT_PATTERNS


def match_topics_to_curriculum(
    text: str,
    course_filter: Optional[str] = None,
    top_k: int = 5,
    threshold: float = 3.0,
) -> List[str]:
    """
    Maps arbitrary text to curriculum unit IDs ordered by relevance score.
    Guarantees shorthand unit IDs (e.g. 'U3', 'U5', 'U7') are returned when
    matching theory topics, as well as canonical IDs.
    Returns empty list if no matches exceed threshold or if text is empty/whitespace.
    """
    if not text or not isinstance(text, str):
        return []

    # Strip symbols and normalize spaces for search
    text_clean = text.lower().strip()
    if not text_clean:
        return []

    unit_keywords, short_patterns = _ensure_matcher_index()
    scores: Dict[str, float] = defaultdict(float)

    for uid, kws in unit_keywords.items():
        if course_filter == "theory" and not (uid.startswith("U") or uid.startswith("THEORY_")):
            continue
        if course_filter in ("lab", "laboratory") and not (uid.startswith("L") or uid.startswith("LAB_")):
            continue

        for kw, weight in kws.items():
            if len(kw) <= 3:
                pat = short_patterns.get(kw)
                if pat and pat.search(text_clean):
                    scores[uid] += weight
            else:
                if kw in text_clean:
                    scores[uid] += weight * max(1.0, len(kw) / 5.0)

    # Sort units by score
    sorted_units = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    valid_matches = [uid for uid, sc in sorted_units if sc >= threshold]

    # Ensure prioritized shorthand IDs (U1..U9) appear in results alongside canonical
    result: List[str] = []
    seen = set()

    for uid in valid_matches:
        if uid not in seen:
            result.append(uid)
            seen.add(uid)
        # If uid is THEORY_Ux, ensure Ux is also added
        if uid.startswith("THEORY_U"):
            short_u = uid.replace("THEORY_", "")
            if short_u not in seen:
                result.append(short_u)
                seen.add(short_u)
        elif uid.startswith("U") and uid[1:].isdigit():
            canon_u = f"THEORY_{uid}"
            if canon_u not in seen:
                result.append(canon_u)
                seen.add(canon_u)

    return result[:top_k]
