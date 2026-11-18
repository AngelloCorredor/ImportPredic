"""
src/auth/session.py
Manejo de sesión en Streamlit: inicio/cierre de sesión, expiración por
inactividad y pantalla de acceso.

Cada página llama a `require_login()` (a través de components.page_setup)
antes de mostrar cualquier contenido; si no hay sesión válida, se dibuja
el formulario de acceso y la ejecución de la página se detiene.
"""
from __future__ import annotations

import time

import streamlit as st

from config import secrets as cfg

_USER_KEY = "_auth_user"
_ACTIVITY_KEY = "_auth_last_activity"


def current_user() -> dict | None:
    return st.session_state.get(_USER_KEY)


def is_admin() -> bool:
    u = current_user()
    return bool(u and u.get("rol") == "admin")


def _start_session(user: dict) -> None:
    # Se limpia todo lo anterior para no heredar datos de otra cuenta
    # que se haya usado en la misma pestaña del navegador.
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state[_USER_KEY] = user
    st.session_state[_ACTIVITY_KEY] = time.time()
    st.session_state["_auth_checked"] = time.time()


def logout(motivo: str | None = None) -> None:
    from src.db import repository as repo

    u = current_user()
    if u:
        repo.auditar("logout", u["id"], u["username"], motivo)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    if motivo:
        st.session_state["_auth_notice"] = motivo


def _check_timeout() -> None:
    last = st.session_state.get(_ACTIVITY_KEY)
    limit = cfg.session_timeout_minutes() * 60
    if last and time.time() - last > limit:
        logout("Tu sesión se cerró por inactividad. Vuelve a iniciar sesión.")
        return
    st.session_state[_ACTIVITY_KEY] = time.time()

    # Cada minuto se revalida contra la BD: si un administrador desactivó
    # la cuenta o le cambió el rol, el cambio aplica sin esperar al logout.
    if time.time() - st.session_state.get("_auth_checked", 0) > 60:
        from src.db import repository as repo

        fresh = repo.obtener_usuario(current_user()["id"])
        if not fresh or not fresh["activo"]:
            logout("Tu cuenta fue desactivada. Contacta al administrador.")
            return
        st.session_state[_USER_KEY] = fresh
        st.session_state["_auth_checked"] = time.time()


_LOGIN_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.auth-brand { text-align:center; margin: 4vh 0 18px; }
.auth-brand h1 { font-family: var(--font-display, 'Poppins', sans-serif); font-size: 2.4rem;
                 margin: 0; letter-spacing: -0.5px; }
.auth-brand h1 span { color: var(--accent-primary, #6C63FF); }
.auth-brand p { color: var(--text-secondary, #6B6A85); margin: 6px 0 0; font-size: 0.95rem; }
.auth-foot { text-align:center; color: var(--text-secondary, #6B6A85); font-size: 0.78rem;
             margin-top: 14px; line-height: 1.6; }
</style>
"""


def _render_login_screen() -> None:
    from src.db import repository as repo

    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.25, 1])
    with col:
        st.markdown(
            '<div class="auth-brand"><h1>Import<span>Predic</span></h1>'
            "<p>Sistema predictivo de importación de insumos críticos</p></div>",
            unsafe_allow_html=True,
        )

        aviso = st.session_state.pop("_auth_notice", None)
        if aviso:
            st.info(aviso)

        try:
            hay_usuarios = repo.contar_usuarios() > 0
        except Exception:
            st.error(
                "No fue posible conectarse a la base de datos. Revisa la variable "
                "DATABASE_URL o los permisos de la carpeta data/."
            )
            st.stop()

        if not hay_usuarios:
            st.success(
                "**Configuración inicial.** Aún no hay cuentas en el sistema: la cuenta "
                "que crees ahora será la de **administrador**."
            )
            _registro_form(repo, primera=True)
            return

        tabs = ["Iniciar sesión"] + (["Crear cuenta"] if cfg.allow_registration() else [])
        t = st.tabs(tabs)
        with t[0]:
            with st.form("login_form", border=True):
                username = st.text_input("Usuario", max_chars=30, autocomplete="username")
                password = st.text_input("Contraseña", type="password", max_chars=128,
                                         autocomplete="current-password")
                enviar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
            if enviar:
                if not username or not password:
                    st.error("Escribe tu usuario y contraseña.")
                else:
                    with st.spinner("Verificando..."):
                        user, error = repo.autenticar(username, password)
                    if user:
                        _start_session(user)
                        st.rerun()
                    else:
                        st.error(error)
        if len(t) > 1:
            with t[1]:
                _registro_form(repo, primera=False)

        st.markdown(
            '<div class="auth-foot">Tus corridas, modelos y pronósticos se guardan en tu '
            "cuenta y solo tú puedes verlos.</div>",
            unsafe_allow_html=True,
        )


def _registro_form(repo, primera: bool) -> None:
    with st.form("registro_form", border=True):
        nombre = st.text_input("Nombre completo", max_chars=120)
        username = st.text_input("Usuario", max_chars=30,
                                 help="3-30 caracteres: letras, números, punto, guion o guion bajo.")
        email = st.text_input("Correo (opcional)", max_chars=160)
        p1 = st.text_input("Contraseña", type="password", max_chars=128,
                           help="Mínimo 8 caracteres, con al menos una letra y un número.",
                           autocomplete="new-password")
        p2 = st.text_input("Confirmar contraseña", type="password", max_chars=128,
                           autocomplete="new-password")
        label = "Crear cuenta de administrador" if primera else "Crear cuenta"
        enviar = st.form_submit_button(label, type="primary", use_container_width=True)
    if enviar:
        if p1 != p2:
            st.error("Las contraseñas no coinciden.")
            return
        try:
            user = repo.crear_usuario(username, nombre, p1, email)
        except ValueError as e:
            st.error(str(e))
            return
        _start_session(user)
        st.rerun()


def require_login() -> dict:
    """Devuelve el usuario autenticado o dibuja el login y detiene la página."""
    if current_user() is not None:
        _check_timeout()
    if current_user() is None:
        _render_login_screen()
        st.stop()
    return current_user()


def require_admin() -> dict:
    user = require_login()
    if user.get("rol") != "admin":
        st.error("Esta sección es solo para administradores.")
        st.stop()
    return user
