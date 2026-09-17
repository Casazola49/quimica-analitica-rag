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

    # Global custom styling for badges, cards, and clean typography
    st.markdown(
        """
        <style>
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .main-header {
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize Ephemeral Client Session State
    ui.init_session_state()

    # Render BYOK Sidebar & Model Settings
    ui.render_sidebar_byok(st)

    # Portal Header Banner
    st.title("🧪 Portal Educativo de Química Analítica")
    st.caption("Carrera de Ingeniería Química | Universidad Mayor de San Simón (UMSS) | Código: 2004061")

    # Multi-Tab Navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 Biblioteca & Libros",
        "📋 Plan de Estudios",
        "💬 Tutor Inteligente",
        "📝 Simulador de Exámenes",
    ])

    with tab1:
        ui.render_library_tab(st)

    with tab2:
        ui.render_syllabus_tab(st)

    with tab3:
        ui.render_tutor_tab(st)

    with tab4:
        ui.render_exam_tab(st)


if __name__ == "__main__":
    main()
