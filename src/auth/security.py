"""
src/auth/security.py
Primitivas de seguridad sin dependencias externas (solo biblioteca estándar):

- Hash de contraseñas con scrypt (función de derivación resistente a
  ataques por GPU/fuerza bruta; recomendada por OWASP) + sal aleatoria.
- Comparación en tiempo constante para evitar ataques de temporización.
- Política mínima de contraseñas.
- Firma HMAC-SHA256 de los artefactos binarios guardados en la BD.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

# Parámetros scrypt (≈16 MiB de memoria por hash; ~50-100 ms por verificación)
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_PREFIX = "scrypt"

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN
    )
    return "{}${}${}${}${}${}".format(
        _PREFIX, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P,
        base64.b64encode(salt).decode(), base64.b64encode(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        prefix, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if prefix != _PREFIX:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# Hash ficticio para igualar el tiempo de respuesta cuando el usuario no existe
# (así no se puede averiguar qué usuarios existen midiendo tiempos).
_DUMMY_HASH = hash_password(secrets.token_urlsafe(12))


def burn_time(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def validate_password_policy(password: str, username: str = "") -> list[str]:
    """Devuelve la lista de problemas (vacía si la contraseña es aceptable)."""
    problemas = []
    if len(password) < 8:
        problemas.append("Debe tener al menos 8 caracteres.")
    if len(password) > 128:
        problemas.append("No puede tener más de 128 caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", password):
        problemas.append("Debe incluir al menos una letra.")
    if not re.search(r"\d", password):
        problemas.append("Debe incluir al menos un número.")
    if username and username.lower() in password.lower():
        problemas.append("No debe contener el nombre de usuario.")
    if password.lower() in {"12345678", "password", "contraseña", "importpredic", "qwerty123"}:
        problemas.append("Es una contraseña demasiado común.")
    return problemas


def validate_username(username: str) -> str | None:
    if not USERNAME_RE.match(username or ""):
        return "El usuario debe tener 3-30 caracteres: letras, números, punto, guion o guion bajo."
    return None


# ---------------------------------------------------------------------------
# Firma de artefactos
# ---------------------------------------------------------------------------
def sign_bytes(data: bytes, key: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_signature(data: bytes, signature: str, key: bytes) -> bool:
    return hmac.compare_digest(sign_bytes(data, key), signature or "")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
