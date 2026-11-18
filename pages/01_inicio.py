import streamlit as st
import streamlit.components.v1 as components

from config.theme import inject_three_js_scene
from config.settings import INSUMOS_CRITICOS, MODELOS_CANDIDATOS, MODELO_REFERENCIA, ACADEMIC_INFO

from components.page_setup import setup_page
user = setup_page("Inicio", "🏠")



# --- HERO con escena 3D ---
st.markdown('<div class="hero-section">', unsafe_allow_html=True)
components.html(inject_three_js_scene(), height=460, scrolling=False)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<p style="text-align:center;color:var(--text-secondary);font-family:var(--font-mono);">'
    'Ingeniería de Sistemas — UDI Barrancabermeja</p>',
    unsafe_allow_html=True,
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- ESTADO DEL SISTEMA ---
st.markdown("### Estado del Sistema")
c1, c2, c3, c4 = st.columns(4)

data_ok = st.session_state.get("dataset_processed") is not None
model_ok = st.session_state.get("best_model_info") is not None
pred_ok = st.session_state.get("predictions_future") is not None

with c1:
    st.metric("Datos Cargados", "✓ Listo" if data_ok else "✗ Sin datos")
with c2:
    best_name = st.session_state["best_model_info"]["best_model_name"] if model_ok else "—"
    st.metric("Modelo Entrenado", best_name)
with c3:
    st.metric("Último Pronóstico", "Generado" if pred_ok else "—")
with c4:
    rmse_val = st.session_state["best_model_info"]["metrics"]["RMSE"] if model_ok else None
    st.metric("RMSE del Mejor Modelo", f"{rmse_val:,.0f} kg" if rmse_val else "—")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- ACCESO RÁPIDO ---
st.markdown("### Acceso Rápido")

# Cada tarjeta es un st.page_link REAL (un <a> de verdad, no un botón
# invisible superpuesto). El click funciona siempre sobre el elemento
# que el usuario ve y toca, y st.page_link navega dentro de la MISMA
# pestaña/ventana (nunca abre una ventana o pestaña nueva).
#
# El color de cada tarjeta tiene dos variantes: una más clara para modo
# claro y una más oscura para modo oscuro (se alternan automáticamente
# con la clase "dark-mode" que ya usa el interruptor día/noche).
quick_links = [
    ("📥", "Cargar Datos", "pages/02_carga_datos.py", "#853240", "#36171c"),
    ("🔍", "Explorar", "pages/03_exploracion.py", "#30537d", "#0d1929"),
    ("🧠", "Entrenar Modelo", "pages/04_entrenamiento.py", "#4c3b80", "#171128"),
    ("📈", "Predecir", "pages/05_prediccion.py", "#766439", "#27200E"),
    ("✅", "Evaluar", "pages/06_evaluacion.py", "#2B6C54", "#0f271e"),
    ("📄", "Reporte", "pages/08_reporte.py", "#313770", "#0e1129"),
]

# CSS base (compartido por todas las tarjetas) + reglas puntuales de
# color/ícono por cada tarjeta (usando su "key" de contenedor).
_base_css = """
<style>
div[class*="st-key-quicklink_"] {
    margin-bottom: 18px;
    width: 100% !important;
}
/* Streamlit envuelve st.page_link en varias capas de <div> con flexbox
   que por defecto se "encogen" al tamaño del contenido (por eso las
   tarjetas salían con anchos distintos). Forzamos el 100% en TODA la
   cadena de contenedores para que las 3 columnas queden parejas. */
div[class*="st-key-quicklink_"] > div,
div[class*="st-key-quicklink_"] [data-testid="stVerticalBlock"],
div[class*="st-key-quicklink_"] [data-testid="stVerticalBlockBorderWrapper"],
div[class*="st-key-quicklink_"] [data-testid="element-container"],
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] {
    width: 100% !important;
    flex: 1 1 100% !important;
}
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] {
    margin: 0 !important;
}
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] a {
    position: relative;
    box-sizing: border-box !important;
    display: flex !important;
    align-items: center;
    width: 100% !important;
    height: 82px;
    border-radius: 20px !important;
    border: none !important;
    padding: 0 78px 0 26px !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
    transition: box-shadow 0.2s ease, transform 0.2s ease, filter 0.2s ease;
    text-decoration: none !important;
    font-family: var(--font-display, inherit);
    font-weight: 600;
    font-size: 0.95rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] a,
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] a * {
    color: #ffffff !important;
}
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] a:hover {
    box-shadow: 0 8px 22px rgba(0,0,0,0.20);
    transform: translateY(-2px);
    filter: brightness(1.08);
}
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] a:active {
    transform: translateY(0);
    filter: brightness(0.96);
}
/* Círculo del ícono, dibujado con ::after para no depender de la
   estructura interna del ícono que arma Streamlit */
div[class*="st-key-quicklink_"] [data-testid="stPageLink"] a::after {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
</style>
"""

_per_card_css = "<style>\n"
for i, (icon, label, target, color_light, color_dark) in enumerate(quick_links):
    key = f"st-key-quicklink_{i}"
    _per_card_css += (
        f'div[class*="{key}"] [data-testid="stPageLink"] a {{ background:{color_light} !important; }}\n'
        f'body.dark-mode div[class*="{key}"] [data-testid="stPageLink"] a,\n'
        f'.dark-mode div[class*="{key}"] [data-testid="stPageLink"] a {{ background:{color_dark} !important; }}\n'
        f'div[class*="{key}"] [data-testid="stPageLink"] a::after {{ content: "{icon}"; }}\n'
    )
_per_card_css += "</style>\n"

st.markdown(_base_css + _per_card_css, unsafe_allow_html=True)

cols = st.columns(3)
for i, (icon, label, target, color_light, color_dark) in enumerate(quick_links):
    with cols[i % 3]:
        with st.container(key=f"quicklink_{i}"):
            # El ancho 100% ya lo impone el CSS de arriba; así evitamos
            # depender de "use_container_width" (no existe en todas las
            # versiones de Streamlit para st.page_link).
            st.page_link(target, label=label)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- CONTEXTO DEL PROYECTO ---
with st.expander("📋 Contexto del Proyecto Académico", expanded=False):
    st.write(
        f"**Objetivo:** {ACADEMIC_INFO['objetivo']}\n\n"
        f"**Hipótesis:** {ACADEMIC_INFO['hipotesis']}\n\n"
        f"**Período de análisis:** {ACADEMIC_INFO['periodo_analisis']}"
    )
    st.markdown("**Insumos críticos analizados:**")
    for code, desc in INSUMOS_CRITICOS.items():
        st.markdown(f'<span class="badge-insumo">{code}</span> {desc}', unsafe_allow_html=True)

    st.markdown("**Fuentes de datos:** DIAN · DANE · Banco de la República")
    st.markdown("**Algoritmos implementados:**")
    for m in MODELOS_CANDIDATOS:
        st.markdown(f"- {m}")
    st.markdown(f"- {MODELO_REFERENCIA} (modelo de referencia)")

    st.markdown("---")
    st.caption(f"Director: {ACADEMIC_INFO['director']}")
    st.caption(f"Autor: {ACADEMIC_INFO['autor']}")

# --- INSTRUCCIONES DE USO ---
with st.expander("🧭 Guía de Uso del Sistema", expanded=True):
    steps = [
        "Cargar datos CSV de DIAN/DANE/Banco de la República (o usar los datos de demostración).",
        "Explorar y validar los datos en el módulo de análisis exploratorio.",
        "Entrenar y comparar los 5 modelos de Machine Learning contra ARIMA.",
        "Generar pronósticos de volumen de importación a futuro.",
        "Revisar métricas y pruebas estadísticas de la hipótesis.",
        "Exportar el reporte final del proyecto.",
    ]
    for i, s in enumerate(steps, 1):
        st.markdown(
            f'<div style="margin-bottom:8px;"><span class="step-badge">{i}</span>{s}</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Panel de bienvenida
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel
render_ai_panel(
    pagina="inicio",
    auto_trigger=True,
    preguntas_sugeridas=[
        "¿Qué son los insumos críticos analizados en este proyecto?",
        "¿Cuál es la hipótesis del proyecto y cómo se verifica?",
        "¿Qué fuentes de datos se utilizan y por qué?",
    ],
    modo="expander",
)