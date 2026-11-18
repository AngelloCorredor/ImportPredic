"""
scripts/migrar_historial.py
Importa a la base de datos las corridas de la versión anterior
(archivos data/history/*.joblib) y las asigna a un usuario existente.

    python -m scripts.migrar_historial --usuario antony

ADVERTENCIA: los .joblib usan pickle; cargar uno puede ejecutar código.
Ejecuta este script SOLO con archivos generados por tu propia instalación.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib  # noqa: E402
from sqlalchemy import select  # noqa: E402

from src.data.persistence import _SNAPSHOT_KEYS  # noqa: E402
from src.db import repository as repo  # noqa: E402
from src.db.engine import session_scope  # noqa: E402
from src.db.models import Usuario  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usuario", required=True, help="username dueño de las corridas importadas")
    ap.add_argument("--carpeta", default=str(Path(__file__).resolve().parent.parent / "data" / "history"))
    args = ap.parse_args()

    with session_scope() as s:
        uid = s.scalar(select(Usuario.id).where(Usuario.username == args.usuario.lower()))
    if uid is None:
        sys.exit(f"No existe el usuario @{args.usuario}. Créalo primero desde la app.")

    carpeta = Path(args.carpeta)
    index = {}
    if (carpeta / "index.json").exists():
        index = {m["id"]: m for m in json.loads((carpeta / "index.json").read_text(encoding="utf-8"))}

    archivos = sorted(carpeta.glob("snap_*.joblib"))
    if not archivos:
        sys.exit(f"No hay corridas en {carpeta}")
    for f in archivos:
        data = joblib.load(f)
        meta = index.get(f.stem, {})
        nombre = f"Importada {f.stem.replace('snap_', '')}"
        cid = repo.crear_corrida(uid, nombre, origen="Migración v1 (archivo local)")
        repo.guardar_estado_corrida(uid, cid, {k: data.get(k) for k in _SNAPSHOT_KEYS})
        print(f"✓ {f.name} -> corrida #{cid} ({meta.get('mejor_modelo') or 'sin modelo'})")
    print(f"Listo: {len(archivos)} corrida(s) importadas para @{args.usuario}.")


if __name__ == "__main__":
    main()
