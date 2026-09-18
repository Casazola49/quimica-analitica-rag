"""
app.py - Main Streamlit Web Application Entry Point.
Portal Educativo y Chatbot RAG para Química Analítica (Código: 2004061).
Licenciatura en Ingeniería Química — Universidad Mayor de San Simón.
"""

from __future__ import annotations

import streamlit as st
from src import ui


def main() -> None:
    """Main web portal entry point."""
    st.set_page_config(
        page_title="Química Analítica — Portal Educativo",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize Ephemeral Client Session State
    ui.init_session_state()

    # Get active visual theme (sumie_dark / washi_light)
    theme_mode = st.session_state.get("theme_mode", "sumie_dark")

    # Apply dynamic visual design system (Alquímica-33: Sumi-e & Washi)
    st.markdown(ui.get_theme_css(theme_mode), unsafe_allow_html=True)

    # Render BYOK Sidebar, Model Settings & Theme Switcher
    ui.render_sidebar_byok(st)

    # Portal Header Banner with Red Sun, Hanko Seal & Japanese Calligraphy
    ui.render_portal_header(st, theme_mode)

    # Multi-Tab Navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 Biblioteca & Libros",
        "📋 Plan de Estudios",
        "💬 Tutor Inteligente",
        "📝 Simulador de Exámenes",
        "🔬 Laboratorio Virtual",
    ])

    with tab1:
        ui.render_library_tab(st)

    with tab2:
        ui.render_syllabus_tab(st)

    with tab3:
        ui.render_tutor_tab(st)

    with tab4:
        ui.render_exam_tab(st)

    with tab5:
        ui.render_simulator_tab(st)



if __name__ == "__main__":
    main()
