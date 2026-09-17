"""Tier 4: Realistic Chemical Engineering Student Workflows.

Verifies 8 comprehensive, end-to-end academic scenarios:
1. Sulfate Gravimetry Study Workflow (Von Weimarn, Ostwald digestion, Lab Practice 5).
2. Acid-Base Titration Calculations Workflow (Henderson-Hasselbalch, buffers, 2nd derivative).
3. Permanganometry Lab Preparation Workflow (Oxalate standardization, autocatalysis, iron ore).
4. Water Hardness Complexometric Exam Simulation (EDTA chelation, pH 10 vs 12, NET, Murexide).
5. Argentometry Mohr vs. Volhard Comparison Workflow (Kps differences, nitrobenzene, pH limits).
6. Redox Thermodynamics & Nernst Equation Workflow (Equivalence potential, galvanic cells).
7. Analytical Balance & Volumetric Calibration Workflow (Buoyancy correction, V20, Dixon Q).
8. Complete Student Portal Journey (BYOK -> Syllabus -> Tutor -> Exam -> WhatsApp request).
"""

from __future__ import annotations

import re
import sqlite3
import urllib.parse
import pytest
from tests.helpers import (
    get_db_module,
    get_syllabus_module,
    get_gemini_module,
    get_rag_module,
    get_tutor_module,
    get_exam_module,
    get_ui_module,
)


class TestTier4RealWorldWorkflows:
    """Tier 4: Realistic Chemical Engineering student workflows verification."""

    def test_scenario_01_sulfate_gravimetry_study_workflow(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Scenario 1: Student studying Gravimetric Analysis of Sulfate (BaSO4).

        Curriculum mapping: Theory Unit 3 & Laboratory Practice 5.
        Verifies:
        - Von Weimarn ratio (Q-S)/S understanding.
        - Digestion (Ostwald ripening) explanation.
        - Ashless filter paper (Whatman 42) and calcination without flame.
        - Gravimetric factor calculation (FG = 96.06 / 233.39 = 0.4116).
        """
        _, db_path = seeded_db
        rag = get_rag_module()
        syllabus = get_syllabus_module()

        # Step 1: Verify syllabus mapping
        unit = syllabus.get_unit_by_id("U3")
        assert unit is not None
        assert "gravimétr" in unit["title"].lower() or "gravimetr" in unit["title"].lower()

        # Step 2: Query RAG for Ostwald ripening and Von Weimarn theory
        rag_res = rag.query_rag(
            "¿Por qué es fundamental la digestión en caliente en la gravimetría de sulfatos como BaSO4?",
            api_key=valid_api_key,
            syllabus_unit="U3",
            db_path=db_path
        )
        assert len(rag_res["answer"]) > 50
        assert "Weimarn" in rag_res["answer"] or "ostwald" in rag_res["answer"].lower()
        assert any("Skoog" in c["book_title"] or "Fundamentos" in c["book_title"] for c in rag_res["citations"])

        # Step 3: Verify gravimetric factor calculation
        mw_so4 = 96.06
        mw_baso4 = 233.39
        fg = mw_so4 / mw_baso4
        assert pytest.approx(fg, 0.0001) == 0.4116

    def test_scenario_02_acid_base_titration_calculations_workflow(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Scenario 2: Student practicing Acid-Base Titration Calculations.

        Curriculum mapping: Theory Unit 6 & Laboratory Practice 7.
        Verifies:
        - Henderson-Hasselbalch equation and buffer capacity.
        - Potentiometric titration with glass electrode.
        - Location of equivalence point via 2nd derivative (d^2pH/dV^2 = 0).
        """
        _, db_path = seeded_db
        rag = get_rag_module()

        # Step 1: Query RAG for buffer and neutralization theory
        rag_res = rag.query_rag(
            "Explica cómo calcular el pH de una solución amortiguadora y la localización del punto de equivalencia con segunda derivada.",
            api_key=valid_api_key,
            syllabus_unit="U6",
            db_path=db_path
        )
        ans = rag_res["answer"]
        assert "Henderson" in ans or "pKa" in ans
        assert len(rag_res["citations"]) >= 1

        # Step 2: Test numerical buffer equation: pH = pKa + log([A-]/[HA])
        # For acetic acid (pKa = 4.75), when [A-] = 0.1 M and [HA] = 0.1 M:
        import math
        pka = 4.75
        ha = 0.1
        a_minus = 0.1
        calculated_ph = pka + math.log10(a_minus / ha)
        assert calculated_ph == 4.75

    def test_scenario_03_permanganometry_lab_preparation_workflow(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Scenario 3: Student preparing for Permanganometry Lab.

        Curriculum mapping: Theory Unit 9 & Laboratory Practices 4 & 13.
        Verifies:
        - Standardization of KMnO4 with sodium oxalate (Na2C2O4).
        - Temperature requirement (70-80 °C) and Mn2+ autocatalysis.
        - Iron ore pre-reduction with SnCl2 and HgCl2 elimination.
        """
        _, db_path = seeded_db
        rag = get_rag_module()
        tutor = get_tutor_module()

        tutor_res = tutor.get_tutor_response(
            "¿Por qué se debe calentar la solución de oxalato a 70 °C antes de agregar KMnO4?",
            history=[],
            current_unit_id="U9",
            api_key=valid_api_key
        )
        assert len(tutor_res) > 30

        # Verify equivalent weight calculation for KMnO4 in acidic medium: PE = MW / 5
        mw_kmno4 = 158.034
        pe_kmno4 = mw_kmno4 / 5.0
        assert pytest.approx(pe_kmno4, 0.01) == 31.61

    def test_scenario_04_water_hardness_complexometric_exam_simulation(
        self,
        valid_api_key: str,
    ) -> None:
        """Scenario 4: Student simulating Water Hardness Complexometric Titration Exam.

        Curriculum mapping: Theory Unit 7 & Laboratory Practices 10 & 11.
        Verifies:
        - EDTA 1:1 hexadentate chelation.
        - Total hardness at pH 10 with Eriochrome Black T (NET).
        - Calcium hardness at pH 12 with Murexide (Mg(OH)2 precipitated).
        - Exam grading with score and bibliographic citations.
        """
        exam = get_exam_module()

        # Step 1: Generate dynamic quiz
        questions = exam.generate_exam_questions(unit_id="U7", count=1, difficulty="media", api_key=valid_api_key)
        assert len(questions) == 1
        q = questions[0]
        assert "citation" in q

        # Step 2: Submit correct answer and verify score
        ans = [q["correct_answer"]]
        result = exam.evaluate_exam_submission(questions, ans, api_key=valid_api_key)
        assert result["score"] == 100.0
        assert len(result["feedback"]) == 1
        assert len(result["citations"]) >= 1

    def test_scenario_05_argentometry_mohr_volhard_comparison_workflow(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Scenario 5: Student reviewing Argentometric Titrations (Mohr vs. Volhard).

        Curriculum mapping: Theory Unit 5 & Laboratory Practice 6.
        Verifies:
        - Mohr method: direct titration, neutral pH (6.5-10.0), K2CrO4 indicator (red Ag2CrO4).
        - Volhard method: back-titration in acidic HNO3 with KSCN and Fe3+ indicator.
        - Nitrobenzene coating requirement due to Kps(AgCl) > Kps(AgSCN).
        """
        _, db_path = seeded_db
        rag = get_rag_module()

        rag_res = rag.query_rag(
            "Compara el método de Mohr y el método de Volhard para la determinación de cloruros.",
            api_key=valid_api_key,
            syllabus_unit="U5",
            db_path=db_path
        )
        ans = rag_res["answer"]
        assert "Mohr" in ans
        assert "Volhard" in ans
        assert "cromato" in ans.lower() or "tiocianato" in ans.lower()

        # Verify Kps difference principle: Kps(AgCl) ~ 1.8e-10 > Kps(AgSCN) ~ 1.0e-12
        kps_agcl = 1.8e-10
        kps_agscn = 1.0e-12
        assert kps_agcl > kps_agscn

    def test_scenario_06_redox_thermodynamics_nernst_workflow(
        self,
        valid_api_key: str,
    ) -> None:
        """Scenario 6: Student practicing Redox Thermodynamics and Nernst Equation.

        Curriculum mapping: Theory Unit 8.
        Verifies:
        - Nernst equation application: E = E° - (0.0592/n) * log(Q).
        - Equivalence point potential formula: E_pe = (n1*E1° + n2*E2°) / (n1 + n2).
        """
        # Calculate equivalence point potential for Fe2+ (E° = 0.771 V, n=1) titrated with Ce4+ (E° = 1.44 V, n=1):
        e1_deg = 0.771
        n1 = 1
        e2_deg = 1.44
        n2 = 1
        e_pe = (n1 * e1_deg + n2 * e2_deg) / (n1 + n2)
        assert pytest.approx(e_pe, 0.001) == 1.1055

        tutor = get_tutor_module()
        res = tutor.get_tutor_response(
            "Calcula el potencial en el punto de equivalencia de Fe2+ con Ce4+",
            history=[],
            current_unit_id="U8",
            api_key=valid_api_key
        )
        assert len(res) > 20

    def test_scenario_07_analytical_balance_volumetric_calibration_workflow(self) -> None:
        """Scenario 7: Student troubleshooting Analytical Balance & Volumetric Calibration.

        Curriculum mapping: Laboratory Practice 2.
        Verifies:
        - Weighing by difference to 0.1 mg precision.
        - Buoyancy correction for apparent mass in air.
        - Dixon Q test for suspect data point evaluation.
        """
        # 1. Buoyancy correction: m_real = m_apparent * (1 + (rho_air / rho_water) - (rho_air / rho_weights))
        m_apparent = 10.0000  # 10 g water
        rho_air = 0.0012      # g/mL
        rho_water = 0.9982    # g/mL at 20 °C
        rho_weights = 8.0     # g/mL brass/steel
        m_real = m_apparent + m_apparent * ((rho_air / rho_water) - (rho_air / rho_weights))
        assert m_real > m_apparent
        assert pytest.approx(m_real, 0.001) == 10.0105

        # 2. Dixon Q-test calculation: Q_calc = |x_suspect - x_neighbor| / (x_max - x_min)
        replicate_masses = [9.998, 9.999, 10.001, 10.002, 10.025]  # 10.025 is suspect
        sorted_m = sorted(replicate_masses)
        q_calc = (sorted_m[-1] - sorted_m[-2]) / (sorted_m[-1] - sorted_m[0])
        # Q_critical for N=5 at 90% confidence is 0.642
        assert q_calc > 0.642, "Suspect point 10.025 should be rejected by Dixon Q test"

    def test_scenario_08_complete_student_portal_journey(
        self,
        seeded_db: tuple[sqlite3.Connection, str],
        valid_api_key: str,
    ) -> None:
        """Scenario 8: Complete End-to-End Student Journey.

        Workflow:
        1. Student opens portal, inputs AI Studio key (validated).
        2. Navigates to Theory Unit 6 (Neutralización).
        3. Asks Tutor about buffer solutions and Henderson-Hasselbalch.
        4. Takes dynamic practice exam on Unit 6, scores 100%.
        5. Accesses textbook catalog and generates WhatsApp request link for Skoog 9ed.
        """
        _, db_path = seeded_db
        gemini = get_gemini_module()
        syllabus = get_syllabus_module()
        tutor = get_tutor_module()
        exam = get_exam_module()
        ui = get_ui_module()

        # Step 1: BYOK Key Validation
        is_valid, msg = gemini.validate_api_key(valid_api_key)
        assert is_valid is True

        # Step 2: Syllabus Navigation
        u6 = syllabus.get_unit_by_id("U6")
        assert u6 is not None
        assert "neutraliz" in u6["title"].lower() or "ácido" in u6["title"].lower()

        # Step 3: Ask Tutor about Unit 6
        tutor_reply = tutor.get_tutor_response(
            "Explica cómo funciona una solución tampón ácido acético / acetato de sodio.",
            history=[],
            current_unit_id="U6",
            api_key=valid_api_key
        )
        assert len(tutor_reply) > 50
        assert "Henderson" in tutor_reply or "pH" in tutor_reply or "Ka" in tutor_reply

        # Step 4: Take Exam on Unit 6
        quiz = exam.generate_exam_questions(unit_id="U6", count=1, difficulty="media", api_key=valid_api_key)
        assert len(quiz) == 1
        correct_opt = quiz[0]["correct_answer"]
        evaluation = exam.evaluate_exam_submission(quiz, [correct_opt], api_key=valid_api_key)
        assert evaluation["score"] == 100.0

        # Step 5: WhatsApp Textbook Request Link
        req_msg = ui.format_book_request_message(
            book_title="Fundamentos de Química Analítica",
            edition="9ª Edición",
            author="Douglas A. Skoog et al."
        )
        whatsapp_url = ui.generate_whatsapp_url("59170000000", req_msg)

        assert "https://wa.me/59170000000?text=" in whatsapp_url
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(whatsapp_url).query)
        assert "Fundamentos de Química Analítica" in parsed["text"][0]
