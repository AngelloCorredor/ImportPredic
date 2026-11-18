"""
components/page_setup.py
Arranque común de TODAS las páginas. Antes cada página repetía ~15
líneas idénticas (set_page_config, CSS, restauración, interruptor de
tema); ahora es una sola llamada:

    from components.page_setup import setup_page
    user = setup_page("Carga de Datos", "📥")

En este orden: configura la página, inyecta el CSS, exige sesión
iniciada, restaura la última corrida del usuario, dibuja la barra
lateral (usuario, corrida activa, cerrar sesión) y el interruptor de
tema claro/oscuro.
"""
from __future__ import annotations

import html
import logging

import streamlit as st

from config.settings import ACADEMIC_INFO
from config.theme import get_css

_configured = False


def _configure_logging():
    global _configured
    if not _configured:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        _configured = True


_DEFAULTS = {
    "dataset_raw": None, "dataset_processed": None, "preprocessing_report": None,
    "preprocessor": None, "feature_cols": None,
    "X_train": None, "X_test": None, "y_train": None, "y_test": None,
    "dates_train": None, "dates_test": None,
    "model_selector": None, "comparison_results": None, "best_model_info": None,
    "predictions_future": None,
}


def _sidebar(user: dict) -> None:
    from src.auth.session import logout
    from src.data.persistence import current_snapshot_id, list_snapshots

    with st.sidebar:
        st.markdown(
            '<h2 class="neon-text-cyan" style="font-family:var(--font-display);margin-bottom:0;">'
            "⚡ IMPORTPREDIC</h2>",
            unsafe_allow_html=True,
        )
        st.caption("Sistema Predictivo de Importación de Insumos Críticos")

        rol = "Administrador" if user.get("rol") == "admin" else "Usuario"
        st.markdown(
            f'<div class="sidebar-user"><div class="sidebar-avatar">'
            f'{html.escape((user.get("nombre") or "?")[:1].upper())}</div>'
            f'<div><div class="sidebar-user-name">{html.escape(user.get("nombre") or "")}</div>'
            f'<div class="sidebar-user-role">@{html.escape(user["username"])} · {rol}</div></div></div>',
            unsafe_allow_html=True,
        )

        status_data = "ok" if st.session_state.get("dataset_processed") is not None else "pending"
        status_model = "ok" if st.session_state.get("best_model_info") is not None else "pending"
        status_pred = "ok" if st.session_state.get("predictions_future") is not None else "pending"
        st.markdown(
            f'<span class="status-indicator {status_data}"></span> Datos procesados<br>'
            f'<span class="status-indicator {status_model}"></span> Modelo entrenado<br>'
            f'<span class="status-indicator {status_pred}"></span> Pronóstico generado',
            unsafe_allow_html=True,
        )

        cid = current_snapshot_id()
        if cid:
            nombre = next((c["nombre"] for c in list_snapshots() if c["id"] == cid), None)
            if nombre:
                st.caption(f"💾 Corrida activa: **{nombre}**")
        st.page_link("pages/09_historial.py", label="Mis corridas", icon="🗂️")
        if user.get("rol") == "admin":
            st.page_link("pages/10_administracion.py", label="Administración", icon="🛡️")

        with st.expander("Mi cuenta"):
            _change_password_form(user)
        if st.button("Cerrar sesión", icon="🚪", use_container_width=True, key="_logout_btn"):
            logout()
            st.rerun()

        st.markdown("---")
        st.caption(f"**Universidad:** {ACADEMIC_INFO['universidad']}")
        st.caption(f"**Programa:** {ACADEMIC_INFO['programa']}")
        st.caption(f"**Autor:** {ACADEMIC_INFO['autor']}")


def _change_password_form(user: dict) -> None:
    from src.db import repository as repo

    with st.form("_pwd_form", clear_on_submit=True, border=False):
        actual = st.text_input("Contraseña actual", type="password", max_chars=128)
        nueva = st.text_input("Nueva contraseña", type="password", max_chars=128)
        conf = st.text_input("Confirmar nueva", type="password", max_chars=128)
        ok = st.form_submit_button("Cambiar contraseña", use_container_width=True)
    if ok:
        if nueva != conf:
            st.error("Las contraseñas nuevas no coinciden.")
            return
        try:
            repo.cambiar_password(user["id"], actual, nueva)
            st.success("Contraseña actualizada.")
        except ValueError as e:
            st.error(str(e))


def setup_page(title: str, icon: str, *, admin_only: bool = False, restore: bool = True) -> dict:
    _configure_logging()
    st.set_page_config(
        page_title=f"{title} | ImportPredic" if title else "ImportPredic",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(f"<style>{get_css()}</style>", unsafe_allow_html=True)

    from src.auth.session import require_admin, require_login

    user = require_admin() if admin_only else require_login()

    if user.get("rol") != "admin":
        # El acceso real lo bloquea require_admin(); esto solo limpia el menú.
        st.markdown(
            '<style>[data-testid="stSidebarNav"] a[href*="administracion"]'
            "{display:none !important;}</style>",
            unsafe_allow_html=True,
        )

    for k, v in _DEFAULTS.items():
        st.session_state.setdefault(k, v)

    if restore:
        from src.data.persistence import ensure_restored, show_restored_notice

        ensure_restored()
        show_restored_notice()

    _sidebar(user)

    from components.theme_toggle import render_theme_toggle

    _spacer, col_toggle = st.columns([10, 1])
    with col_toggle:
        render_theme_toggle()
    return user
