@echo off
chcp 65001 >nul
title ImportPredic - Descarga de datos reales
cd /d "%~dp0"
set "AQUI=%CD%"

REM Busca la carpeta del programa (la que tiene app.py y venv) aqui, arriba o abajo
set "APPDIR="
for %%D in ("%AQUI%" "%AQUI%\.." "%AQUI%\..\.." "%AQUI%\ImportPredic" "%AQUI%\ImportPredic\ImportPredic" "%AQUI%\..\ImportPredic" "%AQUI%\..\ImportPredic\ImportPredic" "%USERPROFILE%\Downloads\ImportPredic\ImportPredic" "%USERPROFILE%\Downloads\ImportPredic" "%USERPROFILE%\Descargas\ImportPredic\ImportPredic" "%USERPROFILE%\Desktop\ImportPredic\ImportPredic" "%USERPROFILE%\Desktop\ImportPredic") do (
  if not defined APPDIR if exist "%%~D\app.py" if exist "%%~D\venv\Scripts\python.exe" set "APPDIR=%%~fD"
)
if not defined APPDIR (
  echo No encontre la carpeta de ImportPredic con el programa ya instalado.
  echo Copia este archivo y la carpeta "scripts" dentro de la carpeta donde esta app.py
  echo y abre antes INICIAR_IMPORTPREDIC_WINDOWS.bat al menos una vez.
  pause
  exit /b 1
)
echo Carpeta del programa: %APPDIR%

REM Si el script quedo en otra carpeta, lo copia a la del programa
if not exist "%APPDIR%\scripts\descargar_datos_reales.py" (
  if exist "%AQUI%\scripts\descargar_datos_reales.py" (
    copy /Y "%AQUI%\scripts\descargar_datos_reales.py" "%APPDIR%\scripts\" >nul
  ) else (
    echo Falta scripts\descargar_datos_reales.py. Descomprime de nuevo Agregar_datos_reales.zip.
    pause
    exit /b 1
  )
)
cd /d "%APPDIR%"
echo Descargando datos reales (DANE / UN Comtrade, Superfinanciera, Banco de la Republica, Banco Mundial)...
echo Tarda entre 1 y 5 minutos. No cierres esta ventana.
echo.
venv\Scripts\python.exe -m scripts.descargar_datos_reales
if exist "data\reales" explorer "data\reales"
echo.
pause
