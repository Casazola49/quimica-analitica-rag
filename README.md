# ⚛️ Portal Educativo y Tutor RAG de Química Analítica
### Carrera de Ingeniería Química — Teoría y Laboratorio

Portal web interactivo de estudio fundamentado con **Recuperación Aumentada por Generación (RAG)** para estudiantes de Ingeniería Química. Permite realizar consultas bibliográficas exactas (libro, autor, edición, capítulo y número de página), recibir tutoría pedagógica paso a paso, practicar con un simulador dinámico de exámenes y solicitar libros vía WhatsApp.

---

## 🌟 Características Principales

1. **Cero Costo de Infraestructura (BYOK - Bring Your Own Key):**
   - Los estudiantes ingresan su clave de API gratuita de [Google AI Studio](https://aistudio.google.com/app/apikey).
   - El anfitrión paga **$0 de servidores y $0 de tokens**.
2. **Flash Lite y Reenrutamiento Inteligente:**
   - Modelo por defecto: `gemini-2.5-flash-lite` (máxima velocidad y cuota generosa).
   - Reenrutamiento automático en caso de saturación temporal (HTTP 429):
     $$\text{2.5-flash-lite} \longrightarrow \text{2.0-flash-lite} \longrightarrow \text{2.5-flash} \longrightarrow \text{2.0-flash} \longrightarrow \text{1.5-flash}$$
3. **Citas Bibliográficas Exactas:**
   - Recuperación contextual mediante BM25 sobre SQLite FTS5 (23.943 fragmentos indexados).
   - Toda respuesta cita autor, título, edición y número de página del material verificado (Skoog 9ed, Aguilar San Juan 2ed, Day & Underwood 5ed/6ed, Kolthoff Treatise).
4. **Soporte Químico y Matemático KaTeX:**
   - Renderizado claro de equilibrios iónicos, solubilidad ($K_{ps}$), titulaciones y reacciones redox.
5. **Simulador Dinámico de Exámenes:**
   - Cuestionarios dinámicos por unidad temática con evaluación y justificación académica en tiempo real.
6. **Catálogo de Libros y WhatsApp:**
   - Biblioteca con portadas y enlaces directos a WhatsApp para solicitar o acceder a los textos.

---

## 🚀 Inicio Rápido Local

### 1. Requisitos Previos
- Python 3.10 o superior.
- `pip` y herramientas estándar de Linux/Windows/Mac.

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar la Aplicación
```bash
./run_app.sh
# O alternativamente:
streamlit run app.py
```
Abre tu navegador en `http://localhost:8501`.

---

## 🌐 Despliegue en Streamlit Community Cloud (Gratis)

1. Sube este repositorio a tu cuenta de GitHub.
2. Inicia sesión en [share.streamlit.io](https://share.streamlit.io/).
3. Haz clic en **"New app"**, selecciona este repositorio, rama `main`, archivo principal `app.py`.
4. Haz clic en **"Deploy"**.

---

## 📚 Materias Cubiertas y Guía de Replicación
Este repositorio sirve como piloto para la materia de **Química Analítica**. Para replicar esta plataforma en cualquier otra materia de la carrera (Fisicoquímica, Termodinámica, Operaciones Unitarias, etc.), consulta:
- [`PROMPT_MAESTRO_REPLICACION.md`](PROMPT_MAESTRO_REPLICACION.md)
- [`REPLICATION_GUIDE.md`](REPLICATION_GUIDE.md)

---
*Desarrollado para la carrera de Ingeniería Química (UMSS).*
