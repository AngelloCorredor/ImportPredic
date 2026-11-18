"""
app.py
Punto de entrada principal de ImportPredic — se ejecuta con: streamlit run app.py
"""
import html

import streamlit as st

from components.page_setup import setup_page

user = setup_page("", "📊")

# ============================================================
# HERO — bienvenida
# ============================================================
st.markdown(
    '''<div class="welcome-hero">
        <div class="welcome-hero-glow"></div>
        <div class="welcome-hero-glow-2"></div>
        <div class="welcome-hero-content">
            <div class="welcome-hero-eyebrow">Hola, {nombre} 👋 · Sistema de pronóstico inteligente</div>
            <h1 class="welcome-hero-title">Import<span>Predic</span></h1>
            <p class="welcome-hero-subtitle">
                Anticipa con meses de antelación la demanda de insumos críticos de
                importación, combinando Machine Learning, series de tiempo y
                validación estadística rigurosa frente a un modelo de referencia (ARIMA).
            </p>
        </div>
        <div class="welcome-hero-tags">
            <span>📥 Datos DIAN · DANE · BanRep</span>
            <span>🤖 6 modelos comparados</span>
            <span>✅ Validación estadística</span>
            <span>🔐 Cuentas y base de datos</span>
        </div>
    </div>'''.replace("{nombre}", html.escape((user.get("nombre") or "").split(" ")[0])),
    unsafe_allow_html=True,
)

# --- Resumen del progreso del usuario (desde la base de datos) ---
from src.data.persistence import list_snapshots

_corridas = list_snapshots()
_entrenadas = [c for c in _corridas if c["mejor_modelo"]]
_mejor = min(_entrenadas, key=lambda c: c["rmse"] if c["rmse"] is not None else float("inf"), default=None)
st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
st.markdown(
    '<div class="kpi-row">'
    f'<div class="kpi-tile"><div class="kpi-label">Corridas guardadas</div><div class="kpi-value">{len(_corridas)}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Con modelo entrenado</div><div class="kpi-value">{len(_entrenadas)}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Criterio del 15 % cumplido</div><div class="kpi-value">'
    f'{sum(1 for c in _entrenadas if c["hipotesis_confirmada"])} / {len(_entrenadas)}</div></div>'
    f'<div class="kpi-tile"><div class="kpi-label">Mejor modelo histórico</div><div class="kpi-value">'
    f'{html.escape(_mejor["mejor_modelo"]) if _mejor else "—"}</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)
col_cta1, col_cta2, _ = st.columns([1.3, 1.3, 3])
with col_cta1:
    st.markdown(
        '<a class="welcome-cta-primary" href="/inicio" target="_self">🚀 Comenzar ahora</a>',
        unsafe_allow_html=True,
    )
with col_cta2:
    st.markdown(
        '<a class="welcome-cta-secondary" href="/carga_datos" target="_self">Ir directo a Carga de Datos →</a>',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ============================================================
# QUÉ ES IMPORTPREDIC
# ============================================================
st.markdown("### 🧭 ¿Qué es ImportPredic?")
st.markdown(
    "**ImportPredic** es un sistema de pronóstico desarrollado como proyecto de grado para "
    "anticipar el volumen mensual de importación de insumos críticos (como refrigerantes, "
    "compresores o componentes electrónicos), apoyándose en variables macroeconómicas "
    "(TRM, inflación, tasas de interés) y en el comportamiento histórico de cada insumo. "
    "El sistema entrena y compara varios algoritmos de Machine Learning contra un modelo "
    "estadístico clásico (ARIMA), y solo declara un modelo \"ganador\" cuando una prueba "
    "estadística formal confirma que su mejora es real y no producto del azar."
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ============================================================
# CÓMO FUNCIONA — pipeline de 8 etapas
# ============================================================
st.markdown("### ⚙️ ¿Cómo funciona? — El flujo de trabajo")
st.caption("Las etapas están pensadas para recorrerse en orden la primera vez, de arriba hacia abajo en el menú de la izquierda.")

stages = [
    ("📥", "1. Carga de Datos", "Sube tus archivos CSV/XLSX de DIAN, DANE o BanRep, o usa el dataset de "
     "demostración. El sistema valida columnas, mide la calidad y prepara las variables."),
    ("🔍", "2. Exploración", "Tendencia, estacionalidad, outliers y correlaciones con gráficas "
     "interactivas — cada una con su propia explicación integrada al hacer clic."),
    ("🧠", "3. Entrenamiento", "Compara XGBoost, Random Forest, Gradient Boosting, Ridge y Lasso "
     "contra un modelo ARIMA de referencia, con validación hold-out o walk-forward."),
    ("📈", "4. Predicción", "Genera el pronóstico del volumen de importación para los próximos "
     "meses, con su intervalo de confianza del 95%."),
    ("✅", "5. Evaluación", "Verifica la hipótesis del proyecto con pruebas estadísticas formales: "
     "Shapiro-Wilk, Diebold-Mariano y análisis de residuos."),
    ("🧩", "6. Interpretabilidad", "Entiende qué variables influyen más en las predicciones del "
     "modelo mediante valores SHAP."),
    ("📄", "7. Reporte", "Genera un PDF profesional listo para anexar al documento de grado, más "
     "archivos Excel con formato de dashboard."),
    ("💾", "8. Historial", "Cada corrida queda guardada en la base de datos dentro de tu cuenta: "
     "puedes retomarla desde cualquier equipo y comparar corridas entre sí."),
]
stage_cards_html = '<div class="stage-grid">' + "".join(
    f'''<div class="stage-card">
            <span class="stage-number">{i+1:02d}</span>
            <div class="stage-icon">{icon}</div>
            <div class="stage-title">{title}</div>
            <div class="stage-desc">{desc}</div>
        </div>'''
    for i, (icon, title, desc) in enumerate(stages)
) + "</div>"
st.markdown(stage_cards_html, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ============================================================
# CARACTERÍSTICAS DESTACADAS
# ============================================================
st.markdown("### ✨ Características destacadas")
features = [
    ("blue", "🤖", "Asistente de IA integrado",
     "Haz consultas en lenguaje natural sobre tus datos, métricas y resultados en cada módulo."),
    ("green", "🌓", "Modo claro / oscuro",
     "Toda la interfaz —incluidas las gráficas— se adapta al tema que prefieras, de un clic."),
    ("amber", "🔐", "Cuentas seguras y base de datos",
     "Cada usuario tiene su propio historial protegido; nada se mezcla entre cuentas."),
    ("violet", "📊", "Reportes profesionales",
     "PDF multi-página y Excel tipo dashboard, listos para anexar al documento de grado."),
]
feat_html = '<div class="stage-grid">' + "".join(
    f'''<div class="stage-card">
            <div class="download-card-icon {color}" style="margin-bottom:14px;">{icon}</div>
            <div class="stage-title">{title}</div>
            <div class="stage-desc">{desc}</div>
        </div>'''
    for color, icon, title, desc in features
) + "</div>"
st.markdown(feat_html, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ============================================================
# CÓMO NAVEGAR
# ============================================================
st.markdown(
    '''<div class="chart-explain" style="margin-top:0;">
        <div class="chart-explain-icon">🧭</div>
        <div>
            <div class="chart-explain-title">Cómo navegar</div>
            <div class="chart-explain-body"><p>
                Usa el menú de la <b>barra lateral izquierda</b> para moverte entre módulos en
                cualquier momento — no es obligatorio seguir el orden, pero cada etapa
                aprovecha los resultados de la anterior (por ejemplo, Predicción necesita un
                modelo ya entrenado). Si en algún momento ves un aviso de "primero completa
                tal módulo", ese enlace te lleva directo a él.
            </p></div>
        </div>
    </div>''',
    unsafe_allow_html=True,
)
