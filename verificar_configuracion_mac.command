#!/bin/bash
cd "$(dirname "$0")"
[ -x venv/bin/python ] || { echo "Primero abre iniciar_importpredic_mac.command una vez para instalar todo."; read -p "Enter"; exit 1; }
venv/bin/python -m scripts.verificar_configuracion
read -p "Presiona Enter para cerrar"
