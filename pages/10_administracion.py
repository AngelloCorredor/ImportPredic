"""
pages/10_administracion.py
Panel de administración: usuarios, uso del asistente de IA y bitácora de
auditoría. Solo accesible para cuentas con rol "admin".
"""
import plotly.graph_objects as go
import streamlit as st

from components.page_setup import setup_page

admin = setup_page("Administración", "🛡️", admin_only=True, restore=False)

from config import secrets as cfg
from src.ai.openrouter_client import is_configured
from src.db import repository as repo
from src.db.engine import get_engine
from src.utils.helpers import apply_neon_theme

st.markdown("## 🛡️ Administración")

stats = repo.estadisticas_generales()
mb = stats["almacenamiento_bytes"] / (1024 * 1024)
st.markdown(
    '<div class="kpi-row">'
    f'<div class="kpi-tile"><div class="kpi-label">Usuarios</div><div class="kpi-value">{stats["usuarios"]}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Corridas</div><div class="kpi-value">{stats["corridas"]}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Consultas IA (24 h)</div><div class="kpi-value">{stats["ia_24h"]}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Fallos IA (24 h)</div><div class="kpi-value">{stats["ia_fallos_24h"]}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Almacenamiento</div><div class="kpi-value">{mb:,.1f} MB</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
with st.expander("Estado de la configuración", expanded=False):
    engine = get_engine()
    filas = [
        ("Motor de base de datos", engine.dialect.name),
        ("Asistente de IA", "Configurado ✓" if is_configured() else "Sin API key ✗"),
        ("Entorno", "Producción" if cfg.is_production() else "Desarrollo"),
        ("Registro abierto", "Sí" if cfg.allow_registration() else "No"),
        ("Límite IA por usuario/hora", str(cfg.ai_requests_per_hour())),
        ("Cierre por inactividad", f"{cfg.session_timeout_minutes()} min"),
    ]
    for k, v in filas:
        st.markdown(f"**{k}:** {v}")
    st.caption("Estos valores se cambian en `.streamlit/secrets.toml` o en las variables de entorno. "
               "Por seguridad, aquí nunca se muestra la API key.")

tab_u, tab_ia, tab_a = st.tabs(["👥 Usuarios", "🤖 Uso de la IA", "📜 Auditoría"])

with tab_u:
    usuarios = repo.listar_usuarios()
    st.dataframe(usuarios.drop(columns=["id"]), use_container_width=True, hide_index=True)

    otros = usuarios[usuarios["id"] != admin["id"]]
    if otros.empty:
        st.caption("No hay otros usuarios todavía.")
    else:
        st.markdown("#### Gestionar un usuario")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            uid = st.selectbox(
                "Usuario", options=otros["id"].tolist(),
                format_func=lambda i: f'{otros.set_index("id").loc[i, "Nombre"]} (@{otros.set_index("id").loc[i, "Usuario"]})',
            )
        fila = otros.set_index("id").loc[uid]
        with c2:
            rol = st.selectbox("Rol", ["usuario", "admin"], index=0 if fila["Rol"] == "usuario" else 1)
        with c3:
            activo = st.toggle("Cuenta activa", value=bool(fila["Activo"]))
        if st.button("Guardar cambios", type="primary"):
            try:
                repo.actualizar_usuario(admin["id"], int(uid), rol=rol, activo=activo)
                st.success("Usuario actualizado.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.markdown("#### Crear un usuario")
    with st.form("admin_crear_usuario", clear_on_submit=True):
        a, b = st.columns(2)
        nombre = a.text_input("Nombre completo", max_chars=120)
        username = b.text_input("Usuario", max_chars=30)
        pwd = a.text_input("Contraseña temporal", type="password", max_chars=128)
        rol_nuevo = b.selectbox("Rol", ["usuario", "admin"])
        if st.form_submit_button("Crear usuario"):
            try:
                repo.crear_usuario(username, nombre, pwd, rol=rol_nuevo)
                st.success(f"Usuario @{username.lower()} creado. Pídele que cambie la contraseña en «Mi cuenta».")
            except ValueError as e:
                st.error(str(e))

with tab_ia:
    uso = repo.uso_ia_por_dia(14)
    if uso.empty:
        st.info("Aún no hay consultas registradas al asistente de IA.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=uso["dia"], y=uso["exitosas"], name="Exitosas", marker_color="#2ECC8F"))
        fig.add_trace(go.Bar(x=uso["dia"], y=uso["llamadas"] - uso["exitosas"], name="Fallidas",
                             marker_color="#FF6B81"))
        fig.update_layout(barmode="stack", template="plotly_dark", title="Consultas al asistente — últimos 14 días")
        apply_neon_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Cada usuario puede hacer como máximo {cfg.ai_requests_per_hour()} consultas por hora. "
               "Esto protege el saldo de la API key frente a abuso.")

with tab_a:
    st.dataframe(repo.listar_auditoria(300), use_container_width=True, hide_index=True)
    st.caption("Registro de inicios de sesión (exitosos y fallidos), bloqueos, creación y borrado de "
               "corridas, cambios de contraseña y acciones de administración.")
