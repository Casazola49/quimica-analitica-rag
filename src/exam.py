"""
src/exam.py - Dynamic Exam Simulator Engine for Química Analítica.

Generates multiple-choice practice exams grounded in theory units and
laboratory practicals. Evaluates student answers against an objective
rubric, calculates percentage scores, validates pass/fail status, and provides
pedagogical explanations and textbook page citations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Comprehensive Curriculum-Grounded Question Bank covering all units
QUESTION_BANK: Dict[str, List[Dict[str, Any]]] = {
    "U1": [
        {
            "id": 1,
            "question": "¿Cuál es la secuencia correcta de etapas en el proceso analítico cuantitativo clásico?",
            "options": [
                "A) Muestreo -> Preparación de muestra -> Medición analítica -> Tratamiento estadístico y reporte",
                "B) Medición directa -> Muestreo -> Disolución ácida -> Presentación",
                "C) Calibración -> Muestreo representativo -> Calcinación -> Titulación",
                "D) Pesada rápida -> Filtración -> Digestión -> Descarte"
            ],
            "correct_answer": "A",
            "explanation": "El proceso analítico se inicia con la obtención de una muestra representativa, seguida de disolución/eliminación de interferencias, cuantificación instrumental o gravimétrica/volumétrica, y reporte estadístico.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 1: La Naturaleza de la Química Analítica",
                "page_num": 12
            },
            "unit_id": "U1"
        },
        {
            "id": 2,
            "question": "¿Cómo se define la concentración expresada en partes por millón (ppm) para una disolución acuosa diluida?",
            "options": [
                "A) 1 ppm = 1 mg de soluto / 1 L de disolución",
                "B) 1 ppm = 1 g de soluto / 100 mL de agua",
                "C) 1 ppm = 1 mol de soluto / 1 kg de solvente",
                "D) 1 ppm = 1 equivalente-gramo / 1 L de disolución"
            ],
            "correct_answer": "A",
            "explanation": "Dado que la densidad del agua pura a temperatura ambiente es aproximadamente 1.00 g/mL, 1 ppm equivale a 1 mg por litro ($10^{-3}\\text{ g} / 10^3\\text{ g}$).",
            "citation": {
                "book_title": "Química Analítica Cuantitativa",
                "author": "R. A. Day, Jr., A. L. Underwood",
                "edition": "5ª Edición",
                "chapter": "Capítulo 1: Errores y Tratamiento de Datos",
                "page_num": 24
            },
            "unit_id": "U1"
        }
    ],
    "U2": [
        {
            "id": 1,
            "question": "¿Cuál es la formulación matemática de la prueba Q de Dixon para evaluar un dato sospechoso en una serie de réplicas?",
            "options": [
                "A) Q_calc = |x_sospechoso - x_vecino| / (x_max - x_min)",
                "B) Q_calc = (media - mediana) / desviacion_estandar",
                "C) Q_calc = |x_sospechoso - media| * sqrt(N)",
                "D) Q_calc = (x_max + x_min) / 2"
            ],
            "correct_answer": "A",
            "explanation": "La prueba Q de Dixon calcula la razón entre la discrepancia del dato dudoso respecto a su vecino más cercano y el rango total (dispersión) de las mediciones ordenadas.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 5: Errores en los Análisis Químicos",
                "page_num": 98
            },
            "unit_id": "U2"
        },
        {
            "id": 2,
            "question": "¿Cuál es la diferencia fundamental entre un error sistemático (determinado) y un error aleatorio (indeterminado)?",
            "options": [
                "A) El error sistemático introduce un sesgo constante o proporcional reproducible; el error aleatorio causa dispersión simétrica en torno a la media",
                "B) El error aleatorio siempre es positivo y el sistemático siempre es negativo",
                "C) El error sistemático se elimina repitiendo muchas mediciones",
                "D) No existe diferencia metrológica entre ambos"
            ],
            "correct_answer": "A",
            "explanation": "Los errores sistemáticos tienen causas asignables (calibración instrumental, impureza en reactivos, sesgo del analista) y afectan la exactitud; los errores aleatorios provienen de fluctuaciones incontrolables y determinan la precisión.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 5: Errores en los Análisis Químicos",
                "page_num": 102
            },
            "unit_id": "U2"
        }
    ],
    "U3": [
        {
            "id": 1,
            "question": "¿Cómo se expresa la Sobresaturación Relativa (RSS) de Von Weimarn y qué condición favorece precipitados cristalinos?",
            "options": [
                "A) RSS = (Q - S) / S; se debe minimizar manteniendo baja concentración de reactivos y alta temperatura",
                "B) RSS = (S - Q) / Q; se debe maximizar enfriando bruscamente con hielo",
                "C) RSS = Q * S; se debe aumentar añadiendo reactivo concentrado sin agitar",
                "D) RSS = Q / S^2; se debe mantener en el punto isoeléctrico"
            ],
            "correct_answer": "A",
            "explanation": "La ecuación de Von Weimarn es RSS = (Q - S) / S. Un RSS bajo disminuye la velocidad de nucleación respecto a la de crecimiento cristalino, produciendo cristales grandes, puros y fácilmente filtrables.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 12: Métodos Gravimétricos de Análisis",
                "page_num": 315
            },
            "unit_id": "U3"
        },
        {
            "id": 2,
            "question": "En la determinación gravimétrica de sulfatos como BaSO4, ¿por qué se realiza la digestión térmica prolongada?",
            "options": [
                "A) Para favorecer la maduración de Ostwald, disolviendo micropartículas coloidales y redepositándolas sobre cristales grandes",
                "B) Para evaporar todo el ácido clorhídrico de la disolución",
                "C) Para oxidar el sulfato a persulfato",
                "D) Para evitar que el precipitado se vuelva cristalino"
            ],
            "correct_answer": "A",
            "explanation": "La digestión en caliente a 90 °C permite que las partículas coloidales con mayor solubilidad se disuelvan y precipiten sobre partículas mayores, purificando el sólido y facilitando la retención en papel Whatman 42.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 12: Métodos Gravimétricos de Análisis",
                "page_num": 318
            },
            "unit_id": "U3"
        },
        {
            "id": 3,
            "question": "¿Cuáles son los cuatro mecanismos conocidos de coprecipitación en métodos gravimétricos?",
            "options": [
                "A) Adsorción superficial, inclusión isomorfa, oclusión mecánica y atrapamiento en la red",
                "B) Evaporación, condensación, sublimación y electrólisis",
                "C) Oxidación, reducción, complejación y volatilización",
                "D) Disolución, hidrólisis, saponificación y neutralización"
            ],
            "correct_answer": "A",
            "explanation": "La coprecipitación es la precipitación de compuestos normalmente solubles junto con el precipitado deseado mediante adsorción superficial, formación de disoluciones sólidas (inclusión) u oclusión/atrapamiento físico.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 12: Métodos Gravimétricos de Análisis",
                "page_num": 322
            },
            "unit_id": "U3"
        }
    ],
    "U4": [
        {
            "id": 1,
            "question": "¿Qué efecto produce el agregado de un electrolito con ion común sobre la solubilidad molar de una sal poco soluble?",
            "options": [
                "A) Disminuye la solubilidad molar debido al desplazamiento del equilibrio según el Principio de Le Châtelier",
                "B) Aumenta la solubilidad molar al incrementar el producto Kps",
                "C) No produce ningún cambio sobre la solubilidad",
                "D) Convierte inmediatamente el precipitado en coloide estable"
            ],
            "correct_answer": "A",
            "explanation": "La adición de un ion común aumenta su concentración en disolución, forzando la precipitación para mantener constante el producto de solubilidad Kps.",
            "citation": {
                "book_title": "Introducción a los equilibrios iónicos",
                "author": "Manuel Aguilar Sanjuán",
                "edition": "2ª Edición",
                "chapter": "Capítulo 5: Equilibrios de Precipitación",
                "page_num": 195
            },
            "unit_id": "U4"
        }
    ],
    "U5": [
        {
            "id": 1,
            "question": "¿Cuál es el compuesto responsable de la coloración rojo ladrillo en el punto final del método de Mohr?",
            "options": [
                "A) AgCl",
                "B) Ag2CrO4",
                "C) BaSO4",
                "D) Fe(SCN)2+"
            ],
            "correct_answer": "B",
            "explanation": "El cromato de plata Ag2CrO4 es el precipitado rojo que se forma inmediatamente después de consumir cuantitativamente todos los iones cloruro en la muestra.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 17: Valoraciones de Precipitación",
                "page_num": 412
            },
            "unit_id": "U5"
        },
        {
            "id": 2,
            "question": "¿Por qué en el método de Volhard para cloruros se debe aislar o filtrar el AgCl antes de retrotitular con KSCN?",
            "options": [
                "A) Porque el AgCl es más soluble que el AgSCN (Kps AgCl > Kps AgSCN) y el tiocianato desplazaría al cloruro",
                "B) Para secar y pesar el cloruro de plata",
                "C) Porque el AgCl inhibe la formación de color con el indicador Fe3+",
                "D) Para eliminar el ácido nítrico de la disolución"
            ],
            "correct_answer": "A",
            "explanation": "Al ser Kps(AgCl) = 1.82e-10 mayor que Kps(AgSCN) = 1.1e-12, la reacción AgCl(s) + SCN- -> AgSCN(s) + Cl- ocurriría lentamente, provocando sobreconsumo de tiocianato.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 17: Valoraciones de Precipitación",
                "page_num": 415
            },
            "unit_id": "U5"
        }
    ],
    "U6": [
        {
            "id": 1,
            "question": "En la titulación de un ácido débil HA con NaOH, ¿cuál es la relación de Henderson-Hasselbalch que describe el pH en el punto de semi-equivalencia?",
            "options": [
                "A) pH = 7.00",
                "B) pH = pKa",
                "C) pH = pKa + 1",
                "D) pH = 14 - pKb"
            ],
            "correct_answer": "B",
            "explanation": "En el punto de semi-equivalencia [A-] = [HA], por lo que log([A-]/[HA]) = log(1) = 0 y pH = pKa.",
            "citation": {
                "book_title": "Introducción a los Equilibrios Iónicos",
                "author": "Manuel Aguilar San Juan",
                "edition": "2ª Edición",
                "chapter": "Capítulo 3: Disoluciones tampón y valoraciones ácido-base",
                "page_num": 112
            },
            "unit_id": "U6"
        },
        {
            "id": 2,
            "question": "¿En qué condición es máxima la capacidad reguladora beta de una disolución tampón?",
            "options": [
                "A) Cuando pH = pKa, es decir, cuando la relación [A-] / [HA] es igual a 1",
                "B) Cuando la concentración del amortiguador tiende a cero",
                "C) Cuando pH = 14",
                "D) Cuando se añade ácido fuerte en exceso"
            ],
            "correct_answer": "A",
            "explanation": "La capacidad reguladora es máxima en el punto medio del tampón, donde las concentraciones de ácido y base conjugada son idénticas y el pH coincide con el pKa.",
            "citation": {
                "book_title": "Introducción a los equilibrios iónicos",
                "author": "Manuel Aguilar Sanjuán",
                "edition": "2ª Edición",
                "chapter": "Capítulo 3: Disoluciones tampón y valoraciones ácido-base",
                "page_num": 112
            },
            "unit_id": "U6"
        }
    ],
    "U7": [
        {
            "id": 1,
            "question": "En la determinación de dureza de agua con EDTA, ¿qué condiciones y reactivos diferencian la Dureza Total de la Dureza Cálcica?",
            "options": [
                "A) Dureza Total a pH 10 con tampón amoniacal y NET; Dureza Cálcica a pH 12 con NaOH (precipitando Mg(OH)2) y Murexida",
                "B) Dureza Total a pH 2 con HCl; Dureza Cálcica a pH 7 con agua destilada",
                "C) Dureza Total con fenolftaleína; Dureza Cálcica con cromato de potasio",
                "D) Ambas se determinan a pH 7 usando almidón como indicador"
            ],
            "correct_answer": "A",
            "explanation": "A pH 10 el EDTA titula conjuntamente Ca2+ y Mg2+ con Negro de Eriocromo T. A pH 12, el magnesio precipita cuantitativamente como Mg(OH)2 y el indicador Murexida vira selectivamente con calcio.",
            "citation": {
                "book_title": "Introducción a los equilibrios iónicos",
                "author": "Manuel Aguilar Sanjuán",
                "edition": "2ª Edición",
                "chapter": "Capítulo 8: Complejometría con EDTA",
                "page_num": 415
            },
            "unit_id": "U7"
        }
    ],
    "U8": [
        {
            "id": 1,
            "question": "¿Cuál es el potencial teórico en el punto de equivalencia para la titulación de Fe2+ con Ce4+ (E° Fe3+/Fe2+ = 0.771 V, E° Ce4+/Ce3+ = 1.440 V en medio 1M H2SO4)?",
            "options": [
                "A) E_pe = 1.1055 V",
                "B) E_pe = 0.7710 V",
                "C) E_pe = 1.4400 V",
                "D) E_pe = 0.0000 V"
            ],
            "correct_answer": "A",
            "explanation": "Para n1 = n2 = 1, el potencial en el punto de equivalencia es el promedio aritmético exacto: E_pe = (0.771 + 1.440) / 2 = 1.1055 V.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 19: Teoría de las Valoraciones de Oxidación-Reducción",
                "page_num": 485
            },
            "unit_id": "U8"
        }
    ],
    "U9": [
        {
            "id": 1,
            "question": "¿Qué reactivo auxiliar se utiliza comúnmente como reductor previo en la determinación de hierro antes de la titulación con K2Cr2O7?",
            "options": [
                "A) SnCl2 en medio caliente con HCl, eliminando el exceso con HgCl2",
                "B) KMnO4 concentrado en medio frío",
                "C) KIO3 con suspensión de almidón",
                "D) Na2CO3 anhidro a temperatura ambiente"
            ],
            "correct_answer": "A",
            "explanation": "El SnCl2 reduce cuantitativamente Fe(III) a Fe(II). El exceso de estaño debe destruirse con HgCl2 para formar el precipitado sedoso blanco de Hg2Cl2.",
            "citation": {
                "book_title": "Quantitative Analysis",
                "author": "R. A. Day, Jr., A. L. Underwood",
                "edition": "6ª Edición",
                "chapter": "Capítulo 11: Titulaciones de Oxidación-Reducción",
                "page_num": 348
            },
            "unit_id": "U9"
        },
        {
            "id": 2,
            "question": "¿Por qué se debe calentar la disolución de oxalato de sodio a 70-80 °C al inicio de la titulación permanganométrica?",
            "options": [
                "A) Porque la reacción inicial entre MnO4- y C2O4(2-) tiene una elevada energía de activación y es catalizada por el ion Mn2+ producido",
                "B) Para evaporar el ácido sulfúrico residual",
                "C) Para precipitar el permanganato de potasio",
                "D) Para evitar que el dióxido de carbono se desprenda"
            ],
            "correct_answer": "A",
            "explanation": "La reacción permanganométrica con oxalato es muy lenta a temperatura ambiente. Una vez que se forman las primeras trazas de Mn2+, actúa como autocatalizador a alta temperatura.",
            "citation": {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 20: Aplicaciones de las Valoraciones de Oxidación-Reducción",
                "page_num": 535
            },
            "unit_id": "U9"
        }
    ]
}


def generate_exam_questions(
    unit_id: str,
    count: int = 3,
    difficulty: str = "media",
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generates dynamic or curriculum-bank exam questions for the specified unit.
    Clamps count safely to [1, 10] and handles unrecognized difficulty strings.
    """
    # 1. Clamp question count strictly to [1, 10]
    try:
        if isinstance(count, float):
            count_int = int(count)
        else:
            try:
                count_int = int(count)
            except ValueError:
                count_int = int(float(count))
    except (TypeError, ValueError):
        count_int = 3
    clamped_count = max(1, min(count_int, 10))

    # 2. Normalize difficulty
    diff_norm = str(difficulty).lower().strip()
    if diff_norm not in ("facil", "fácil", "easy", "media", "medium", "dificil", "difícil", "hard"):
        diff_norm = "media"

    # 3. Normalize unit ID
    clean_unit = str(unit_id).strip().upper() if unit_id else "U1"
    if clean_unit.startswith("THEORY_"):
        clean_unit = clean_unit.replace("THEORY_", "")
    if clean_unit.startswith("LAB_U"):
        clean_unit = clean_unit.replace("LAB_U", "L")

    # 4. Attempt LLM generation if valid API key provided
    if api_key and str(api_key).strip().startswith(("AIzaSy", "AQ.")):
        try:
            from src.gemini_client import generate_response
            llm_prompt = (
                f"Genera {clamped_count} preguntas de examen para la unidad {clean_unit} con nivel de dificultad {diff_norm}.\n"
                f"Formato JSON estricto requerido:\n"
                f"{{\n"
                f'  "questions": [\n'
                f"    {{\n"
                f'      "id": 1,\n'
                f'      "question": "Pregunta...",\n'
                f'      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
                f'      "correct_answer": "A",\n'
                f'      "explanation": "Explicación detallada...",\n'
                f'      "citation": {{\n'
                f'        "book_title": "Fundamentos de Química Analítica",\n'
                f'        "author": "Douglas A. Skoog et al.",\n'
                f'        "edition": "9ª Edición",\n'
                f'        "chapter": "Capítulo 12",\n'
                f'        "page_num": 315\n'
                f"      }},\n"
                f'      "unit_id": "{clean_unit}"\n'
                f"    }}\n"
                f"  ]\n"
                f"}}"
            )
            raw_res = generate_response(
                api_key=str(api_key).strip(),
                prompt=llm_prompt,
                system_instruction="Eres un evaluador académico experto en Química Analítica. Devuelve exclusivamente JSON válido sin rodeos ni markdown exterior."
            )
            cleaned_json = str(raw_res).strip()
            if cleaned_json.startswith("```"):
                cleaned_json = re.sub(r"^```(?:json)?", "", cleaned_json).strip()
                cleaned_json = re.sub(r"```$", "", cleaned_json).strip()

            parsed = json.loads(cleaned_json)
            raw_questions = parsed.get("questions", [])
            valid_questions = []
            for idx, q in enumerate(raw_questions[:clamped_count], 1):
                if (
                    isinstance(q, dict)
                    and "question" in q
                    and "options" in q
                    and isinstance(q["options"], list)
                    and len(q["options"]) >= 2
                    and "correct_answer" in q
                ):
                    q_copy = dict(q)
                    q_copy["id"] = idx
                    q_copy["unit_id"] = clean_unit
                    if "citation" not in q_copy or not isinstance(q_copy["citation"], dict):
                        q_copy["citation"] = {
                            "book_title": "Fundamentos de Química Analítica",
                            "author": "Douglas A. Skoog et al.",
                            "edition": "9ª Edición",
                            "chapter": "Capítulo General",
                            "page_num": 100
                        }
                    valid_questions.append(q_copy)

            if len(valid_questions) == clamped_count:
                return valid_questions
        except Exception as e:
            logger.warning("Dynamic question generation via LLM failed: %s, falling back to bank", e)

    # 5. Deterministic Question Bank Fallback
    bank_questions = QUESTION_BANK.get(clean_unit, [])
    if not bank_questions:
        lab_map = {
            "LAB_P1": "U1", "LAB_P2": "U2", "LAB_P3": "U1", "LAB_P4": "U1",
            "LAB_P5": "U3", "LAB_P6": "U5", "LAB_P7": "U6", "LAB_P8": "U9",
            "LAB_P9": "U9", "LAB_P10": "U7", "LAB_P11": "U8", "LAB_P12": "U9",
            "L1": "U2", "L2": "U1", "L3": "U1", "L4": "U3", "L5": "U5", "L6": "U8", "L7": "U9", "L8": "U9"
        }
        mapped_unit = lab_map.get(clean_unit, "U3")
        bank_questions = QUESTION_BANK.get(mapped_unit, QUESTION_BANK["U3"])

    selected = []
    for i in range(clamped_count):
        source_q = bank_questions[i % len(bank_questions)]
        q_copy = dict(source_q)
        q_copy["id"] = i + 1
        q_copy["unit_id"] = clean_unit
        selected.append(q_copy)

    return selected


def evaluate_exam_submission(
    questions: List[Dict[str, Any]],
    student_answers: List[str],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates student exam answers, computes percentage score, validates pass status,
    and formats per-question feedback with verifiable citations.
    """
    # 1. Handle empty question set
    if not questions or not isinstance(questions, list):
        return {
            "score": 0.0,
            "total_questions": 0,
            "correct_answers": 0,
            "passed": False,
            "feedback": [],
            "citations": []
        }

    total_count = len(questions)
    correct_count = 0
    feedback_items = []
    collected_citations = []
    seen_citation_keys = set()

    # Normalize student_answers to list
    if student_answers is None or not isinstance(student_answers, (list, tuple)):
        safe_answers = []
    else:
        safe_answers = list(student_answers)

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        raw_ans = safe_answers[idx] if idx < len(safe_answers) else ""
        raw_ans_str = str(raw_ans).strip() if raw_ans is not None else ""

        # Extract answer letter (e.g. "A" from "A", "a", "A) AgCl", "A.")
        m = re.match(r"^\s*([A-Da-d])(?:[\)\.\:\s]|$)", raw_ans_str)
        student_letter = m.group(1).upper() if m else raw_ans_str.upper()

        expected_letter = str(q.get("correct_answer") or "").strip().upper()

        is_correct = bool(student_letter and (student_letter == expected_letter))
        if is_correct:
            correct_count += 1

        cit = q.get("citation")
        if not isinstance(cit, dict):
            cit = {}

        raw_exp = q.get("explanation")
        feedback_text = str(raw_exp) if raw_exp is not None else "Explicación del fundamento químico."
        if not is_correct and student_letter:
            feedback_text = (
                f"Respuesta incorrecta: seleccionaste ({student_letter}). "
                f"La opción correcta es ({expected_letter}). {feedback_text}"
            )
        elif not student_letter:
            feedback_text = (
                f"Pregunta sin responder. La opción correcta es ({expected_letter}). {feedback_text}"
            )

        feedback_items.append({
            "question_id": q.get("id", idx + 1),
            "is_correct": is_correct,
            "student_answer": raw_ans_str,
            "correct_answer": expected_letter,
            "feedback": feedback_text,
            "citation": cit
        })

        if cit and "book_title" in cit:
            cit_key = f"{cit.get('book_title')}_{cit.get('chapter')}_{cit.get('page_num')}"
            if cit_key not in seen_citation_keys:
                collected_citations.append(cit)
                seen_citation_keys.add(cit_key)

    score = round((correct_count / total_count) * 100.0, 1)
    passed = bool(score >= 51.0)

    return {
        "score": score,
        "total_questions": total_count,
        "correct_answers": correct_count,
        "passed": passed,
        "feedback": feedback_items,
        "citations": collected_citations
    }
