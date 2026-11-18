"""
config/secrets.py
Lectura centralizada de secretos y configuración sensible.

Orden de prioridad para cada valor:
  1. st.secrets  (.streamlit/secrets.toml en local, o el panel "Secrets"
     de Streamlit Community Cloud en producción)
  2. Variables de entorno del sistema operativo
  3. Archivo .env en la raíz del proyecto (solo desarrollo local)

Reglas de seguridad:
  - Ningún secreto vive en el código fuente ni se muestra en la interfaz.
  - Los archivos .env y secrets.toml están en .gitignore.
  - Si falta APP_SECRET_KEY en producción, la app se niega a arrancar
    en vez de usar un valor por defecto conocido.
"""
from __future__ import annotations

import os
import secrets as _py_secrets
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # python-dotenv es opcional: solo se usa en desarrollo local
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


def _from_streamlit(name: str):
    """Lee st.secrets sin romper si Streamlit no está disponible
    (pruebas unitarias, scripts de consola) o no hay secrets.toml."""
    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        return None
    return None


def get_secret(name: str, default=None):
    value = _from_streamlit(name)
    if value is None or value == "":
        value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def get_bool(name: str, default: bool = False) -> bool:
    value = get_secret(name)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def get_int(name: str, default: int) -> int:
    try:
        return int(get_secret(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Valores concretos usados por la aplicación
# ---------------------------------------------------------------------------
def openrouter_api_key() -> str | None:
    key = get_secret("OPENROUTER_API_KEY")
    if not key or "PEGA_TU_KEY" in str(key) or str(key).startswith("sk-or-v1-xxxx"):
        return None
    return str(key).strip()


def database_url() -> str:
    url = get_secret("DATABASE_URL")
    if url:
        url = str(url)
        # Heroku/Supabase entregan a veces "postgres://", que SQLAlchemy 2 ya no acepta
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        return url
    default_path = BASE_DIR / "data" / "importpredic.db"
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{default_path.as_posix()}"


def is_production() -> bool:
    return str(get_secret("APP_ENV", "development")).lower() in {"production", "prod", "produccion"}


@lru_cache(maxsize=1)
def app_secret_key() -> bytes:
    """Clave usada para firmar (HMAC) los artefactos binarios guardados en
    la base de datos. En desarrollo, si no se define, se genera una y se
    guarda en data/.secret_key para que no cambie entre reinicios."""
    key = get_secret("APP_SECRET_KEY")
    if key:
        return str(key).encode("utf-8")

    if is_production():
        raise RuntimeError(
            "APP_SECRET_KEY no está configurada. Defínela en los secrets del "
            "despliegue antes de arrancar ImportPredic en producción."
        )

    key_file = BASE_DIR / "data" / ".secret_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip().encode("utf-8")
    generated = _py_secrets.token_urlsafe(48)
    key_file.write_text(generated, encoding="utf-8")
    try:
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return generated.encode("utf-8")


def allow_registration() -> bool:
    return get_bool("ALLOW_REGISTRATION", True)


def ai_requests_per_hour() -> int:
    return get_int("AI_MAX_REQUESTS_PER_HOUR", 40)


def session_timeout_minutes() -> int:
    return get_int("SESSION_TIMEOUT_MINUTES", 60)
