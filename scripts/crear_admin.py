"""
scripts/crear_admin.py
Crea (o promueve) una cuenta de administrador desde la consola.
Útil cuando ALLOW_REGISTRATION=false o se olvidó la contraseña del admin.

    python -m scripts.crear_admin
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from src.auth import security  # noqa: E402
from src.db import repository as repo  # noqa: E402
from src.db.engine import session_scope  # noqa: E402
from src.db.models import Usuario  # noqa: E402


def main():
    username = input("Usuario: ").strip().lower()
    with session_scope() as s:
        existente = s.scalar(select(Usuario).where(Usuario.username == username))
        if existente:
            pwd = getpass.getpass("Nueva contraseña: ")
            problemas = security.validate_password_policy(pwd, username)
            if problemas:
                sys.exit(" ".join(problemas))
            existente.password_hash = security.hash_password(pwd)
            existente.rol = "admin"
            existente.activo = True
            existente.intentos_fallidos = 0
            existente.bloqueado_hasta = None
            print(f"@{username} ahora es administrador y su contraseña fue restablecida.")
            return
    nombre = input("Nombre completo: ").strip()
    pwd = getpass.getpass("Contraseña: ")
    if pwd != getpass.getpass("Confirmar contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    try:
        repo.crear_usuario(username, nombre, pwd, rol="admin")
    except ValueError as e:
        sys.exit(str(e))
    print(f"Administrador @{username} creado.")


if __name__ == "__main__":
    main()
