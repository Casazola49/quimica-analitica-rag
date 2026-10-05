#!/usr/bin/env python3
"""
benchmark_retrieval.py - Measure whether the RAG retrieves the right material.

A tutoring portal is only as good as what it reads before answering. This
benchmark asks real course questions, each tagged with the syllabus unit that
should answer it, and reports how often retrieval lands on that unit.

It calls ``src.db.search_chunks`` -- the exact function ``query_rag`` uses -- so
the number reflects production behaviour, not a proxy.

Run it:

    .venv/bin/python scripts/benchmark_retrieval.py
    .venv/bin/python scripts/benchmark_retrieval.py --k 8 --verbose

The tagged questions live in BENCHMARK below. Adding a question is the cheapest
way to catch a retrieval regression before a student hits it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import search_chunks  # noqa: E402

# Syllabus units, from data/curriculum_spec.json.
UNIT_TITLES = {
    "U1": "Análisis químico",
    "U2": "Pruebas estadísticas y análisis de errores",
    "U3": "Métodos gravimétricos de análisis",
    "U4": "Solubilidad de los precipitados",
    "U5": "Valoraciones de precipitación",
    "U6": "Valoraciones de neutralización",
    "U7": "Valoraciones de formación de complejos",
    "U8": "Teoría de las valoraciones oxido-reducción",
    "U9": "Aplicaciones de las valoraciones oxido-reducción",
}

# (question, expected unit). Kept in the students' own words, not textbook
# headings: a benchmark made of keywords would flatter a lexical retriever.
BENCHMARK: list[tuple[str, str]] = [
    ("¿Qué error experimental se.committea al medir y cómo se cuantifica?", "U2"),
    ("¿Cuál es la diferencia entre error absoluto y error relativo?", "U2"),
    ("¿Qué es la desviación estándar y qué mide?", "U2"),
    ("¿Cómo se calcula el intervalo de confianza de una media?", "U2"),
    ("¿Qué es un factor de recoveries y cómo afecta al resultado?", "U1"),
    ("¿Cuántas cifras significativas tiene un resultado y cómo se redondea?", "U1"),
    ("¿Cómo se realiza una gravimetría por precipitación y por qué se incuba la mezcla?", "U3"),
    ("¿Qué es un agente precipitante y qué condiciones debe cumplir?", "U3"),
    ("¿Por qué se lava y se incina el precipitado antes de pesarlo?", "U3"),
    ("¿Cómo se calcula el producto de solubilidad Kps de una sal?", "U4"),
    ("¿Qué efecto tiene el pH sobre la solubilidad de un hidróxido?", "U4"),
    ("¿Cómo se determina el punto de equivalencia en una precipitación?", "U5"),
    ("¿Qué es la argentometría y para qué se usa el cromato de potasio?", "U5"),
    ("¿Cuál es la curva de titulación de un ácido fuerte con base fuerte?", "U6"),
    ("¿Cómo se elige el indicador adecuado para una valoración ácido-base?", "U6"),
    ("¿Qué es la constante de formación de complejos y cómo afecta a la titulación?", "U7"),
    ("¿Cómo se titula el calcio y el magnesio con EDTA y a qué pH?", "U7"),
    ("¿Qué dice la ecuación de Nernst sobre el potencial de un electrodo?", "U8"),
    ("¿Cómo se calcula el potencial en una celda redox?", "U8"),
    ("¿Cómo se determina el hierro(II) con permanganato de potasio?", "U9"),
]


def unit_matches(chunks: list[dict], expected: str) -> bool:
    """True when at least one retrieved chunk belongs to the expected unit."""
    return any(c.get("syllabus_unit") == expected for c in chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=4, help="Chunks to retrieve per question")
    parser.add_argument("--verbose", action="store_true", help="Show retrieved units per question")
    args = parser.parse_args()

    hit1 = hitk = 0
    misses: list[tuple[str, str, list[str]]] = []

    print("=" * 78)
    print(f"RETRIEVAL BENCHMARK — {len(BENCHMARK)} preguntas, top-{args.k}")
    print("=" * 78)

    for question, expected in BENCHMARK:
        chunks = search_chunks(query=question, limit=args.k)
        units = [c.get("syllabus_unit") or "-" for c in chunks]
        first = bool(chunks) and chunks[0].get("syllabus_unit") == expected
        any_hit = unit_matches(chunks, expected)
        hit1 += first
        hitk += any_hit
        mark = "OK " if any_hit else "FALLA"
        if not any_hit:
            misses.append((question, expected, units))
        if args.verbose or not any_hit:
            print(f"{mark} [{expected}] {question[:58]}")
            print(f"      -> {units}")

    total = len(BENCHMARK)
    print("-" * 78)
    print(f"Unidad correcta en la posición 1 : {hit1}/{total}  ({hit1 / total:.0%})")
    print(f"Unidad correcta en el top-{args.k}   : {hitk}/{total}  ({hitk / total:.0%})")
    if misses:
        print("-" * 78)
        print("Preguntas que no recuperaron su unidad:")
        for q, exp, units in misses:
            print(f"  esperado {exp} ({UNIT_TITLES.get(exp, '')})")
            print(f"    {q}")
            print(f"    recuperado: {units}")
    print("=" * 78)
    return 0 if hitk == total else 1


if __name__ == "__main__":
    raise SystemExit(main())