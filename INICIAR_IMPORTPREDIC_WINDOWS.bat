@echo off
chcp 65001 >nul
title ImportPredic
cd /d "%~dp0"

echo ==========================================================
echo   ImportPredic - inicio automatico
echo ==========================================================

REM Cierra copias anteriores de Streamlit que sigan abiertas
taskkill /F /IM streamlit.exe >nul 2>&1

REM Busca Python 3.12 (o el Python disponible)
set "PY=python"
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
%PY% --version >nul 2>&1 || (
  echo No se encontro Python. Instala Python 3.12 desde python.org
  echo y marca la casilla "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [1/3] Creando el entorno virtual...
  %PY% -m venv venv || goto :error
)

if not exist "venv\.instalado" (
  echo [2/3] Instalando dependencias. Solo pasa la primera vez y puede tardar 5 a 10 minutos...
  venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
  venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
  echo ok> venv\.instalado
)

findstr /C:"sk-or-v1-" .streamlit\secrets.toml >nul || (
  echo.
  echo AVISO: no hay API key en .streamlit\secrets.toml
  echo        El asistente de IA estara desactivado; el resto funciona normal.
  echo.
)

echo [3/3] Abriendo ImportPredic en http://localhost:8501
echo        Para cerrarlo, cierra esta ventana o presiona Ctrl + C.
venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Toma una captura de este mensaje.
pause
exit /b 1
