#!/bin/bash
# ImportPredic - inicio automático (macOS). Doble clic para ejecutar.
cd "$(dirname "$0")"
echo "=========================================================="
echo "  ImportPredic - inicio automático"
echo "=========================================================="
pkill -f "streamlit run app.py" 2>/dev/null

PY=python3
command -v python3.12 >/dev/null && PY=python3.12
if ! command -v $PY >/dev/null; then
  echo "No se encontró Python. Instálalo con: brew install python@3.12"; read -p "Enter para salir"; exit 1
fi

if [ ! -x venv/bin/python ]; then
  echo "[1/3] Creando el entorno virtual..."; $PY -m venv venv || { read -p "Error. Enter para salir"; exit 1; }
fi
if [ ! -f venv/.instalado ]; then
  echo "[2/3] Instalando dependencias (solo la primera vez, 5 a 10 minutos)..."
  venv/bin/python -m pip install --upgrade pip && venv/bin/python -m pip install -r requirements.txt \
    || { echo "Si el error menciona libomp, ejecuta: brew install libomp"; read -p "Enter para salir"; exit 1; }
  touch venv/.instalado
fi
grep -q "sk-or-v1-" .streamlit/secrets.toml || echo "AVISO: no hay API key en .streamlit/secrets.toml; el asistente de IA estará desactivado."
echo "[3/3] Abriendo ImportPredic en http://localhost:8501 (Ctrl + C para cerrar)"
venv/bin/python -m streamlit run app.py --server.port 8501
