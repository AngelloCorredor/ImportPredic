# -*- coding: utf-8 -*-
"""
src/ai/assistant.py
Logica central del asistente IA. Coordina OpenRouter con los prompts.

v2.0:
- El historial de chat se guarda en la base de datos (tabla mensajes_ia),
  por usuario, por pagina y por corrida: al volver a una corrida, su
  conversacion sigue ahi.
- Limite de consultas por usuario y por hora (AI_MAX_REQUESTS_PER_HOUR)
  para proteger el saldo de la API key frente a abuso.
- Las preguntas se validan (longitud maxima) antes de enviarse.
"""

import logging

import streamlit as st

from config.secrets import ai_requests_per_hour
from src.ai.openrouter_client import call_ai_detailed, DEFAULT_MODEL
from src.ai import prompts
from src.auth.session import current_user
from src.db import repository as repo

log = logging.getLogger(__name__)

MAX_PREGUNTA = 1500


def _uid():
    u = current_user()
    return u["id"] if u else None


def _corrida():
    return st.session_state.get("_snapshot_id")


def _chat_key(pagina):
    return "ai_chat_{}_{}".format(pagina, _corrida() or "none")


def cuota_restante():
    uid = _uid()
    if uid is None:
        return 0
    try:
        return max(0, ai_requests_per_hour() - repo.uso_ia_ultima_hora(uid))
    except Exception:
        log.exception("No se pudo consultar la cuota de IA")
        return ai_requests_per_hour()


def _llamar(pagina, tipo, msgs, temperature):
    """Punto unico de salida hacia la API: aplica cuota y registra el uso."""
    uid = _uid()
    if uid is None:
        return "Inicia sesion para usar el asistente."
    if cuota_restante() <= 0:
        return ("Alcanzaste el limite de {} consultas por hora al asistente. "
                "Intenta de nuevo en unos minutos.".format(ai_requests_per_hour()))
    model = st.session_state.get("ai_model", DEFAULT_MODEL)
    r = call_ai_detailed(msgs, model=model, max_tokens=3000, temperature=temperature)
    repo.registrar_uso_ia(uid, pagina, tipo, r.get("modelo") or model, r["exito"])
    return r["texto"]


def init_session(pagina):
    if "ai_model" not in st.session_state:
        st.session_state["ai_model"] = DEFAULT_MODEL


def get_historial(pagina):
    key = _chat_key(pagina)
    if key not in st.session_state:
        uid = _uid()
        try:
            st.session_state[key] = repo.historial_ia(uid, pagina, _corrida()) if uid else []
        except Exception:
            log.exception("No se pudo leer el historial de IA")
            st.session_state[key] = []
    return st.session_state[key]


def add_to_historial(pagina, role, content):
    get_historial(pagina).append({"role": role, "content": content})
    uid = _uid()
    if uid:
        try:
            repo.guardar_mensaje_ia(uid, pagina, role, content, _corrida())
        except Exception:
            log.exception("No se pudo guardar el mensaje de IA")


def clear_historial(pagina):
    st.session_state[_chat_key(pagina)] = []
    uid = _uid()
    if uid:
        repo.borrar_historial_ia(uid, pagina, _corrida())


def generate_auto_analysis(pagina, contexto=None, subtipo=None, force=False):
    """
    Genera el analisis automatico de una pagina.
    subtipo permite seleccionar prompts especificos dentro de la misma pagina
    (ej. "descomposicion", "outliers", "correlaciones" en exploracion).
    Cachea el resultado en session_state para no repetir la llamada.
    """
    # Clave unica por pagina + subtipo
    cache_key = "ai_auto_{}_{}".format(pagina, subtipo or "main")

    if not force and st.session_state.get(cache_key):
        return st.session_state[cache_key]

    ctx = contexto or {}

    # Seleccionar prompt
    if pagina == "inicio":
        msgs = prompts.prompt_inicio_bienvenida()

    elif pagina == "carga":
        msgs = prompts.prompt_carga_analisis(ctx)

    elif pagina == "exploracion":
        if subtipo == "correlaciones":
            msgs = prompts.prompt_eda_correlaciones(ctx)
        elif subtipo == "descomposicion":
            msgs = prompts.prompt_eda_descomposicion(ctx)
        elif subtipo == "outliers":
            msgs = prompts.prompt_eda_outliers(ctx)
        else:
            msgs = prompts.prompt_eda_serie_tiempo(ctx)

    elif pagina == "entrenamiento":
        if subtipo == "residuos":
            msgs = prompts.prompt_entrenamiento_residuos(ctx)
        else:
            msgs = prompts.prompt_entrenamiento_resultado(ctx)

    elif pagina == "prediccion":
        if subtipo == "banda":
            msgs = prompts.prompt_prediccion_banda_confianza(ctx)
        else:
            msgs = prompts.prompt_prediccion_resultado(ctx)

    elif pagina == "evaluacion":
        if subtipo == "estabilidad":
            msgs = prompts.prompt_evaluacion_estabilidad(ctx)
        elif subtipo == "residuos_detalle":
            msgs = prompts.prompt_evaluacion_residuos_detalle(ctx)
        else:
            msgs = prompts.prompt_evaluacion_metricas(ctx)

    elif pagina == "interpretabilidad":
        if subtipo == "waterfall":
            msgs = prompts.prompt_interpretabilidad_waterfall(ctx)
        elif subtipo == "coeficientes":
            msgs = prompts.prompt_interpretabilidad_coeficientes(ctx)
        elif subtipo == "shap_global":
            msgs = prompts.prompt_interpretabilidad_shap(ctx)
        elif subtipo == "shap_summary":
            msgs = prompts.prompt_interpretabilidad_shap_summary(ctx)
        else:
            msgs = prompts.prompt_interpretabilidad_shap(ctx)

    elif pagina == "reporte":
        msgs = prompts.prompt_reporte_resumen(ctx)

    else:
        return "Pagina no reconocida."

    respuesta = _llamar(pagina, "analisis", msgs, 0.35)
    st.session_state[cache_key] = respuesta
    return respuesta


def chat_response(pagina, pregunta, contexto=None):
    """
    Procesa pregunta del usuario, agrega al historial y retorna respuesta.
    """
    ctx = contexto or {}
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return ""
    if len(pregunta) > MAX_PREGUNTA:
        pregunta = pregunta[:MAX_PREGUNTA]
    historial = list(get_historial(pagina))

    if pagina == "inicio":
        msgs = prompts.prompt_inicio_chat(pregunta, historial)
    elif pagina == "carga":
        msgs = prompts.prompt_carga_chat(pregunta, ctx, historial)
    elif pagina == "exploracion":
        # FIX: antes no se pasaba ctx, por lo que el chat de Exploracion
        # nunca tenia acceso a las correlaciones ni a la tendencia reales.
        msgs = prompts.prompt_eda_chat(pregunta, ctx, historial)
    elif pagina == "entrenamiento":
        msgs = prompts.prompt_entrenamiento_chat(pregunta, ctx, historial)
    elif pagina == "prediccion":
        msgs = prompts.prompt_prediccion_chat(pregunta, ctx, historial)
    elif pagina == "evaluacion":
        msgs = prompts.prompt_evaluacion_chat(pregunta, ctx, historial)
    elif pagina == "interpretabilidad":
        msgs = prompts.prompt_interpretabilidad_chat(pregunta, ctx, historial)
    elif pagina == "reporte":
        msgs = prompts.prompt_reporte_chat(pregunta, ctx, historial)
    else:
        msgs = [
            {"role": "system", "content": prompts.SYSTEM_BASE},
            {"role": "user", "content": pregunta},
        ]

    respuesta = _llamar(pagina, "chat", msgs, 0.5)
    add_to_historial(pagina, "user", pregunta)
    add_to_historial(pagina, "assistant", respuesta)
    return respuesta