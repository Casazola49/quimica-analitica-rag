#!/usr/bin/env bash
# run_app.sh - Run Streamlit Web Portal for Química Analítica
set -euo pipefail

PORT="${PORT:-8501}"
HOST="${HOST:-0.0.0.0}"

echo "🧪 Iniciando Portal Educativo de Química Analítica en http://${HOST}:${PORT}..."
exec streamlit run app.py \
    --server.port="${PORT}" \
    --server.address="${HOST}" \
    --server.headless=true \
    --browser.gatherUsageStats=false
