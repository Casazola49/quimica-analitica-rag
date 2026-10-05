"""
src/unit_inference.py - Guess which syllabus unit a student question belongs to.

The retriever reaches 100% first-position accuracy when it knows the unit and
65% when it does not, so the unit selector is the highest-leverage control in
the portal. Students rarely set it, and the previous default silently forced
every question into U1, which is worse than no filter at all: a redox question
was searched in "Análisis químico".

This module infers the unit from the question's own vocabulary. It is a
deliberately small, inspectable keyword map rather than a model call: the
inference is shown to the student and must be correctable, so it has to be
explainable and free.
"""

from __future__ import annotations

import re
from typing import Optional

# Terms that identify a unit, keyed by unit id. Ordered from most specific to
# most generic so a tie prefers the specific reading: "permanganato" is an
# application (U9) even though it is also a redox reagent (U8).
UNIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "U9": (
        "permanganato", "dicromato", "yodato", "yoduro", "iodometria", "iodometría",
        "hierro", "ce4+", "permanganometria", "permanganometría", "difenilamina",
        "oxidante", "reductor", "valoracion redox", "aplicaciones de las valoraciones",
    ),
    "U8": (
        "nernst", "potencial", "electrodo", "celda", "anodo", "ánodo", "catodo", "cátodo",
        "semirreaccion", "semirreacción", "oxido-reduccion", "oxidorreducción", "oxido-reducción",
        "redox", "potencial estandar", "fuerza impulsora", "equilibrio redox",
    ),
    "U7": (
        "edta", "complejo", "complejos", "constante de formacion", "complexometria", "complexometría",
        "dcta", "quelato", "quelacion", "titulacion con edta",
    ),
    "U6": (
        "neutralizacion", "neutralización", "indicador", "fenolftaleina", "fenolftaleína",
        "metil naranja", "curva de titulacion", "curva de titulación", "acido fuerte", "ácido fuerte",
        "base fuerte", "tampón", "tapon", "henderson", "ph del punto equivalente",
        "acido base", "ácido base", "equilibrio acido",
    ),
    "U5": (
        "argentometria", "argentometría", "mohr", "volhard", "fajans", "indicador de adsorcion",
        "cromato de potasio", "nitrato de plata", "cloruro", "yoduro de plata", "determinacion de cloruros",
    ),
    "U4": (
        "producto de solubilidad", "kps", "solubilidad", "ion comun", "ión común",
        "precipitacion selectiva", "precipitación selectiva", "curva de solubilidad", "log kps",
    ),
    "U3": (
        "gravimetria", "gravimetría", "agente precipitante", "precipitado gravimetrico",
        "precipitado gravimétrico", "crisol", "filtro de gooch", "peso constante", "ceniza",
        "secado y calcinacion", "calcinacion",
    ),
    "U2": (
        "error", "errores", "desviacion", "desviación", "precision", "precisión", "exactitud",
        "media aritmetica", "desviacion estandar", "desviación estándar", "intervalo de confianza",
        "propagacion de error", "propagación de error", "cifras significativas", "t de student",
        "rechazo de hipotesis", "prueba t", "rango", "semidesviacion",
    ),
    "U1": (
        "cifras significativas", "analito", "análisis química", "analisis quimico", "muestra",
        "pureza", "reactivo", "disolucion", "disolución", "concentracion", "concentración",
        "estequiometria", "estequiometría", "equilibrio quimico",
    ),
}

# Units whose questions are about laboratory technique rather than theory.
LAB_KEYWORDS: dict[str, tuple[str, ...]] = {
    "LAB_P1": ("laboratorio", "practica de laboratorio", "práctica de laboratorio", "ensayo", "pipeta", "balanza analitica"),
    "L6": ("espectrofotometria", "espectrofotometría", "uv-vis", "absorbancia", "ley de beer", "barrido espectral"),
    "L5": ("cromatografia", "cromatografía", "crom", "fase movil", "fase móvil", "tiempo de retencion"),
    "L7": ("potenciometria", "potenciometría", "electrodo de referencia", "nernst", "titulacion redox"),
}

# Lab keys are matched after theory keys, and never override a confident theory hit.
ALL_KEYWORDS: dict[str, tuple[str, ...]] = {**UNIT_KEYWORDS, **LAB_KEYWORDS}

_ACCENTED = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def _normalize(text: str) -> str:
    """Lowercases and strips accents so 'potenciometria' matches 'potenciometría'."""
    return str(text or "").lower().translate(_ACCENTED)


def infer_unit(
    query: str,
    default: Optional[str] = None,
) -> tuple[Optional[str], float]:
    """
    Infers the syllabus unit a question belongs to.

    Counts how many distinct keywords of each unit appear in the question and
    returns the strongest. Ties and zero matches return ``default`` with a
    confidence of 0.0, so the caller can fall back rather than guess.

    Args:
        query: The student's question, in their own words.
        default: Unit to return when nothing matches.

    Returns:
        A ``(unit, confidence)`` pair. Confidence is the winning unit's score
        divided by the total score, so 0.0 means "no signal" and 1.0 means every
        matched term pointed at the same unit.
    """
    text = _normalize(query)
    if not text.strip():
        return default, 0.0

    scores: dict[str, float] = {}
    for unit, keywords in ALL_KEYWORDS.items():
        hits = 0
        for word in keywords:
            if _normalize(word) in text:
                hits += 1.0
        if hits:
            # Lab evidence is weaker than theory evidence for the same score.
            scores[unit] = hits * (0.6 if unit.startswith("L") or unit.startswith("LAB") else 1.0)

    if not scores:
        return default, 0.0

    total = sum(scores.values())
    best = max(scores, key=lambda u: (scores[u], -list(ALL_KEYWORDS).index(u)))
    return best, round(scores[best] / total, 3) if total else 0.0


def explain_unit(unit: Optional[str]) -> str:
    """Returns a short human label for a unit id, for the inference notice."""
    labels = {
        "U1": "Análisis químico",
        "U2": "Pruebas estadísticas y análisis de errores",
        "U3": "Métodos gravimétricos",
        "U4": "Solubilidad de los precipitados",
        "U5": "Valoraciones de precipitación",
        "U6": "Valoraciones de neutralización",
        "U7": "Valoraciones de formación de complejos",
        "U8": "Teoría de las valoraciones oxido-reducción",
        "U9": "Aplicaciones de las valoraciones oxido-reducción",
        "LAB_P1": "Laboratorio de química analítica",
        "L5": "Laboratorio de cromatografía",
        "L6": "Laboratorio de espectrofotometría",
        "L7": "Laboratorio de potenciometría",
    }
    if not unit:
        return "todo el temario"
    return labels.get(unit, unit)
