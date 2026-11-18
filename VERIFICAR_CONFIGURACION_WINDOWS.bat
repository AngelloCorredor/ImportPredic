@echo off
chcp 65001 >nul
title ImportPredic - verificacion
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Primero abre INICIAR_IMPORTPREDIC_WINDOWS.bat una vez para instalar todo.
  pause
  exit /b 1
)
venv\Scripts\python.exe -m scripts.verificar_configuracion
pause
