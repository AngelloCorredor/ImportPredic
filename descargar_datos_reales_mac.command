#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x venv/bin/python ]; then echo "Primero abre iniciar_importpredic_mac.command una vez."; read -p "Enter para salir"; exit 1; fi
venv/bin/python -m scripts.descargar_datos_reales
open data/reales 2>/dev/null
read -p "Presiona Enter para cerrar"
