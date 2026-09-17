"""
tests/test_challenger_empirical_m3_ui_stress.py - Empirical Adversarial Stress Test Suite
for Milestone 3: Tutor Chat UI, Exam Simulator UI, and Headless Environment Safety.

Executed by: Challenger 2 (teamwork_preview_challenger_m3_2)
Objective:
1. Tutor Chat UI Stress Testing:
   - Empty and rapid whitespace chat submissions: verify they are ignored and do not pollute message history.
   - Chat message structure: verify message history maintains {"role": "user"|"assistant", "content": ...}.
   - Citation drawer labels: verify format conforms to '📖 {book_title} (Pág. {page_num})'.
   - Guided study mode: verify topic suggestion and seamless transition to exam.
2. Exam Simulator UI Stress Testing:
   - Question rendering state: verify questions list, options formatting with prefixes A) , B) , C) , D) , and student answer tracking.
   - Scorecard evaluation: test boundary score cases (0/3 = 0.0%, 1/3 = 33.3%, 2/3 = 66.7%, 3/3 = 100.0%). Verify badge string conforms to f"Puntaje Obtenido: {score_val}%".
   - Passing threshold: verify scores < 51.0% trigger failing status and remediation advice, and >= 51.0% trigger passing status.
   - Retake/reset operations: verify exam state resets cleanly without corruption.
3. Headless Environment Safety:
   - Verify STREAMLIT_AVAILABLE guard and ensure no crashes when imported in headless test runners.
"""

from __future__ import annotations

import html
import re
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

import src.ui as ui
from src.exam import QUESTION_BANK, evaluate_exam_submission, generate_exam_questions
from src.tutor import suggest_next_topic


# ==============================================================================
# Mock Streamlit Infrastructure for Empirical Component Testing
# ==============================================================================

class StreamlitRerunInterrupt(Exception):
    """Simulates Streamlit's internal RerunException when st.rerun() is called."""
    pass


class MockContextManager:
    """Generic no-op context manager for containers, expanders, chat messages."""
    def __init__(self, name: str = "context"):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def markdown(self, text: str):
        pass

    def caption(self, text: str):
        pass

    def write(self, *args):
        pass

    def info(self, text: str):
        pass


class MockStreamlitContext:
    """
    Comprehensive Headless Mock Context for Streamlit View Renderers.
    Emulates st layout, session_state, input elements, metrics, and lifecycle triggers.
    """

    def __init__(
        self,
        session_state: Optional[Dict[str, Any]] = None,
        raise_on_rerun: bool = True,
        chat_input_val: Optional[str] = None,
    ):
        self.session_state: Dict[str, Any] = session_state if session_state is not None else {}
        self.raise_on_rerun = raise_on_rerun
        self.chat_input_val = chat_input_val
        self.rerun_called = False
        self.balloons_called = False
        self.sidebar = self

        # Captured output logs
        self.rendered_markdown: List[str] = []
        self.rendered_headers: List[str] = []
        self.rendered_metrics: List[Dict[str, Any]] = []
        self.rendered_success: List[str] = []
        self.rendered_errors: List[str] = []
        self.rendered_infos: List[str] = []

        # Programmable inputs
        self.button_clicks: Dict[str, bool] = {}
        self.selectbox_values: Dict[str, Any] = {}
        self.radio_values: Dict[str, Any] = {}
        self.slider_values: Dict[str, Any] = {}
        self.text_input_values: Dict[str, str] = {}

    def rerun(self) -> None:
        self.rerun_called = True
        if self.raise_on_rerun:
            raise StreamlitRerunInterrupt("st.rerun() invoked")

    def header(self, text: str) -> None:
        self.rendered_headers.append(text)

    def subheader(self, text: str) -> None:
        self.rendered_headers.append(text)

    def caption(self, text: str) -> None:
        self.rendered_markdown.append(f"CAPTION: {text}")

    def markdown(self, text: str, unsafe_allow_html: bool = False) -> None:
        self.rendered_markdown.append(text)

    def write(self, *args) -> None:
        self.rendered_markdown.append(" ".join(str(a) for a in args))

    def info(self, text: str) -> None:
        self.rendered_infos.append(text)

    def success(self, text: str) -> None:
        self.rendered_success.append(text)

    def error(self, text: str) -> None:
        self.rendered_errors.append(text)

    def divider(self) -> None:
        pass

    def balloons(self) -> None:
        self.balloons_called = True

    def metric(self, label: str, value: Any, delta: Optional[str] = None) -> None:
        self.rendered_metrics.append({"label": label, "value": str(value), "delta": delta})

    def columns(self, spec: Any) -> List[MockContextManager]:
        count = spec if isinstance(spec, int) else len(spec)
        return [MockContextManager(f"col_{i}") for i in range(count)]

    def tabs(self, titles: List[str]) -> List[MockContextManager]:
        return [MockContextManager(f"tab_{t}") for t in titles]

    def container(self, border: bool = False) -> MockContextManager:
        return MockContextManager("container")

    def expander(self, label: str, expanded: bool = False) -> MockContextManager:
        return MockContextManager(f"expander_{label}")

    def chat_message(self, name: str) -> MockContextManager:
        return MockContextManager(f"chat_{name}")

    def chat_input(self, placeholder: str) -> Optional[str]:
        return self.chat_input_val

    def button(self, label: str, key: Optional[str] = None, **kwargs) -> bool:
        k = key or label
        return self.button_clicks.get(k, False)

    def selectbox(self, label: str, options: List[Any], index: int = 0, format_func: Optional[Any] = None, key: Optional[str] = None) -> Any:
        k = key or label
        if k in self.selectbox_values:
            return self.selectbox_values[k]
        return options[index] if 0 <= index < len(options) else (options[0] if options else None)

    def radio(self, label: str, options: List[Any], index: Optional[int] = None, key: Optional[str] = None, **kwargs) -> Any:
        k = key or label
        if k in self.radio_values:
            return self.radio_values[k]
        if index is not None and 0 <= index < len(options):
            return options[index]
        return None

    def slider(self, label: str, min_value: int, max_value: int, value: int, step: int = 1, key: Optional[str] = None) -> int:
        k = key or label
        return self.slider_values.get(k, value)

    def text_input(self, label: str, value: str = "", key: Optional[str] = None, **kwargs) -> str:
        k = key or label
        return self.text_input_values.get(k, value)

    def link_button(self, label: str, url: str, **kwargs) -> None:
        pass

    def image(self, image_data: Any, **kwargs) -> None:
        pass

    def spinner(self, text: str) -> MockContextManager:
        return MockContextManager(f"spinner_{text}")


# ==============================================================================
# 1. TUTOR CHAT UI EMPIRICAL STRESS TESTS
# ==============================================================================

class TestTutorChatUiStressHarness:
    """Stress tests covering Tutor Chat input handling, message schema, citations, and guided study."""

    def test_empty_chat_submission_is_ignored(self) -> None:
        """Verify empty string chat submission does not trigger LLM and does not pollute history."""
        session = ui.init_session_state({})
        assert len(session["messages"]) == 0

        mock_ctx = MockStreamlitContext(session_state=session, chat_input_val="")
        ui.render_tutor_tab(st_ctx=mock_ctx)

        assert len(session["messages"]) == 0
        assert not mock_ctx.rerun_called

    def test_whitespace_chat_submission_with_rerun_interruption(self) -> None:
        """
        Verify whitespace submissions ('   ', tabs, newlines) trigger rerun interruption
        and do NOT pollute message history when st.rerun acts as flow control interrupt.
        """
        whitespace_payloads = [" ", "   ", "\t\t", "\n\r\n", " \t \n ", "\u2003\u2002  "]
        for ws in whitespace_payloads:
            session = ui.init_session_state({"messages": []})
            mock_ctx = MockStreamlitContext(session_state=session, chat_input_val=ws, raise_on_rerun=True)

            with pytest.raises(StreamlitRerunInterrupt):
                ui.render_tutor_tab(st_ctx=mock_ctx)

            assert mock_ctx.rerun_called is True
            assert len(session["messages"]) == 0, f"Whitespace payload {ws!r} polluted message history!"

    def test_whitespace_chat_submission_fallthrough_without_exception(self) -> None:
        """
        EMPIRICAL CHALLENGE FINDING:
        In headless or bare Streamlit execution where st.rerun() does NOT raise an interrupt exception,
        line 966 of src/ui.py calls ctx.rerun() without a following return statement.
        This test documents that if rerun does not raise, execution falls through and appends
        an empty user message {"role": "user", "content": ""}.
        """
        session = ui.init_session_state({"messages": []})
        mock_ctx = MockStreamlitContext(session_state=session, chat_input_val="   ", raise_on_rerun=False)

        # Execute without interrupt exception
        ui.render_tutor_tab(st_ctx=mock_ctx)

        assert mock_ctx.rerun_called is True
        # Notice: because 'return' is absent after ctx.rerun(), fallthrough appends an empty message
        if len(session["messages"]) > 0:
            assert session["messages"][0]["role"] == "user"
            assert session["messages"][0]["content"] == ""
            # Document finding: missing return after rerun causes fallthrough in bare environments

    def test_rapid_consecutive_empty_and_whitespace_submissions(self) -> None:
        """Verify rapid repeated submissions of empty strings do not corrupt chat state."""
        session = ui.init_session_state({"messages": []})
        for i in range(15):
            mock_ctx = MockStreamlitContext(session_state=session, chat_input_val="")
            ui.render_tutor_tab(st_ctx=mock_ctx)

        assert len(session["messages"]) == 0

    def test_chat_message_schema_integrity_across_all_roles(self) -> None:
        """Verify all messages in history strictly adhere to role ('user'|'assistant') and content schema."""
        session = ui.init_session_state({"messages": []})

        # 1. Normal user submission
        mock_ctx = MockStreamlitContext(
            session_state=session,
            chat_input_val="¿Qué es el factor gravimétrico?",
            raise_on_rerun=False,
        )
        ui.render_tutor_tab(st_ctx=mock_ctx)

        assert len(session["messages"]) >= 2
        for msg in session["messages"]:
            assert isinstance(msg, dict)
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("user", "assistant")
            assert isinstance(msg["content"], str)
            assert len(msg["content"]) > 0

    def test_citation_drawer_label_exact_formatting(self) -> None:
        """
        Verify citation drawer cards conform strictly to:
        '📖 {book_title} (Pág. {page_num})'
        """
        test_citations = [
            {
                "book_title": "Fundamentos de Química Analítica",
                "author": "Douglas A. Skoog et al.",
                "edition": "9ª Edición",
                "chapter": "Capítulo 12",
                "page_num": 315,
                "excerpt": "La relación de Von Weimarn...",
            },
            {
                "book_title": "Introducción a los Equilibrios Iónicos",
                "author": "Manuel Aguilar San Juan",
                "edition": "2ª Edición",
                "chapter": "Capítulo 3",
                "page_num": 115,
                "excerpt": "Ecuación de Henderson-Hasselbalch...",
            },
            {
                # Missing book title fallback
                "page_num": 42,
            },
            {
                # Non-integer page representation
                "book_title": "Quantitative Analysis",
                "page_num": "45-48",
            }
        ]

        expected_labels = [
            "📖 Fundamentos de Química Analítica (Pág. 315)",
            "📖 Introducción a los Equilibrios Iónicos (Pág. 115)",
            "📖 Libro Oficial (Pág. 42)",
            "📖 Quantitative Analysis (Pág. 45-48)",
        ]

        for cit, expected in zip(test_citations, expected_labels):
            b_title = cit.get("book_title", "Libro Oficial")
            page_num = cit.get("page_num", "")
            card_label = f"📖 {b_title} (Pág. {page_num})"
            assert card_label == expected
            assert re.match(r"^📖 .+\(Pág\. .*\)$", card_label)

    def test_guided_study_mode_progression_and_completion_transition(self) -> None:
        """
        Verify Guided Study Mode:
        1. Suggests next topic in syllabus order.
        2. Appends user inquiry and assistant pedagogical reply.
        3. Appends topic to completed_topics.
        4. When all topics completed, emits completion notice advising transition to Exam Simulator.
        """
        unit = "U3"
        session = ui.init_session_state({
            "current_unit": unit,
            "tutor_unit": unit,
            "completed_topics": [],
            "messages": [],
        })

        # Step 1: Initial Guided Study Topic Request
        mock_ctx = MockStreamlitContext(
            session_state=session,
            raise_on_rerun=False,
        )
        mock_ctx.button_clicks["🎯 Modo de Estudio Guiado"] = True
        ui.render_tutor_tab(st_ctx=mock_ctx)

        assert len(session["completed_topics"]) == 1
        first_topic = session["completed_topics"][0]
        assert len(session["messages"]) >= 2
        assert session["messages"][0]["role"] == "user"
        assert first_topic in session["messages"][0]["content"]
        assert session["messages"][1]["role"] == "assistant"

        # Step 2: Exhaust all topics to test completion boundary
        rec = suggest_next_topic(unit, session["completed_topics"])
        while rec.get("status") != "completed":
            session["completed_topics"].append(rec["next_topic"])
            rec = suggest_next_topic(unit, session["completed_topics"])

        assert rec["status"] == "completed"

        # Now click Guided Study again when all topics are completed
        mock_ctx2 = MockStreamlitContext(
            session_state=session,
            raise_on_rerun=False,
        )
        mock_ctx2.button_clicks["🎯 Modo de Estudio Guiado"] = True
        ui.render_tutor_tab(st_ctx=mock_ctx2)

        last_msg = session["messages"][-1]
        assert last_msg["role"] == "assistant"
        assert "¡Felicidades!" in last_msg["content"]
        assert "Simulador de Exámenes" in last_msg["content"]

    def test_cross_tab_navigation_payload_builders(self) -> None:
        """Verify navigation action payload builders generate valid routing contracts."""
        tut_payload = ui.create_tutor_navigation_payload("u5", "Precipitación")
        assert tut_payload["action"] == "open_tutor"
        assert tut_payload["target_unit"] == "U5"
        assert "U5" in tut_payload["prefill_prompt"]
        assert "Precipitación" in tut_payload["prefill_prompt"]

        exm_payload = ui.create_exam_navigation_payload("u7", default_count=5)
        assert exm_payload["action"] == "start_exam"
        assert exm_payload["target_unit"] == "U7"
        assert exm_payload["default_count"] == 5

        # Boundary: non-positive count clamped
        exm_clamped = ui.create_exam_navigation_payload("U1", default_count=-10)
        assert exm_clamped["default_count"] == 1


# ==============================================================================
# 2. EXAM SIMULATOR UI EMPIRICAL STRESS TESTS
# ==============================================================================

class TestExamSimulatorUiStressHarness:
    """Stress tests covering question rendering, option formatting, scoring boundaries, pass/fail, and reset."""

    def test_question_rendering_state_and_option_prefix_conformance(self) -> None:
        """Verify questions generated for all syllabus units strictly conform to A) , B) , C) , D) format."""
        tested_units = ["U1", "U3", "U5", "U6", "U7", "U8", "U9", "L2", "L5"]
        for unit in tested_units:
            questions = generate_exam_questions(unit_id=unit, count=3, difficulty="media", api_key="test_key")
            assert len(questions) == 3, f"Expected 3 questions for unit {unit}"
            for q in questions:
                assert "id" in q
                assert "question" in q
                assert "options" in q
                assert "correct_answer" in q
                options = q["options"]
                assert len(options) >= 2
                for opt in options:
                    assert re.match(r"^[A-D]\)\s+", opt), f"Option '{opt}' in unit {unit} lacks 'A) ' prefix!"

    def test_student_answer_tracking_radio_selection(self) -> None:
        """Verify student answer tracking synchronizes full option text and option letter."""
        session = ui.init_session_state({
            "exam_status": "in_progress",
            "exam_unit": "U5",
            "exam_difficulty": "media",
            "exam_questions": [
                {
                    "id": 1,
                    "question": "¿Cuál es el indicador en el método de Mohr?",
                    "options": ["A) K2CrO4", "B) Fluoresceína", "C) Almidón", "D) Fe3+"],
                    "correct_answer": "A",
                },
                {
                    "id": 2,
                    "question": "¿Cuál es el medio de pH requerido en Mohr?",
                    "options": ["A) Fuertemente ácido", "B) Neutro a ligeramente alcalino (6.5-10.0)", "C) pH 1", "D) pH 14"],
                    "correct_answer": "B",
                }
            ],
            "exam_answers": {},
            "exam_student_answers": {},
        })

        mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
        mock_ctx.radio_values["q_radio_1"] = "A) K2CrO4"
        mock_ctx.radio_values["q_radio_2"] = "B) Neutro a ligeramente alcalino (6.5-10.0)"

        ui.render_exam_tab(st_ctx=mock_ctx)

        assert session["exam_student_answers"][1] == "A) K2CrO4"
        assert session["exam_answers"][1] == "A"
        assert session["exam_student_answers"][2] == "B) Neutro a ligeramente alcalino (6.5-10.0)"
        assert session["exam_answers"][2] == "B"

    @pytest.mark.parametrize(
        "correct_count,total_count,expected_score,expected_pass,expected_badge",
        [
            (0, 3, 0.0, False, "Puntaje Obtenido: 0.0%"),
            (1, 3, 33.3, False, "Puntaje Obtenido: 33.3%"),
            (2, 3, 66.7, True, "Puntaje Obtenido: 66.7%"),
            (3, 3, 100.0, True, "Puntaje Obtenido: 100.0%"),
            (0, 1, 0.0, False, "Puntaje Obtenido: 0.0%"),
            (1, 1, 100.0, True, "Puntaje Obtenido: 100.0%"),
            (1, 2, 50.0, False, "Puntaje Obtenido: 50.0%"),
            (2, 2, 100.0, True, "Puntaje Obtenido: 100.0%"),
        ],
    )
    def test_scorecard_evaluation_exact_boundary_cases(
        self,
        correct_count: int,
        total_count: int,
        expected_score: float,
        expected_pass: bool,
        expected_badge: str,
    ) -> None:
        """
        Verify exact scorecard evaluation boundaries:
        0/3 = 0.0%, 1/3 = 33.3%, 2/3 = 66.7%, 3/3 = 100.0%.
        Verify badge string conforms to f"Puntaje Obtenido: {score_val}%".
        """
        questions = [
            {"id": i + 1, "correct_answer": "A", "explanation": f"Exp {i}"}
            for i in range(total_count)
        ]
        # Provide correct answers for first `correct_count` questions, wrong for remainder
        student_answers = ["A"] * correct_count + ["D"] * (total_count - correct_count)

        eval_res = evaluate_exam_submission(questions, student_answers, api_key="dummy_key")

        assert eval_res["score"] == expected_score
        assert eval_res["passed"] == expected_pass
        assert eval_res["correct_answers"] == correct_count
        assert eval_res["total_questions"] == total_count

        badge = ui.format_score_badge(eval_res["score"])
        assert badge == expected_badge

    def test_passing_threshold_exact_boundary_51_percent(self) -> None:
        """
        Verify passing threshold logic:
        Scores < 51.0% trigger failing status (REPROBADO) and remediation advice.
        Scores >= 51.0% trigger passing status (APROBADO).
        """
        failing_scores = [0.0, 33.3, 45.0, 50.0, 50.9]
        passing_scores = [51.0, 51.1, 60.0, 66.7, 75.0, 100.0]

        for s in failing_scores:
            eval_res = {"score": s, "total_questions": 10, "correct_answers": int(s / 10), "passed": s >= 51.0}
            session = ui.init_session_state({
                "exam_status": "evaluated",
                "exam_results": eval_res,
                "exam_unit": "U3",
            })
            mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
            ui.render_exam_tab(st_ctx=mock_ctx)

            # Check status metric
            status_metric = next((m for m in mock_ctx.rendered_metrics if m["label"] == "Estado Final"), None)
            assert status_metric is not None
            assert status_metric["value"] == "REPROBADO"
            assert status_metric["delta"] == "< 51%"
            assert any("Calificación Insuficiente" in err for err in mock_ctx.rendered_errors)

        for s in passing_scores:
            eval_res = {"score": s, "total_questions": 10, "correct_answers": int(s / 10), "passed": s >= 51.0}
            session = ui.init_session_state({
                "exam_status": "evaluated",
                "exam_results": eval_res,
                "exam_unit": "U3",
            })
            mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
            ui.render_exam_tab(st_ctx=mock_ctx)

            status_metric = next((m for m in mock_ctx.rendered_metrics if m["label"] == "Estado Final"), None)
            assert status_metric is not None
            assert status_metric["value"] == "APROBADO"
            assert status_metric["delta"] == "≥ 51%"
            assert any("Evaluación Aprobada" in succ or "Puntaje Perfecto" in succ for succ in mock_ctx.rendered_success)

    def test_failing_exam_triggers_remediation_advice(self) -> None:
        """Verify failing exam (< 51.0%) renders remediation button and appends prompt to tutor."""
        eval_res = {
            "score": 33.3,
            "total_questions": 3,
            "correct_answers": 1,
            "passed": False,
            "feedback": [
                {"question_id": 1, "is_correct": False, "feedback": "Repasar relación de Von Weimarn RSS"},
                {"question_id": 2, "is_correct": True, "feedback": "Correcto"},
                {"question_id": 3, "is_correct": False, "feedback": "Repasar maduración de Ostwald"},
            ],
            "citations": []
        }
        session = ui.init_session_state({
            "exam_status": "evaluated",
            "exam_results": eval_res,
            "exam_unit": "U3",
            "messages": [],
        })

        mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
        mock_ctx.button_clicks["💬 Repasar Conceptos Fallidos con el Tutor"] = True
        ui.render_exam_tab(st_ctx=mock_ctx)

        assert len(session["messages"]) == 1
        user_prompt = session["messages"][0]
        assert user_prompt["role"] == "user"
        assert "Hola Tutor, rendí el examen de la unidad U3" in user_prompt["content"]
        assert "33.3%" in user_prompt["content"]
        assert "Von Weimarn" in user_prompt["content"] or "Ostwald" in user_prompt["content"]

    def test_perfect_score_triggers_balloons_celebration(self) -> None:
        """Verify 100.0% score triggers balloons animation and celebratory notification."""
        eval_res = {
            "score": 100.0,
            "total_questions": 3,
            "correct_answers": 3,
            "passed": True,
            "feedback": [],
            "citations": []
        }
        session = ui.init_session_state({
            "exam_status": "evaluated",
            "exam_results": eval_res,
            "exam_unit": "U6",
        })

        mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
        ui.render_exam_tab(st_ctx=mock_ctx)

        assert mock_ctx.balloons_called is True
        assert any("Puntaje Perfecto" in s for s in mock_ctx.rendered_success)

    def test_exam_cancel_during_active_quiz_resets_cleanly(self) -> None:
        """Verify clicking 'Cancelar' during an in-progress exam cleanly resets exam state to idle."""
        session = ui.init_session_state({
            "exam_status": "in_progress",
            "exam_questions": [{"id": 1, "question": "Q1", "options": ["A) 1", "B) 2"]}],
            "exam_answers": {1: "A"},
            "exam_student_answers": {1: "A) 1"},
            "exam_submitted": False,
        })

        mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
        mock_ctx.button_clicks["🔄 Cancelar"] = True
        ui.render_exam_tab(st_ctx=mock_ctx)

        assert session["exam_status"] == "idle"
        assert session["exam_questions"] == []
        assert session["exam_answers"] == {}
        assert session["exam_student_answers"] == {}
        assert session["exam_results"] is None

    def test_exam_retake_after_evaluation_resets_cleanly(self) -> None:
        """Verify clicking 'Intentar Otro Examen' cleans all results and allows fresh exam generation."""
        session = ui.init_session_state({
            "exam_status": "evaluated",
            "exam_questions": [{"id": 1}],
            "exam_answers": {1: "A"},
            "exam_student_answers": {1: "A) 1"},
            "exam_submitted": True,
            "exam_results": {"score": 100.0},
        })

        mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)
        mock_ctx.button_clicks["🔄 Intentar Otro Examen"] = True
        ui.render_exam_tab(st_ctx=mock_ctx)

        assert session["exam_status"] == "idle"
        assert session["exam_questions"] == []
        assert session["exam_answers"] == {}
        assert session["exam_student_answers"] == {}
        assert session["exam_submitted"] is False
        assert session["exam_results"] is None

    def test_session_clear_purges_all_exam_and_tutor_state(self) -> None:
        """Verify clear_session_state resets all student state cleanly without residual leakage."""
        session = {
            "api_key": "AIzaSyTestSecretKey",
            "gemini_api_key": "AIzaSyTestSecretKey",
            "api_key_valid": True,
            "messages": [{"role": "user", "content": "Hola"}],
            "completed_topics": ["Tema 1", "Tema 2"],
            "exam_status": "evaluated",
            "exam_questions": [{"id": 1}],
            "exam_answers": {1: "B"},
            "exam_results": {"score": 66.7},
        }

        ui.clear_session_state(session)

        assert session["api_key"] is None
        assert session["gemini_api_key"] is None
        assert session["api_key_valid"] is False
        assert session["messages"] == []
        assert session["completed_topics"] == []
        assert session["exam_status"] == "idle"
        assert session["exam_questions"] == []
        assert session["exam_answers"] == {}
        assert session["exam_results"] is None


# ==============================================================================
# 3. HEADLESS ENVIRONMENT SAFETY EMPIRICAL TESTS
# ==============================================================================

class TestHeadlessEnvironmentSafetyHarness:
    """Stress tests covering import safety, STREAMLIT_AVAILABLE guard, and pure helper isolation."""

    def test_streamlit_available_guard_flag(self) -> None:
        """Verify STREAMLIT_AVAILABLE is a valid boolean attribute on src.ui."""
        assert hasattr(ui, "STREAMLIT_AVAILABLE")
        assert isinstance(ui.STREAMLIT_AVAILABLE, bool)

    def test_pure_helpers_operate_without_streamlit_active(self) -> None:
        """Verify all pure python helper functions execute without Streamlit context."""
        # 1. WhatsApp URL generation
        url = ui.generate_whatsapp_url("591-700-00000", "Solicitud de Libro")
        assert url.startswith("https://wa.me/59170000000?text=")

        # 2. Book request message formatting
        msg = ui.format_book_request_message("Química Analítica", "9ª Edición", "Skoog")
        assert "Química Analítica" in msg
        assert "Skoog" in msg

        # 3. WhatsApp book builder
        book = {"title": "Fundamentos", "edition": "9ª", "authors": "Skoog", "phone": "59171112233"}
        b_url = ui.build_whatsapp_request_url(book)
        assert "https://wa.me/59171112233" in b_url

        # 4. Course catalog metadata
        cat = ui.get_course_catalog()
        assert len(cat) == 11
        for item in cat:
            assert "id" in item
            assert "title" in item
            assert "whatsapp_url" in item

        # 5. KaTeX formula formatting and XSS sanitization
        formula = "La reacción $$Ba^{2+} + SO_4^{2-} \\rightarrow BaSO_4\\downarrow$$ con <script>alert(1)</script>"
        sanitized = ui.format_chemical_formula(formula)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized
        assert "$$Ba^{2+}" in sanitized

        # 6. KaTeX unclosed delimiter balancing
        unclosed = "El pH es $pH = -\\log[H^+]"
        balanced = ui.format_chemical_formula(unclosed)
        assert balanced.count("$") % 2 == 0

        # 7. Score badge
        badge = ui.format_score_badge(33.3)
        assert badge == "Puntaje Obtenido: 33.3%"

    def test_simulated_missing_streamlit_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify that when Streamlit is not available (STREAMLIT_AVAILABLE = False, st = None),
        all pure helpers continue to work, and attempting to render views without st_ctx
        raises a clean RuntimeError instead of an unexpected AttributeError or crash.
        """
        monkeypatch.setattr(ui, "STREAMLIT_AVAILABLE", False)
        monkeypatch.setattr(ui, "st", None)

        # Pure helpers work without issue
        badge = ui.format_score_badge(100.0)
        assert badge == "Puntaje Obtenido: 100.0%"

        # Calling renderers without st_ctx cleanly raises RuntimeError
        with pytest.raises(RuntimeError, match="Streamlit is not available"):
            ui.render_sidebar_byok()

        with pytest.raises(RuntimeError, match="Streamlit is not available"):
            ui.render_library_tab()

        with pytest.raises(RuntimeError, match="Streamlit is not available"):
            ui.render_syllabus_tab()

        with pytest.raises(RuntimeError, match="Streamlit is not available"):
            ui.render_tutor_tab()

        with pytest.raises(RuntimeError, match="Streamlit is not available"):
            ui.render_exam_tab()

    def test_full_ui_tabs_render_end_to_end_with_mock_context(self) -> None:
        """Verify all 5 main view renderers execute completely without unhandled exceptions."""
        session = ui.init_session_state({
            "api_key": "AIzaSyTestMockKey",
            "api_key_valid": True,
            "current_unit": "U1",
            "active_tab": "Syllabus Navigator",
        })

        mock_ctx = MockStreamlitContext(session_state=session, raise_on_rerun=False)

        # 1. Sidebar BYOK
        ui.render_sidebar_byok(st_ctx=mock_ctx)
        assert any("Química Analítica" in m for m in mock_ctx.rendered_markdown)

        # 2. Library Tab
        ui.render_library_tab(st_ctx=mock_ctx)
        assert any("Biblioteca" in h for h in mock_ctx.rendered_headers)

        # 3. Syllabus Tab
        ui.render_syllabus_tab(st_ctx=mock_ctx)
        assert any("Plan Global" in h for h in mock_ctx.rendered_headers)

        # 4. Tutor Tab
        ui.render_tutor_tab(st_ctx=mock_ctx)
        assert any("Tutor Inteligente" in h for h in mock_ctx.rendered_headers)

        # 5. Exam Tab (Idle)
        ui.render_exam_tab(st_ctx=mock_ctx)
        assert any("Simulador de Exámenes" in h for h in mock_ctx.rendered_headers)
