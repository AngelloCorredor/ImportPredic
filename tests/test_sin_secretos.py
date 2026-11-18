"""Falla si alguien vuelve a pegar una API key en el código fuente."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATRONES = [
    re.compile(r"sk-or-v1-[0-9a-f]{32,}"),      # OpenRouter
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),   # Anthropic
    re.compile(r"sk-[A-Za-z0-9]{40,}"),         # OpenAI (formato clásico)
]
IGNORAR = {".git", "__pycache__", "venv", ".venv", "data"}


def test_no_hay_api_keys_en_el_repositorio():
    hallazgos = []
    for f in ROOT.rglob("*"):
        if not f.is_file() or IGNORAR & set(f.relative_to(ROOT).parts):
            continue
        if f.name in {".env", "secrets.toml"}:
            continue  # están en .gitignore; nunca se versionan
        if f.suffix not in {".py", ".toml", ".md", ".txt", ".example", ".json", ".html", ".js", ".cfg", ".ini", ""}:
            continue
        texto = f.read_text(encoding="utf-8", errors="ignore")
        for p in PATRONES:
            if p.search(texto):
                hallazgos.append(str(f.relative_to(ROOT)))
    assert not hallazgos, f"Posibles API keys en: {hallazgos}"


def test_cliente_ia_sin_key_no_esta_configurado(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from src.ai import openrouter_client as c

    assert c.is_configured() is False
    r = c.call_ai_detailed([{"role": "user", "content": "hola"}])
    assert r["exito"] is False


def test_filtro_de_razonamiento():
    from src.ai.openrouter_client import _limpiar_respuesta

    crudo = "Okay, the user is asking about RMSE.\n\nEl RMSE mide el error cuadrático medio del modelo."
    assert _limpiar_respuesta(crudo) == "El RMSE mide el error cuadrático medio del modelo."
