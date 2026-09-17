# 📋 Prompt Maestro de Replicación para Materias de Ingeniería Química
## Plantilla Autónoma para Antigravity CLI y `/teamwork-preview`

Utiliza este documento para replicar este mismo sistema para cualquier otra materia de la carrera de **Ingeniería Química** (por ejemplo: *Fisicoquímica*, *Termodinámica*, *Operaciones Unitarias I y II*, *Reactores Químicos*, *Cinética Química*, *Balance de Materia y Energía*, etc.).

---

### 📂 Paso Previo: Preparación de la Carpeta de Trabajo

Antes de lanzar el prompt maestro, en tu nueva carpeta de trabajo crea esta estructura:

```text
nombre_de_materia/
├── books/               <-- Coloca aquí los libros PDF conseguidos de la bibliografía
└── plan_global/         <-- Coloca aquí el PDF del Plan Global / Programa Analítico (y laboratorio si aplica)
```

---

### 💬 Prompt Maestro para Copiar y Pegar

Copia y pega el siguiente bloque directamente en tu sesión de **Antigravity CLI** tras entrar en la carpeta de la nueva materia:

```markdown
/teamwork-preview Quiero construir un portal educativo interactivo y sistema RAG de estudio para la materia de "[NOMBRE_DE_LA_MATERIA]" de la carrera de Ingeniería Química (Semestre [NUMERO_SEMESTRE]), basándome en el plan global y los libros oficiales de la asignatura que he colocado en las carpetas "plan_global/" y "books/".

OBJETIVO GENERAL:
Crear un sistema web completo, de $0 costo de infraestructura/servidor (arquitectura Bring-Your-Own-Key con Google AI Studio), que funcione eficientemente en hardware modesto (consumo de RAM < 100 MB), que indexe los textos oficiales y permita a los estudiantes realizar consultas con citas exactas (libro, autor, edición, capítulo y página), recibir tutoría pedagógica paso a paso guiada por el plan analítico, autoevaluarse con un simulador dinámico de exámenes, y acceder a los libros con portadas y enlaces directos a WhatsApp.

FASE 1: ORGANIZACIÓN Y RENOMBRADO DE LIBROS
- Inspecciona los archivos PDF en "books/" y en "plan_global/".
- Renombra los libros en "books/" con una nomenclatura estándar y limpia:
  `[Autor]_[Titulo_Corto]_[Edicion]ed_[ES/EN].pdf`
- Detecta y elimina archivos duplicados idénticos si existen.
- Extrae la portada de cada libro a "assets/covers/" en formato PNG optimizado.

FASE 2: INGESTA LIGERA Y MAPEO CURRICULAR (R1)
- Extrae el texto de los libros de forma delimitada en memoria (streaming / chunks de páginas) sin cargar libros enteros a RAM (evitar sobrepasar 2 GB de RAM, idealmente < 100 MB RSS).
- Parsea el Plan Global (teoría y laboratorio si son complementarios) identificando todas las Unidades Temáticas y Prácticas.
- Crea una base de datos local SQLite con FTS5 BM25 en "data/[materia].db" indexando los fragmentos con metadatos rigurosos: ID de unidad curricular, título de la unidad, libro fuente, autor, edición, capítulo, rango de páginas y texto limpio.

FASE 3: CLIENTE GEMINI BYOK CON AUTO-REENRUTAMIENTO (R2)
- Implementa un cliente robusto en "src/gemini_client.py" que permita al estudiante ingresar su clave gratuita de Google AI Studio (prefijo AIzaSy) almacenada solo en su sesión de navegador.
- Modelo principal: Priorizar modelos Flash Lite ("gemini-2.5-flash-lite", "gemini-2.0-flash-lite") por su alta cuota gratuita, rapidez y bajo consumo de tokens.
- Cadena de Reenrutamiento Dinámico (Auto-Fallback): Si el modelo principal llega al límite de cuota temporal (HTTP 429), reenrutar de forma transparente al siguiente modelo de la cadena:
  gemini-2.5-flash-lite -> gemini-2.0-flash-lite -> gemini-2.5-flash -> gemini-2.0-flash -> gemini-1.5-flash -> gemini-1.5-flash-8b.
- Validación instantánea de clave con insignia visual y enlace a https://aistudio.google.com/app/apikey para usuarios sin clave.

FASE 4: MOTOR RAG, TUTOR CURRICULAR Y SIMULADOR DE EXÁMENES (R3)
- Motor RAG ("src/rag.py"): Recuperación por BM25 sobre SQLite FTS5 filtrando o priorizando por unidad curricular. Toda respuesta debe fundamentarse y citar obligatoriamente la fuente exacta: [Libro, Autor, Edición, Cap., Pág.]. Soporte para fórmulas matemáticas y químicas en KaTeX/LaTeX.
- Tutor Inteligente ("src/tutor.py"): Guía interactiva que explica los temas en orden pedagógico según el temario analítico.
- Simulador Dinámico de Exámenes ("src/exam.py"): Genera preguntas de opción múltiple con justificación para cualquier unidad seleccionada, califica en tiempo real y ofrece retroalimentación personalizada de puntos débiles.

FASE 5: PORTAL WEB Y CATÁLOGO CON WHATSAPP (R4)
- Aplicación web responsive en Streamlit ("app.py" y "src/ui.py") con 4 pestañas:
  1. Temario y Navegador del Plan Global.
  2. Chat de Tutoría RAG con citas exactas.
  3. Simulador Dinámico de Exámenes y Evaluación.
  4. Catálogo de Libros con portadas, metadatos y botón de 1 clic a WhatsApp (enlace wa.me con mensaje predeterminado codificado para solicitar el libro).
- Script de ejecución inmediata "run_app.sh" (`chmod +x run_app.sh`).

FASE 6: VERIFICACIÓN Y REPRODUCIBILIDAD (R5)
- Suite completa de pruebas automatizadas en "tests/" (Feature isolation, Boundary cases, Pairwise combinations, Student workflows y Adversarial tests) verificables con un ejecutor único `python3 tests/run_e2e_tests.py`.
- Documento "REPLICATION_GUIDE.md" detallando dependencias ("requirements.txt", "packages.txt") y pasos para desplegar en Streamlit Cloud o Hugging Face Spaces.
```

---

### 🛠️ Parámetros a Sustituir al Aplicar a Otra Materia

| Variable | Ejemplo 1 (Fisicoquímica) | Ejemplo 2 (Operaciones Unitarias) | Ejemplo 3 (Reactores) |
|---|---|---|---|
| `[NOMBRE_DE_LA_MATERIA]` | Fisicoquímica | Operaciones Unitarias I | Cinética y Reactores Químicos |
| `[NUMERO_SEMESTRE]` | Cuarto Semestre | Sexto Semestre | Séptimo Semestre |
| Libros típicos en `books/` | Castellan, Levine, Atkins | McCabe-Smith, Treybal, Coulson | Levenspiel, Fogler, Smith |
| Planes en `plan_global/` | Fisicoquímica teoría + laboratorio | Op. Unitarias teoría + laboratorio | Reactores teoría |

---

### 🌐 Opciones de Despliegue en la Web (100% Gratuitas)

Una vez completado el proyecto por los agentes, para que los estudiantes lo usen en internet sin costo:

#### Opción A: Streamlit Community Cloud (Recomendada - 2 minutos)
1. Sube tu carpeta a un repositorio en GitHub (`git init`, `git add .`, `git commit -m "init"`, `git push`).
2. Entra a [share.streamlit.io](https://share.streamlit.io/) con tu cuenta de GitHub.
3. Haz clic en **"New app"**, selecciona el repositorio y define `Main file path: app.py`.
4. Haz clic en **"Deploy"**. En 1 minuto tendrás una URL pública con HTTPS gratuita (`https://tu-materia.streamlit.app`).

#### Opción B: Hugging Face Spaces (Alternativa de alta RAM - 16 GB libres)
1. Crea una cuenta gratuita en [huggingface.co](https://huggingface.co/).
2. Haz clic en **"New Space"**, ponle nombre (ej: `quimica-analitica-portal`), selecciona **Streamlit** como SDK y hardware **Free (2 vCPU, 16 GB RAM)**.
3. Sube los archivos mediante Git o la interfaz web de Hugging Face. Estará en línea inmediatamente.

---
*Archivo generado automáticamente para el proyecto de Ingeniería Química.*
