"""
src/data/persistence.py
Persistencia del progreso del usuario en la BASE DE DATOS.

Antes (v1.x) cada corrida se guardaba como archivo .joblib en
data/history/, en una carpeta GLOBAL: cualquier persona que abriera la
app veía —y cargaba automáticamente— las corridas de todos los demás.
Ahora:

  - Cada corrida pertenece a un usuario autenticado (tabla `corridas`).
  - Métricas, resultados por modelo y pronósticos quedan en tablas
    relacionales, consultables y comparables entre corridas.
  - Los objetos de Python (modelo entrenado, scaler, DataFrames) se
    guardan como artefactos firmados con HMAC y solo se reescriben
    cuando cambian.

La interfaz pública (save_current_snapshot, ensure_restored,
list_snapshots, load_snapshot, ...) se mantiene igual que en la
versión anterior para no tener que reescribir las páginas.
"""
from __future__ import annotations

import logging

import streamlit as st

from src.auth.session import current_user
from src.db import repository as repo

log = logging.getLogger(__name__)

# Claves de session_state que conforman una corrida completa
_SNAPSHOT_KEYS = [
    "dataset_processed", "dataset_raw", "preprocessing_report", "preprocessor",
    "selected_partidas", "feature_cols", "scaler", "validation_method",
    "comparison_results", "best_model_info", "model_selector", "walk_forward_results",
    "X_train", "X_test", "y_train", "y_test", "dates_train", "dates_test",
    "predictions_future",
    "shap_importance_df", "hyp_results", "residuals_analysis",
]

# Qué se invalida cuando se rehace una etapa (para no mezclar resultados
# de un dataset/modelo anterior con los nuevos).
_DOWNSTREAM = {
    "datos": [
        "comparison_results", "best_model_info", "model_selector", "walk_forward_results",
        "X_train", "X_test", "y_train", "y_test", "dates_train", "dates_test",
        "feature_cols", "scaler", "validation_method",
        "predictions_future", "shap_importance_df", "hyp_results", "residuals_analysis",
    ],
    "entrenamiento": [
        "predictions_future", "shap_importance_df", "hyp_results", "residuals_analysis",
    ],
}


def _uid():
    user = current_user()
    return user["id"] if user else None


def _clear_ai_cache():
    for k in [k for k in st.session_state.keys() if str(k).startswith(("ai_auto_", "ai_chat_"))]:
        del st.session_state[k]


def reset_downstream(etapa: str) -> None:
    """Borra de la sesión los resultados que dependen de `etapa`."""
    for k in _DOWNSTREAM.get(etapa, []):
        st.session_state[k] = None
    st.session_state.pop("_pdf_report_bytes", None)
    _clear_ai_cache()


def save_current_snapshot(nombre: str | None = None, origen: str | None = None):
    """Guarda (o actualiza) la corrida actual del usuario en la base de datos.
    Devuelve el id de la corrida, o None si no hay nada que guardar."""
    uid = _uid()
    if uid is None or st.session_state.get("dataset_processed") is None:
        return None
    try:
        cid = st.session_state.get("_snapshot_id")
        if not cid:
            cid = repo.crear_corrida(uid, nombre, origen)
            st.session_state["_snapshot_id"] = cid
        estado = {k: st.session_state.get(k) for k in _SNAPSHOT_KEYS}
        ok = repo.guardar_estado_corrida(uid, cid, estado)
        if not ok:  # la corrida fue borrada desde otra pestaña
            cid = repo.crear_corrida(uid, nombre, origen)
            st.session_state["_snapshot_id"] = cid
            repo.guardar_estado_corrida(uid, cid, estado)
        return cid
    except Exception:
        log.exception("Error guardando la corrida")
        st.toast("No se pudo guardar el progreso en la base de datos. "
                 "Tu sesión sigue activa, pero revisa la conexión.", icon="⚠️")
        return None


def start_new_snapshot():
    """La próxima llamada a save_current_snapshot() creará una corrida nueva."""
    st.session_state["_snapshot_id"] = None


def list_snapshots():
    uid = _uid()
    return repo.listar_corridas(uid) if uid is not None else []


def load_snapshot(snapshot_id) -> bool:
    uid = _uid()
    if uid is None:
        return False
    estado = repo.cargar_estado_corrida(uid, int(snapshot_id))
    if estado is None:
        return False
    invalidos = estado.pop("_artefactos_invalidos", [])
    for k in _SNAPSHOT_KEYS:          # limpiar restos de la corrida anterior
        st.session_state[k] = None
    st.session_state.pop("_pdf_report_bytes", None)
    _clear_ai_cache()
    for k, v in estado.items():
        st.session_state[k] = v
    st.session_state["_snapshot_id"] = int(snapshot_id)
    if invalidos:
        st.warning(
            "Algunos datos guardados de esta corrida no pasaron la verificación de "
            "integridad y se omitieron: " + ", ".join(invalidos)
        )
    return True


def delete_snapshot(snapshot_id):
    uid = _uid()
    if uid is None:
        return False
    ok = repo.eliminar_corrida(uid, int(snapshot_id))
    if ok and st.session_state.get("_snapshot_id") == int(snapshot_id):
        for k in _SNAPSHOT_KEYS:
            st.session_state[k] = None
        st.session_state["_snapshot_id"] = None
        _clear_ai_cache()
    return ok


def rename_snapshot(snapshot_id, nombre: str) -> bool:
    uid = _uid()
    return bool(uid) and repo.renombrar_corrida(uid, int(snapshot_id), nombre)


def current_snapshot_id():
    return st.session_state.get("_snapshot_id")


def ensure_restored():
    """Si la sesión está vacía (página recargada), restaura la corrida más
    reciente DEL USUARIO AUTENTICADO."""
    if st.session_state.get("dataset_processed") is not None:
        return False
    if st.session_state.get("_restore_attempted"):
        return False
    st.session_state["_restore_attempted"] = True
    try:
        corridas = list_snapshots()
        if corridas and load_snapshot(corridas[0]["id"]):
            st.session_state["_just_restored"] = True
            return True
    except Exception:
        log.exception("Error restaurando la última corrida")
    return False


def show_restored_notice():
    if st.session_state.pop("_just_restored", False):
        st.toast("Se restauró tu última corrida guardada.", icon="💾")
