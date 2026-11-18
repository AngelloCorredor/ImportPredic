"""
scripts/verificar_configuracion.py
Revisa en segundos que ImportPredic esté bien configurado:
librerías, API key de OpenRouter, modelos gratuitos, base de datos y clave
de firma. No modifica nada.

    python -m scripts.verificar_configuracion
"""
import importlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

OK, MAL, AVISO = "[ OK ]", "[FALLA]", "[AVISO]"
problemas = []


def linea(estado, texto, solucion=None):
    print(f"{estado} {texto}")
    if solucion:
        print(f"        -> {solucion}")
        if estado == MAL:
            problemas.append(solucion)


print("=" * 64)
print(" VERIFICACIÓN DE CONFIGURACIÓN - ImportPredic")
print("=" * 64)

# 1. Python
v = sys.version_info
if (3, 10) <= (v.major, v.minor) <= (3, 13):
    linea(OK, f"Python {v.major}.{v.minor}.{v.micro}")
else:
    linea(MAL, f"Python {v.major}.{v.minor} no es compatible", "Instala Python 3.12 desde python.org")

# 2. Librerías
print("\n-- Librerías")
fijas = {}
for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
    if "==" in l and not l.startswith("#"):
        n, ver = l.split("#")[0].strip().split("==")
        fijas[n.lower()] = ver
modulo = {"scikit-learn": "sklearn", "sqlalchemy": "sqlalchemy", "psycopg2-binary": "psycopg2", "fpdf2": "fpdf",
          "pillow": "PIL", "python-dotenv": "dotenv"}
faltan = []
for paquete in fijas:
    try:
        importlib.import_module(modulo.get(paquete, paquete.replace("-", "_")))
    except Exception:
        faltan.append(paquete)
if faltan:
    linea(MAL, "Faltan librerías: " + ", ".join(faltan),
          "Borra el archivo venv\\.instalado y vuelve a abrir INICIAR_IMPORTPREDIC_WINDOWS.bat")
else:
    linea(OK, f"Las {len(fijas)} librerías necesarias están instaladas")

# 3. Secretos
print("\n-- API key del asistente de IA")
secrets_path = ROOT / ".streamlit" / "secrets.toml"
cfg = {}
try:
    import tomllib
    cfg = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
except FileNotFoundError:
    linea(MAL, "No existe .streamlit/secrets.toml", "Copia .streamlit/secrets.toml.example como secrets.toml")
except Exception as e:
    linea(MAL, f"secrets.toml tiene un error de formato: {e}",
          "Revisa que los valores estén entre comillas rectas \"...\" (no uses Word ni TextEdit)")

key = str(cfg.get("OPENROUTER_API_KEY", "") or "").strip()
if (ROOT / ".env").exists():
    linea(AVISO, "Existe un archivo .env; la app podría tomar de ahí una key vieja",
          "Borra el archivo .env y deja la key solo en .streamlit/secrets.toml")
if not key:
    linea(MAL, "No hay API key en .streamlit/secrets.toml (el asistente de IA estará apagado)",
          "Crea una key en https://openrouter.ai/keys y pégala en OPENROUTER_API_KEY = \"...\"")
elif not key.startswith("sk-or-"):
    linea(MAL, "La key no parece de OpenRouter (debe empezar por sk-or-)", "Copia la key completa desde openrouter.ai/keys")
else:
    linea(OK, f"Key encontrada: {key[:12]}…{key[-4:]}")
    for url in ("https://openrouter.ai/api/v1/key", "https://openrouter.ai/api/v1/auth/key"):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=20) as r:
                info = json.loads(r.read().decode()).get("data", {})
            limite = info.get("limit")
            linea(OK, "OpenRouter acepta la key" + (f" (límite: {limite})" if limite is not None else ""))
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            linea(MAL, f"OpenRouter rechazó la key (HTTP {e.code})",
                  "La key fue revocada o está mal copiada: crea una nueva en openrouter.ai/keys")
            break
        except Exception as e:
            linea(AVISO, f"No se pudo contactar a OpenRouter: {e}", "Revisa tu conexión a internet")
            break

    from src.ai.openrouter_client import FALLBACK_MODELS, DEFAULT_MODEL, modelos_gratis_disponibles
    gratis = modelos_gratis_disponibles()
    if gratis:
        configurados = [DEFAULT_MODEL] + FALLBACK_MODELS
        vigentes = [m for m in configurados if m in gratis]
        linea(OK, f"{len(gratis)} modelos gratuitos disponibles hoy; {len(vigentes)} de la lista de la app siguen vigentes")
        if not vigentes:
            linea(AVISO, "Ninguno de los modelos fijos existe ya; la app usará automáticamente: " + ", ".join(gratis[:3]))
    # prueba real
    from src.ai.openrouter_client import call_ai_detailed
    r = call_ai_detailed([{"role": "user", "content": "Responde solo con esta frase: Conexión correcta."}], max_tokens=80)
    if r["exito"]:
        linea(OK, f"El asistente respondió correctamente (modelo: {r['modelo']})")
    else:
        linea(MAL, "El asistente no respondió: " + r["texto"][:160],
              "Si dice límite (429), espera unos minutos; si dice credencial, cambia la key")

# 4. Base de datos
print("\n-- Base de datos")
try:
    from config.secrets import database_url
    url = database_url()
    from sqlalchemy import func, select
    from src.db.engine import session_scope, get_engine
    from src.db.models import Artefacto, Corrida, Usuario
    eng = get_engine()
    destino = url.split("@")[-1].split("?")[0] if "@" in url else url.replace("sqlite:///", "")
    with session_scope() as s:
        nu = s.scalar(select(func.count(Usuario.id))) or 0
        nc = s.scalar(select(func.count(Corrida.id))) or 0
        admins = [u for (u,) in s.execute(select(Usuario.username).where(Usuario.rol == "admin")).all()]
        art = s.execute(select(Artefacto.contenido, Artefacto.firma).limit(1)).first()
    tipo = "PostgreSQL (nube)" if eng.dialect.name.startswith("postgres") else "SQLite (local)"
    linea(OK, f"Conectado a {tipo}: {destino}")
    linea(OK, f"{nu} usuario(s), {nc} corrida(s)" + (f"; administrador: {', '.join(admins)}" if admins else ""))
    if nu == 0:
        linea(AVISO, "La base está vacía: la primera cuenta que crees en la app será la de administrador")
    if art:
        from config.secrets import app_secret_key
        from src.auth.security import verify_signature
        if verify_signature(art[0], art[1], app_secret_key()):
            linea(OK, "La clave de firma coincide: tus corridas guardadas se pueden abrir")
        else:
            linea(MAL, "Las corridas guardadas fueron firmadas con otra APP_SECRET_KEY",
                  "Usa la misma clave de antes (data/.secret_key o la de secrets.toml) o empieza con una base nueva")
except Exception as e:
    msg = str(e).splitlines()[0][:200]
    linea(MAL, f"No se pudo conectar a la base de datos: {msg}",
          "Revisa DATABASE_URL en secrets.toml (o coméntala con # para usar la base local)")

print("\n" + "=" * 64)
if problemas:
    print(f" Hay {len(problemas)} problema(s) por corregir (ver las flechas -> arriba).")
else:
    print(" Todo está bien configurado. Ya puedes abrir ImportPredic.")
print("=" * 64)
