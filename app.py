"""
app.py - Main Streamlit Web Application Entry Point.
Portal Educativo y Chatbot RAG para Química Analítica (Código: 2004061).
Licenciatura en Ingeniería Química — Universidad Mayor de San Simón.
"""

from __future__ import annotations

import importlib
import streamlit as st
from src import ui

# Force reload of src.ui to invalidate stale in-memory module cache on Streamlit Cloud
try:
    importlib.reload(ui)
except Exception:
    pass


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

    # Apply dynamic visual design system (Alquímica-33: Sumi-e & Washi) with cache-safe fallback
    if hasattr(ui, "get_theme_css"):
        theme_css = ui.get_theme_css(theme_mode)
    else:
        theme_css = """
        <style>
        #MainMenu {visibility: hidden; display: none !important;}
        header {visibility: hidden; display: none !important;}
        footer {visibility: hidden; display: none !important;}
        .stApp {background-color: #0a0a0a !important; color: #f5f5f5 !important;}
        </style>
        """
    st.markdown(theme_css, unsafe_allow_html=True)

    # Render BYOK Sidebar, Model Settings & Theme Switcher
    ui.render_sidebar_byok(st)

    # Portal Header Banner with Red Sun, Hanko Seal & Japanese Calligraphy
    if hasattr(ui, "render_portal_header"):
        ui.render_portal_header(st, theme_mode)
    else:
        st.title("🧪 Portal Educativo de Química Analítica")
        st.caption("Carrera de Ingeniería Química | Universidad Mayor de San Simón (UMSS) | Código: 2004061")

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
