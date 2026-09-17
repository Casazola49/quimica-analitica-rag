"""Mock Google GenAI Client for Deterministic Zero-Cost Testing.

Simulates the Google GenAI SDK (google-genai) client without making real network
calls or consuming API quota. Provides realistic domain-specific chemical engineering
responses with exact bibliographic citations.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator, Optional


class MockAPIError(Exception):
    """Simulates google.genai.errors.APIError."""

    def __init__(self, code: int, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class MockGeminiModel:
    """Represents model metadata returned by client.models.get."""

    def __init__(self, model_id: str):
        self.name = f"models/{model_id}"
        self.display_name = f"Gemini {model_id}"
        self.supported_generation_methods = ["generateContent", "countTokens"]


class MockGeminiChunk:
    """Represents a streaming chunk from generate_content_stream."""

    def __init__(self, text: str):
        self.text = text


class MockGeminiResponse:
    """Represents a completed generation response from generate_content."""

    def __init__(self, text: str):
        self.text = text


class MockGeminiModelsService:
    """Simulates client.models service."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get(self, model: str) -> MockGeminiModel:
        """Lightweight model metadata lookup for key validation."""
        self._check_key_permission()
        clean_model = model.replace("models/", "")
        valid_models = [
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "text-embedding-004",
        ]
        if clean_model not in valid_models:
            raise MockAPIError(404, f"Model '{model}' not found.")
        return MockGeminiModel(clean_model)

    def generate_content(
        self,
        model: str,
        contents: str | list[Any],
        config: Optional[dict[str, Any]] = None,
    ) -> MockGeminiResponse:
        """Simulates LLM content generation."""
        self._check_key_permission()

        prompt_str = self._extract_prompt_text(contents)
        response_text = self._synthesize_response(prompt_str, config)
        return MockGeminiResponse(response_text)

    def generate_content_stream(
        self,
        model: str,
        contents: str | list[Any],
        config: Optional[dict[str, Any]] = None,
    ) -> Iterator[MockGeminiChunk]:
        """Simulates streaming content generation."""
        self._check_key_permission()

        prompt_str = self._extract_prompt_text(contents)
        full_text = self._synthesize_response(prompt_str, config)

        # Yield in realistic word-group chunks
        words = full_text.split(" ")
        chunk_size = 6
        for i in range(0, len(words), chunk_size):
            chunk_slice = words[i : i + chunk_size]
            separator = " " if i + chunk_size < len(words) else ""
            yield MockGeminiChunk(" ".join(chunk_slice) + separator)

    def _check_key_permission(self) -> None:
        if not self.api_key:
            raise MockAPIError(400, "API key is missing or empty.")
        if not self.api_key.startswith("AIzaSy"):
            raise MockAPIError(400, "Invalid API key format. Key must start with 'AIzaSy'.")
        if len(self.api_key) < 30:
            raise MockAPIError(400, "API key is too short.")
        if "QUOTA" in self.api_key or "429" in self.api_key:
            raise MockAPIError(429, "Resource has been exhausted (quota limit exceeded).")
        if "FORBIDDEN" in self.api_key or "403" in self.api_key:
            raise MockAPIError(403, "Caller does not have permission to access model.")
        if "BAD_REQUEST" in self.api_key:
            raise MockAPIError(400, "Bad request: invalid API parameters.")

    def _extract_prompt_text(self, contents: str | list[Any]) -> str:
        if isinstance(contents, str):
            return contents
        if isinstance(contents, list):
            parts = []
            for item in contents:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "parts" in item:
                    for p in item["parts"]:
                        parts.append(p.get("text", ""))
            return "\n".join(parts)
        return str(contents)

    def _synthesize_response(self, prompt: str, config: Optional[dict[str, Any]]) -> str:
        prompt_lower = prompt.lower()

        # 1. Exam Generation Prompt
        if "genera" in prompt_lower and ("examen" in prompt_lower or "preguntas" in prompt_lower or "pregunta" in prompt_lower):
            count = 3
            match = re.search(r"(\d+)\s+preguntas", prompt_lower)
            if match:
                count = int(match.group(1))
            count = max(1, min(count, 10))

            questions = []
            if "sulfato" in prompt_lower or "gravimetr" in prompt_lower or "u3" in prompt_lower or "p5" in prompt_lower:
                questions.append({
                    "id": 1,
                    "question": "¿Cuál es la función principal de la digestión en caliente (maduración de Ostwald) durante la determinación gravimétrica de sulfatos como BaSO4?",
                    "options": [
                        "A) Reducir el BaSO4 a BaS mediante carbón",
                        "B) Favorecer la disolución de microcristales e incrementar el tamaño de partícula facilitando la filtración",
                        "C) Neutralizar el exceso de ion cloruro en disolución",
                        "D) Evaporar el disolvente para alcanzar sequedad"
                    ],
                    "correct_answer": "B",
                    "explanation": "La digestión en caliente favorece la maduración de Ostwald, disolviendo los cristales menores y depositándolos sobre los más grandes, lo que reduce la coprecipitación y mejora la filtrabilidad.",
                    "citation": {
                        "book_title": "Fundamentos de Química Analítica",
                        "author": "Douglas A. Skoog et al.",
                        "edition": "9ª Edición",
                        "chapter": "Capítulo 12: Métodos Gravimétricos de Análisis",
                        "page_num": 315
                    },
                    "unit_id": "U3"
                })
            elif "ácido" in prompt_lower or "neutraliz" in prompt_lower or "u6" in prompt_lower or "p7" in prompt_lower:
                questions.append({
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
                })
            else:
                questions.append({
                    "id": 1,
                    "question": "¿Qué reactivo auxiliar se utiliza comúnmente como reductor previo en la determinación de hierro antes de la titulación con K2Cr2O7?",
                    "options": [
                        "A) SnCl2 en medio caliente con HCl",
                        "B) KMnO4 concentrado",
                        "C) KIO3 con almidón",
                        "D) Na2CO3 anhidro"
                    ],
                    "correct_answer": "A",
                    "explanation": "El SnCl2 reduce cuantitativamente Fe(III) a Fe(II), eliminándose el exceso con HgCl2 para formar el precipitado sedoso de Hg2Cl2.",
                    "citation": {
                        "book_title": "Quantitative Analysis",
                        "author": "R. A. Day, Jr., A. L. Underwood",
                        "edition": "6th Edition",
                        "chapter": "Chapter 11: Oxidation-Reduction Titrations",
                        "page_num": 348
                    },
                    "unit_id": "U9"
                })

            # Repeat or pad to requested count
            while len(questions) < count:
                idx = len(questions) + 1
                questions.append({
                    "id": idx,
                    "question": f"Pregunta conceptual #{idx} sobre el método analítico y su validación estadística:",
                    "options": [
                        "A) Error sistemático atribuible al analista o calibración",
                        "B) Error aleatorio minimizado por repetición estadística",
                        "C) Intervalo de confianza según t de Student",
                        "D) Todas las anteriores son correctas"
                    ],
                    "correct_answer": "D",
                    "explanation": "La evaluación metrológica integral combina la identificación de sesgos y la dispersión estadística de réplicas.",
                    "citation": {
                        "book_title": "Fundamentos de Química Analítica",
                        "author": "Douglas A. Skoog et al.",
                        "edition": "9ª Edición",
                        "chapter": "Capítulo 5: Errores en los Análisis Químicos",
                        "page_num": 98
                    },
                    "unit_id": "U2"
                })

            return json.dumps({"questions": questions}, ensure_ascii=False, indent=2)

        # 2. Exam Evaluation Prompt
        if "evalúa" in prompt_lower or "califica" in prompt_lower or "respuestas del estudiante" in prompt_lower:
            feedback = [
                {
                    "question_id": 1,
                    "is_correct": True,
                    "feedback": "¡Excelente deducción termodinámica! La justificación está plenamente respaldada por la cinética de nucleación y crecimiento cristalino.",
                    "citation": {
                        "book_title": "Fundamentos de Química Analítica",
                        "author": "Douglas A. Skoog et al.",
                        "edition": "9ª Edición",
                        "chapter": "Capítulo 12: Métodos Gravimétricos de Análisis",
                        "page_num": 315
                    }
                }
            ]
            citations = [
                {
                    "book_title": "Fundamentos de Química Analítica",
                    "author": "Douglas A. Skoog et al.",
                    "edition": "9ª Edición",
                    "chapter": "Capítulo 12: Métodos Gravimétricos de Análisis",
                    "page_num": 315,
                    "excerpt": "La sobresaturación relativa de Von Weimarn (Q-S)/S debe mantenerse baja mediante digestión térmica prolongada."
                }
            ]
            return json.dumps({
                "score": 100.0,
                "total_questions": 1,
                "correct_answers": 1,
                "feedback": feedback,
                "citations": citations
            }, ensure_ascii=False, indent=2)

        # 3. Chemical Engineering Tutor & RAG Queries
        if "sulfato" in prompt_lower or "baso4" in prompt_lower or "weimarn" in prompt_lower or "rss" in prompt_lower or "gravimetr" in prompt_lower or "coprecipit" in prompt_lower:
            return (
                "Para la determinación gravimétrica de sulfatos como $BaSO_4$ (Práctica 5 / Unidad 3):\n\n"
                "1. **Mecanismo de Precipitación**: Se basa en la reacción cuantitativa:\n"
                "$$SO_4^{2-} + Ba^{2+} \\rightarrow BaSO_4(s)$$\n\n"
                "2. **Sobresaturación Relativa**: Según Von Weimarn, $RSS = \\frac{Q - S}{S}$. Para obtener cristales grandes y fácilmente filtrables, se mantiene $Q$ bajo agregando $BaCl_2$ diluido lentamente con agitación en caliente ($90^\\circ\\text{C}$), aumentando $S$ temporalmente con medio ácido clorhídrico.\n\n"
                "3. **Maduración de Ostwald**: La digestión en caliente favorece la redisolución de microcristales coloidales y su crecimiento en macrorredes cristalinas.\n\n"
                "4. **Precaución Crítica**: Al calcinar el filtro Whatman 42 a $800^\\circ\\text{C}$, se debe evitar la llama directa para impedir la reducción parcial:\n"
                "$$BaSO_4 + 4C \\rightarrow BaS + 4CO$$\n\n"
                "[Libro: Fundamentos de Química Analítica, Skoog et al., 9na Ed., Cap. 12, Pág. 315-320]"
            )

        if "mohr" in prompt_lower or "volhard" in prompt_lower or "argentometr" in prompt_lower:
            return (
                "En las valoraciones de precipitación argentométricas (Unidad 5 / Práctica 6):\n\n"
                "- **Método de Mohr**: Titulación directa de haluros ($Cl^-$) con $AgNO_3$ estándar empleando $K_2CrO_4$ como indicador a $pH \\in [6.5, 10.0]$. En el punto final se forma el precipitado rojo ladrillo de cromato de plata:\n"
                "$$2Ag^+ + CrO_4^{2-} \\rightarrow Ag_2CrO_4(s)$$\n"
                "A $pH < 6.5$, el cromato se protona formando $HCrO_4^-$ y $Cr_2O_7^{2-}$, retrasando el punto final.\n\n"
                "- **Método de Volhard**: Titulación por retroceso en medio ácido ($HNO_3$). Se agrega exceso de $AgNO_3$ y se retrotitula con $KSCN$ en presencia de $Fe^{3+}$ como indicador (formación de $[Fe(SCN)]^{2+}$ rojo sangre). Es imprescindible recubrir el $AgCl$ con nitrobenceno o filtrarlo debido a que $K_{ps}(AgCl) > K_{ps}(AgSCN)$.\n\n"
                "[Libro: Fundamentos de Química Analítica, Skoog et al., 9na Ed., Cap. 17, Pág. 410-418]"
            )

        if "edta" in prompt_lower or "dureza" in prompt_lower or "complejo" in prompt_lower:
            return (
                "En las valoraciones quelatométricas con EDTA (Unidad 7 / Práctica 10 y 11):\n\n"
                "1. El EDTA ($H_4Y$) reacciona estequiométricamente 1:1 con iones metálicos dipositivos ($Ca^{2+}, Mg^{2+}$):\n"
                "$$M^{2+} + Y^{4-} \\rightleftharpoons MY^{2-}$$\n\n"
                "2. La constante condicional de formación se expresa como $K'_{MY} = \\alpha_4 \\cdot K_{MY}$, donde $\\alpha_4$ depende críticamente del pH.\n\n"
                "3. Para la determinación de dureza de agua, a pH 10 (tampón $NH_3/NH_4^+$) se determina la dureza total ($Ca^{2+} + Mg^{2+}$) con Negro de Eriocromo T (NET). A pH 12 ($NaOH$), precipita $Mg(OH)_2$ y se cuantifica la dureza cálcica selectiva con indicador Murexida.\n\n"
                "[Libro: Introducción a los Equilibrios Iónicos, Aguilar San Juan, 2da Ed., Cap. 8, Pág. 405-420]"
            )

        if "ácido" in prompt_lower or "neutraliz" in prompt_lower or "buffer" in prompt_lower or "tampón" in prompt_lower or "amortiguador" in prompt_lower or "ph" in prompt_lower:
            return (
                "En las valoraciones de neutralización ácido-base (Unidad 6 / Práctica 7):\n\n"
                "1. Ecuación de Henderson-Hasselbalch para soluciones reguladoras:\n"
                "$$pH = pKa + \\log\\left(\\frac{[A^-]}{[HA]}\\right)$$\n\n"
                "2. Capacidad reguladora $\\beta$ máxima cuando $[A^-] = [HA]$ y $pH = pKa$.\n\n"
                "3. En la titulación potenciométrica con electrodo combinado de vidrio, el punto de equivalencia se localiza exactamente mediante la segunda derivada:\n"
                "$$\\frac{d^2pH}{dV^2} = 0$$\n\n"
                "[Libro: Fundamentos de Química Analítica, Skoog et al., 9na Ed., Cap. 14, Pág. 350-365]"
            )

        # General chemistry response with default citation
        return (
            "En Química Analítica Cuantitativa, la precisión se evalúa mediante la desviación estándar ($s$) "
            "y el coeficiente de variación ($CV$), mientras que la exactitud se verifica con estándares primarios y blancos.\n\n"
            "$$s = \\sqrt{\\frac{\\sum_{i=1}^n (x_i - \\bar{x})^2}{n - 1}}$$\n\n"
            "[Libro: Fundamentos de Química Analítica, Skoog et al., 9na Ed., Cap. 5, Pág. 95-105]"
        )


class MockGeminiClient:
    """Entry point mock for genai.Client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models = MockGeminiModelsService(api_key=api_key)
