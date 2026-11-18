# -*- coding: utf-8 -*-
"""
src/ai/openrouter_client.py - VERSION 1.6

Correcciones:
- Error 'choices' resuelto: validacion completa de la respuesta antes de acceder
- Fallback mas robusto: espera entre intentos para no saturar el rate limit
- max_tokens reducido a 900 (compatible con limites de modelos gratuitos)
- Manejo de respuestas vacias, malformadas o con error embebido en JSON 200
- Logging de errores mas informativo sin exponer datos sensibles
- FIX (v1.6): filtro anti fuga de razonamiento. Los modelos gratuitos
  pequenos (Gemma 2 9B, etc.) a veces ignoran las reglas del prompt y
  devuelven su "pensamiento en voz alta" en ingles ("Okay, the user is
  asking...", "Let me recall...", "Wait, the rule says...") mezclado
  con la respuesta real. Antes se confiaba unicamente en las
  instrucciones del prompt para evitar esto, lo cual es fragil: si el
  modelo no obedece, el texto crudo (incluyendo el razonamiento en
  ingles) se mostraba directo al usuario. Ahora se limpia la respuesta
  quitando parrafos de razonamiento antes de devolverla, y si despues
  de limpiar no queda una respuesta real en espanol, se trata como
  fallo recuperable para que el fallback automatico pruebe el
  siguiente modelo en vez de mostrar la fuga.
- v2.0: la API key se lee de los secretos del servidor; se agrega
  call_ai_detailed() para saber si la llamada tuvo exito (necesario para
  el limite de uso por usuario) y los errores ya no exponen el cuerpo
  crudo de la respuesta HTTP.
"""

import json
import logging
import re
import time
import urllib.request
import urllib.error

# -----------------------------------------------------------------------
# API KEY
# -----------------------------------------------------------------------
# SEGURIDAD (v2.0): la key YA NO vive en el código fuente. Se lee en el
# servidor desde st.secrets / variable de entorno OPENROUTER_API_KEY
# (ver config/secrets.py). Nunca se envía al navegador ni se muestra en
# la interfaz: el usuario solo ve las respuestas del modelo.
from config.secrets import openrouter_api_key

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# -----------------------------------------------------------------------
# MODELOS GRATUITOS - julio 2026
# -----------------------------------------------------------------------
MODELOS_DISPONIBLES = {
    "Gemma 2 9B  [RECOMENDADO]":      "google/gemma-2-9b-it:free",
    "Mistral 7B":                      "mistralai/mistral-7b-instruct:free",
    "OpenAI GPT-OSS 20B":              "openai/gpt-oss-20b:free",
    "Llama 3.2 3B  [Rapido]":          "meta-llama/llama-3.2-3b-instruct:free",
    "Gemma 4 31B":                     "google/gemma-4-31b-it:free",
    "OpenAI GPT-OSS 120B":             "openai/gpt-oss-120b:free",
    "NVIDIA Nemotron 120B":            "nvidia/nemotron-3-super-120b-a12b:free",
    "Llama 3.3 70B  [NO recomendado - responde en ingles]": "meta-llama/llama-3.3-70b-instruct:free",
    "OpenRouter Auto":                 "openrouter/free",
}
# NOTA: Llama 3.3 70B se deja disponible en el selector mas no como
# recomendado, ya que en pruebas mostro consistentemente razonamiento
# interno en ingles (chain-of-thought) antes de responder, ignorando
# las reglas de idioma del system prompt.

DEFAULT_MODEL = "google/gemma-2-9b-it:free"
# IMPORTANTE: Gemma 2 9B es el modelo principal porque es notablemente
# mas obediente con las instrucciones de idioma y formato. Llama 3.3 70B
# muestra razonamiento interno (chain-of-thought) en ingles ANTES de
# responder, incluso con las reglas anti chain-of-thought en el system
# prompt, por eso se movio al final del fallback, como ultimo recurso.

# Fallback ordenado por obediencia a instrucciones (NO por potencia)
FALLBACK_MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-3.3-70b-instruct:free",  # ultimo recurso: chain-of-thought en ingles
    "openrouter/free",
]

log = logging.getLogger(__name__)

# Tokens maximos — se subio de 1400 a 2200: con el filtro anti fuga de
# razonamiento (ver mas abajo) los modelos pequenos a veces gastan varios
# cientos de tokens "pensando en voz alta" antes de llegar a la respuesta
# real; con el limite anterior, esa respuesta real quedaba cortada a
# mitad de frase antes de que el filtro pudiera siquiera extraerla.
_MAX_TOKENS = 2200

# Pausa entre intentos de fallback (segundos)
_RETRY_WAIT = 1.5


# -----------------------------------------------------------------------
# FILTRO ANTI FUGA DE RAZONAMIENTO
# -----------------------------------------------------------------------
# Frases iniciales tipicas de "pensar en voz alta" en modelos pequenos,
# tanto en ingles como en espanol. Se comparan en minusculas contra el
# inicio de cada parrafo/oracion.
_FRASES_FUGA = (
    "okay,", "okay ", "ok,", "ok let", "let me", "let's", "lets ",
    "i need to", "i should", "i will", "i'll", "i must", "i think",
    "first,", "first i", "so,", "so the", "so let", "given that",
    "the user", "the question", "the context", "therefore, the",
    "but i ", "but the user", "is there any", "as an ai", "also,",
    "wait,", "wait -", "wait i", "wait the", "checking",
    "let me draft", "let me recall", "let me check", "let me think",
    "voy a pensar", "pensemos", "analicemos internamente",
    "el usuario pregunta", "el usuario quiere", "el usuario esta",
    "permitame recordar", "permíteme recordar", "bien, el usuario",
    "el contexto dice", "debo verificar", "espera,", "espera -",
    "revisando el contexto", "recapitulando", "voy a responder",
    "segun el contexto,", "según el contexto,",
)

# Fragmentos que casi siempre son el modelo hablando SOBRE la respuesta
# (metainstrucciones del propio prompt repetidas en voz alta) en vez de
# dar la respuesta en si — sin importar en que idioma aparezcan.
_MARCADORES_META = (
    "word count", "max 320", "320 words", "320 palabras",
    "academic tone", "tono academico", "third person", "tercera persona",
    "must be in spanish", "debe ser en espanol", "as per rule",
    "segun la regla", "según la regla", "rule 5", "regla 5",
    "rule number", "regla numero", "regla número",
)

# Palabras funcionales para estimar si un parrafo esta mayormente en
# ingles (razonamiento filtrado) o en espanol (respuesta real).
_STOP_EN = (
    " the ", " is ", " are ", " and ", " to ", " of ", " that ",
    " this ", " need ", " should ", " user ", " let ", " wait ",
    " but ", " so ", " given ", " therefore ", " i ", " with ",
    " for ", " context ", " answer ", " question ", " must ",
    " be ", " draft ",
)
_STOP_ES = (
    " el ", " la ", " los ", " las ", " que ", " de ", " en ",
    " con ", " para ", " es ", " son ", " esta ", " este ",
    " una ", " un ", " se ", " del ", " por ", " sistema ",
)


def _parrafo_es_fuga(parrafo):
    """True si el parrafo parece razonamiento interno filtrable."""
    texto = parrafo.strip()
    if not texto:
        return True

    bajo = " " + texto.lower() + " "

    for frase in _FRASES_FUGA:
        if bajo.strip().startswith(frase):
            return True

    for marcador in _MARCADORES_META:
        if marcador in bajo:
            return True

    # Fragmentos huerfanos: un parrafo corto que empieza en minuscula
    # casi siempre es el resto de una oracion cortada de razonamiento
    # anterior, no una respuesta real (una respuesta real siempre
    # empieza con mayuscula, tal como pide el prompt).
    if len(texto) < 80 and texto[:1].islower():
        return True

    # Heuristica de idioma: si hay claramente mas marcadores de ingles
    # que de espanol en un parrafo largo, se trata como fuga.
    if len(texto) > 25:
        n_en = sum(bajo.count(s) for s in _STOP_EN)
        n_es = sum(bajo.count(s) for s in _STOP_ES)
        if n_en >= 2 and n_en > n_es:
            return True

    return False


def _limpiar_respuesta(texto):
    """
    Quita parrafos de razonamiento interno filtrado (chain-of-thought)
    de la respuesta del modelo, dejando solo el contenido real en
    espanol. Si no queda nada util despues de filtrar, devuelve "".
    """
    if not texto:
        return ""

    # Separar por parrafos (linea en blanco); si el modelo no usa
    # parrafos, tambien se intenta por saltos de linea simples.
    partes = re.split(r"\n\s*\n", texto.strip())
    if len(partes) == 1:
        partes = texto.strip().split("\n")

    limpio = [p for p in partes if not _parrafo_es_fuga(p)]
    resultado = "\n\n".join(p.strip() for p in limpio if p.strip())
    return resultado.strip()



# -----------------------------------------------------------------------
# MODELOS GRATUITOS DISPONIBLES (consulta en vivo, con cache de 1 hora)
# -----------------------------------------------------------------------
# Los modelos ":free" de OpenRouter cambian con frecuencia. Si un id de la
# lista fija deja de existir, la llamada falla. Por eso se consulta la lista
# publica de modelos y se usan solo los que realmente existen, completando
# con otros modelos gratuitos disponibles.
_MODELS_URL = "https://openrouter.ai/api/v1/models"
_cache_gratis = {"t": 0.0, "ids": []}
_PREFERENCIA = ("gemma", "llama", "mistral", "qwen", "deepseek", "gpt-oss", "nemotron", "phi")


def modelos_gratis_disponibles(timeout=15):
    """Lista de ids ':free' disponibles hoy en OpenRouter ([] si no hay conexion)."""
    if time.time() - _cache_gratis["t"] < 3600 and _cache_gratis["ids"]:
        return _cache_gratis["ids"]
    try:
        req = urllib.request.Request(_MODELS_URL, headers={"User-Agent": "ImportPredic"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8")).get("data", [])
        ids = []
        for m in data:
            mid = m.get("id", "")
            arch = (m.get("architecture") or {})
            salida = arch.get("output_modalities") or ["text"]
            if mid.endswith(":free") and "text" in salida:
                ids.append(mid)
        ids.sort(key=lambda i: next((k for k, p in enumerate(_PREFERENCIA) if p in i), 99))
        _cache_gratis.update(t=time.time(), ids=ids)
        return ids
    except Exception as e:  # sin internet o servicio caido: se usa la lista fija
        log.warning("No se pudo consultar la lista de modelos de OpenRouter: %s", e)
        return []


def call_ai_detailed(messages, model=DEFAULT_MODEL, max_tokens=_MAX_TOKENS, temperature=0.4):
    """
    Llama a OpenRouter con fallback automatico entre modelos.
    Devuelve dict {exito: bool, texto: str, modelo: str | None}.
    """
    api_key = openrouter_api_key()
    if not api_key:
        return {"exito": False, "modelo": None,
                "texto": "El asistente de IA no esta configurado en el servidor."}

    tokens = min(max_tokens, _MAX_TOKENS)
    if model not in MODELOS_DISPONIBLES.values():
        model = DEFAULT_MODEL  # nunca se envia un id de modelo arbitrario
    modelos = [model] + [m for m in FALLBACK_MODELS if m != model]
    disponibles = modelos_gratis_disponibles()
    if disponibles:
        # solo modelos que existen hoy, mas hasta 5 gratuitos adicionales
        modelos = [m for m in modelos if m in disponibles or m == "openrouter/free"]
        modelos += [m for m in disponibles if m not in modelos][:5]
    modelos = modelos[:10]
    ultimo_error = "Sin respuesta"

    for i, modelo_actual in enumerate(modelos):
        if i > 0:
            time.sleep(_RETRY_WAIT)

        resultado = _llamar_modelo(messages, modelo_actual, tokens, temperature, api_key)

        if resultado["exito"]:
            return {"exito": True, "texto": resultado["texto"], "modelo": modelo_actual}

        ultimo_error = resultado["error"]
        log.warning("OpenRouter fallo con %s: %s", modelo_actual, ultimo_error)
        # 400 suele indicar un id de modelo invalido: se prueba el siguiente
        if resultado["codigo"] not in [400, 429, 404, 503, 502, 500, -2]:
            break  # error no recuperable (401, conexion...) — no seguir

    return {
        "exito": False, "modelo": None,
        "texto": "No se pudo obtener respuesta del asistente en este momento. {}".format(ultimo_error),
    }


def call_ai(messages, model=DEFAULT_MODEL, max_tokens=_MAX_TOKENS, temperature=0.4):
    """Compatibilidad con la version anterior: devuelve solo el texto."""
    return call_ai_detailed(messages, model, max_tokens, temperature)["texto"]


def _llamar_modelo(messages, model, max_tokens, temperature, api_key):
    """
    Intenta una llamada a un modelo especifico.
    Valida completamente la estructura de la respuesta.
    Retorna dict: {exito, texto, error, codigo}
    """
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        ensure_ascii=True,
    ).encode("utf-8")

    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json; charset=utf-8",
        "HTTP-Referer": "https://importpredic.udi.edu.co",
        "X-Title": "ImportPredic UDI Barrancabermeja",
    }

    try:
        req = urllib.request.Request(
            OPENROUTER_BASE_URL, data=payload, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")

        # Parsear JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "exito": False, "texto": "",
                "error": "Respuesta no es JSON valido",
                "codigo": -2,
            }

        # Verificar si la respuesta contiene un error embebido
        # (algunos modelos devuelven HTTP 200 con error en el cuerpo)
        if "error" in data:
            err_msg = data["error"].get("message", str(data["error"]))
            err_code = data["error"].get("code", -2)
            # Tratar como 429 si el mensaje menciona rate limit
            if "rate" in err_msg.lower() or "limit" in err_msg.lower():
                return {"exito": False, "texto": "", "error": err_msg, "codigo": 429}
            return {"exito": False, "texto": "", "error": err_msg, "codigo": err_code}

        # Verificar que exista el campo 'choices' con contenido valido
        choices = data.get("choices")
        if not choices or not isinstance(choices, list) or len(choices) == 0:
            return {
                "exito": False, "texto": "",
                "error": "Respuesta sin 'choices' validos (modelo sobrecargado o sin respuesta)",
                "codigo": -2,
            }

        # Verificar que el primer choice tenga message y content
        message = choices[0].get("message", {})
        content = message.get("content", "")

        if not content or not content.strip():
            return {
                "exito": False, "texto": "",
                "error": "Respuesta con contenido vacio",
                "codigo": -2,
            }

        # FIX v1.6: limpiar fugas de razonamiento antes de aceptar la
        # respuesta. Si despues de limpiar no queda nada (el modelo
        # solo "penso en voz alta" sin llegar a una respuesta real),
        # se trata como fallo recuperable para que el fallback
        # automatico pruebe el siguiente modelo de la lista.
        texto_limpio = _limpiar_respuesta(content.strip())
        if not texto_limpio:
            return {
                "exito": False, "texto": "",
                "error": "Respuesta descartada por fuga de razonamiento interno",
                "codigo": -2,
            }

        return {
            "exito": True,
            "texto": texto_limpio,
            "error": "",
            "codigo": 200,
        }

    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""

        if e.code in (401, 403):
            log.error("OpenRouter rechazo la API key (HTTP %s). Revisa OPENROUTER_API_KEY.", e.code)
            return {"exito": False, "texto": "", "error": "El servicio de IA rechazo la credencial del servidor.", "codigo": e.code}
        if e.code == 429:
            return {"exito": False, "texto": "", "error": "Limite de solicitudes (429)", "codigo": 429}
        if e.code == 404:
            return {"exito": False, "texto": "", "error": "Modelo no disponible (404)", "codigo": 404}
        if e.code == 503:
            return {"exito": False, "texto": "", "error": "Servicio no disponible (503)", "codigo": 503}

        log.warning("OpenRouter HTTP %s: %s", e.code, body[:300])
        return {
            "exito": False, "texto": "",
            "error": "Error del servicio de IA (HTTP {}).".format(e.code),
            "codigo": e.code,
        }

    except urllib.error.URLError as e:
        log.warning("OpenRouter sin conexion: %s", e.reason)
        return {
            "exito": False, "texto": "",
            "error": "Sin conexion con el servicio de IA.",
            "codigo": 0,
        }

    except Exception:
        log.exception("Error inesperado llamando a OpenRouter")
        return {
            "exito": False, "texto": "",
            "error": "Error inesperado en el servicio de IA.",
            "codigo": -1,
        }


def is_configured():
    """True si la API key esta configurada en el servidor."""
    return openrouter_api_key() is not None


def get_modelos_disponibles():
    return MODELOS_DISPONIBLES


def get_default_model():
    return DEFAULT_MODEL