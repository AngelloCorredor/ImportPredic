import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats
from statsmodels.tsa.seasonal import STL

import streamlit as st

from config.theme import CHART_SLATE, CHART_ROSE, CHART_SAGE, CHART_GOLD, CHART_NEUTRAL_MID
from config.settings import TARGET_VARIABLE, FEATURE_COLUMNS
from src.utils.helpers import apply_neon_theme, mes_nombre
from components.chart_card import chart_card

from components.page_setup import setup_page
user = setup_page("Exploración", "🔍")


st.markdown("## 🔍 Análisis Exploratorio de Datos")

if st.session_state.get("dataset_processed") is None:
    st.warning("Primero carga y procesa los datos en el módulo **Carga de Datos**.")
    st.page_link("pages/02_carga_datos.py", label="Ir a Carga de Datos", icon="📥")
    st.stop()

df = st.session_state["dataset_processed"].copy()
df["fecha"] = pd.to_datetime(df["fecha"])

# --- SECCIÓN 1: SERIE DE TIEMPO PRINCIPAL ---
st.markdown("#### Serie de tiempo principal")
overlay_vars = st.multiselect(
    "Variables macroeconómicas a superponer",
    [c for c in FEATURE_COLUMNS if c in df.columns and c not in ["mes", "anio"]],
)

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["fecha"], y=df[TARGET_VARIABLE], name="Volumen importado (kg)",
                          line=dict(color=CHART_SLATE, width=2)))
for v in overlay_vars:
    fig.add_trace(go.Scatter(x=df["fecha"], y=df[v], name=v, yaxis="y2",
                              line=dict(width=1, dash="dot")))
fig.add_vrect(x0="2020-03-01", x1="2020-06-01", fillcolor=CHART_GOLD, opacity=0.18,
              annotation_text="Pandemia", annotation_font_color=CHART_GOLD, annotation_font_size=13,
              line_width=0)
fig.add_vrect(x0="2022-09-01", x1="2022-12-01", fillcolor=CHART_ROSE, opacity=0.18,
              annotation_text="Crisis cambiaria", annotation_font_color=CHART_ROSE, annotation_font_size=13,
              line_width=0)
fig.update_layout(template="plotly_dark", yaxis2=dict(overlaying="y", side="right", showgrid=False))
apply_neon_theme(fig)
chart_card(
    fig,
    chart_id="explo_serie_tiempo",
    title="Volumen de importación a través del tiempo",
    icon="📈",
    summary=[
        "<b>Eje X:</b> el tiempo, mes a mes, desde enero de 2015 hasta diciembre de 2024. "
        "<b>Eje Y izquierdo:</b> volumen importado en kilogramos (kg) — la línea principal. "
        "<b>Eje Y derecho (solo si superpones variables):</b> el valor de la variable "
        "macroeconómica elegida (por ejemplo la TRM en pesos por dólar), con su propia escala.",
        "Esta gráfica de <b>línea de tiempo</b> muestra el volumen mensual importado "
        "(eje izquierdo) a lo largo de todo el histórico disponible. Si eliges variables "
        "macroeconómicas para superponer, se dibujan como líneas punteadas contra un "
        "<b>eje secundario</b> (derecha), para comparar su comportamiento sin que su escala "
        "distinta distorsione la del volumen.",
        "Las franjas de color marcan períodos de interés conocidos (<b>Pandemia</b> y "
        "<b>Crisis cambiaria</b>) para ayudar a explicar visualmente caídas o picos atípicos.",
        "Sirve para detectar a simple vista la <b>tendencia</b> general, la "
        "<b>estacionalidad</b> (patrones que se repiten cada año) y el efecto de eventos "
        "externos sobre las importaciones — el punto de partida de cualquier análisis de "
        "series de tiempo.",
    ],
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 2: DESCOMPOSICIÓN STL ---
st.markdown("#### Descomposición de la serie (STL)")
try:
    ts = df.set_index("fecha")[TARGET_VARIABLE].asfreq("MS").interpolate()
    stl = STL(ts, period=12, robust=True).fit()
    fig_stl = go.Figure()
    fig_stl.add_trace(go.Scatter(x=ts.index, y=stl.trend, name="Tendencia", line=dict(color=CHART_SLATE)))
    fig_stl.add_trace(go.Scatter(x=ts.index, y=stl.seasonal, name="Estacionalidad", line=dict(color=CHART_ROSE)))
    fig_stl.add_trace(go.Scatter(x=ts.index, y=stl.resid, name="Residuo", line=dict(color=CHART_SAGE)))
    fig_stl.update_layout(template="plotly_dark")
    apply_neon_theme(fig_stl)
    chart_card(
        fig_stl,
        chart_id="explo_stl",
        title="Descomposición STL: tendencia, estacionalidad y residuo",
        icon="🧩",
        summary=[
            "<b>Eje X:</b> el tiempo, mes a mes (2015-2024). <b>Eje Y:</b> kilogramos (kg) "
            "para las tres líneas: la <b>tendencia</b> está en el nivel real del volumen, mientras "
            "que la <b>estacionalidad</b> y el <b>residuo</b> oscilan alrededor de 0 (valores "
            "positivos = más de lo habitual para ese momento; negativos = menos).",
            "La técnica <b>STL</b> (Seasonal-Trend decomposition using Loess) separa la serie "
            "original en tres componentes que se suman entre sí: la <b>tendencia</b> (evolución "
            "de largo plazo), la <b>estacionalidad</b> (patrón que se repite cada 12 meses) y "
            "el <b>residuo</b> (lo que no explican las dos anteriores, es decir, el ruido).",
            "Sirve para entender <b>por qué</b> sube o baja la serie en un momento dado: si el "
            "movimiento viene de la tendencia de fondo, de un pico estacional normal de esa "
            "época del año, o de un evento inusual reflejado en el residuo.",
            "Es una herramienta clave antes de elegir un modelo de pronóstico: si la "
            "estacionalidad es fuerte y estable, modelos como SARIMA o Prophet suelen "
            "aprovecharla bien.",
        ],
    )

    trend_change = (stl.trend.iloc[-1] - stl.trend.iloc[0]) / stl.trend.iloc[0] * 100
    seasonal_by_month = pd.Series(stl.seasonal.values, index=ts.index.month).groupby(level=0).mean()
    top_month = seasonal_by_month.idxmax()
    st.info(
        f"La tendencia muestra un cambio del **{trend_change:+.1f}%** en el período analizado. "
        f"El mes con mayor componente estacional es **{mes_nombre(top_month)}**."
    )

    # IA inline: interpretacion de la descomposicion STL
    from components.ai_panel import render_ai_insight
    render_ai_insight(
        pagina="exploracion", subtipo="descomposicion",
        contexto={
            "cambio_tendencia_pct": trend_change,
            "mes_mayor_estacional": mes_nombre(top_month),
            "fuerza_estacional": "alta" if abs(stl.seasonal.std()) > stl.resid.std() else "media",
        },
        label="IA - DESCOMPOSICION STL",
    )
except Exception as e:
    st.warning(f"No fue posible calcular la descomposición STL: {e}")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 3: MATRIZ DE CORRELACIÓN ---
st.markdown("#### Matriz de correlación")
corr_cols = [c for c in FEATURE_COLUMNS + [TARGET_VARIABLE] if c in df.columns]
corr = df[corr_cols].corr()
fig_corr = go.Figure(data=go.Heatmap(
    z=corr.values, x=corr.columns, y=corr.columns,
    colorscale=[[0, CHART_ROSE], [0.5, CHART_NEUTRAL_MID], [1, CHART_SLATE]],
    zmid=0, colorbar=dict(title="corr"),
))
fig_corr.update_layout(template="plotly_dark", height=520)
apply_neon_theme(fig_corr)
chart_card(
    fig_corr,
    chart_id="explo_correlacion",
    title="Matriz de correlación entre variables",
    icon="🔗",
    summary=[
        "<b>Eje X y Eje Y:</b> son las mismas variables del modelo (volumen importado, TRM, IPC, "
        "tasa de interés, rezagos, etc.), cruzadas entre sí. <b>Color de cada celda:</b> el "
        "coeficiente de correlación entre la variable de su fila y la de su columna, de -1 "
        "(tonos rosados) a +1 (tonos azul pizarra); la diagonal siempre vale 1 porque cada "
        "variable se correlaciona perfecto consigo misma.",
        "Cada celda muestra el <b>coeficiente de correlación</b> (r) entre dos variables, un "
        "número entre -1 y 1: cerca de 1 indica que suben y bajan juntas, cerca de -1 que se "
        "mueven en sentido contrario, y cerca de 0 que no hay relación lineal clara entre ellas.",
        "El color ayuda a leerlo de un vistazo: los tonos de un extremo de la escala marcan "
        "correlación negativa y los del otro extremo positiva, mientras que los tonos neutros "
        "del centro indican poca o ninguna relación.",
        "Sirve principalmente para <b>selección de variables</b>: identificar qué factores "
        "(precio del dólar, inflación, tasas, etc.) están más relacionados con el volumen "
        "importado, y detectar variables redundantes entre sí antes de entrenar un modelo.",
    ],
)

target_corr = corr[TARGET_VARIABLE].drop(TARGET_VARIABLE).abs().sort_values(ascending=False)
st.caption(f"Variable más correlacionada con el objetivo: **{target_corr.index[0]}** (|r| = {target_corr.iloc[0]:.2f})")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 4: ESTACIONALIDAD ---
st.markdown("#### Análisis de estacionalidad")
col1, col2 = st.columns(2)
with col1:
    monthly_avg = df.groupby(df["fecha"].dt.month)[TARGET_VARIABLE].mean()
    fig_polar = go.Figure(go.Scatterpolar(
        r=monthly_avg.values, theta=[mes_nombre(m) for m in monthly_avg.index],
        fill="toself", line_color=CHART_SLATE, fillcolor="rgba(124, 139, 150, 0.28)",
    ))
    fig_polar.update_layout(template="plotly_dark")
    apply_neon_theme(fig_polar)
    chart_card(
        fig_polar,
        chart_id="explo_radar_estacional",
        title="Patrón estacional promedio",
        icon="🕸️",
        summary=[
            "<b>Ángulo (los 12 \"rayos\"):</b> cada mes del año, de enero a diciembre. "
            "<b>Distancia desde el centro:</b> volumen importado promedio de ese mes, en "
            "kilogramos (kg), promediando todos los años del histórico. Entre más lejos del "
            "centro, mayor el volumen típico de ese mes.",
            "Este <b>gráfico de radar</b> (o araña) ubica los 12 meses del año alrededor de un "
            "círculo, y la distancia del centro hacia afuera representa el volumen "
            "<b>promedio histórico</b> importado en ese mes (promediando todos los años "
            "disponibles).",
            "A diferencia de una línea de tiempo, aquí <b>se elimina el eje del tiempo</b> y "
            "solo queda el 'perfil estacional' típico: permite ver de inmediato en qué meses "
            "la demanda suele ser más alta o más baja, sin que la tendencia de crecimiento "
            "general lo oculte.",
            "Sirve, por ejemplo, para planear con anticipación los meses de mayor importación "
            "(picos del polígono) y anticipar necesidades de inventario o de divisas.",
        ],
    )
    st.caption(f"Mayor demanda histórica promedio: **{mes_nombre(monthly_avg.idxmax())}**")
with col2:
    fig_years = go.Figure()
    for year in sorted(df["fecha"].dt.year.unique()):
        sub = df[df["fecha"].dt.year == year]
        fig_years.add_trace(go.Scatter(x=sub["fecha"].dt.month, y=sub[TARGET_VARIABLE],
                                        name=str(year), mode="lines"))
    fig_years.update_layout(template="plotly_dark", xaxis_title="Mes")
    apply_neon_theme(fig_years)
    chart_card(
        fig_years,
        chart_id="explo_comparacion_anual",
        title="Comparación año a año",
        icon="📅",
        summary=[
            "<b>Eje X:</b> el mes del año (1 = enero, 12 = diciembre). <b>Eje Y:</b> volumen "
            "importado ese mes, en kilogramos (kg). <b>Cada línea de color:</b> un año distinto "
            "(ver la leyenda de la derecha), para poder superponerlos y compararlos.",
            "Aquí se dibuja <b>una línea por cada año</b>, todas usando el mismo eje horizontal "
            "(mes 1 a 12), superpuestas unas sobre otras.",
            "Sirve para comparar directamente la <b>forma</b> de la curva estacional entre "
            "distintos años (¿el pico ocurre siempre en el mismo mes?) y el <b>nivel</b> "
            "general (¿un año importó consistentemente más que otro?).",
            "Es un buen complemento del radar: mientras el radar muestra el promedio general, "
            "esta vista deja ver la variabilidad año a año y si el patrón estacional se ha "
            "mantenido estable o ha ido cambiando con el tiempo.",
        ],
    )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 5: OUTLIERS ---
st.markdown("#### Análisis de outliers")
q1, q3 = df[TARGET_VARIABLE].quantile([0.25, 0.75])
iqr = q3 - q1
lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
outliers = df[(df[TARGET_VARIABLE] < lower) | (df[TARGET_VARIABLE] > upper)]

fig_box = go.Figure()
for year in sorted(df["fecha"].dt.year.unique()):
    fig_box.add_trace(go.Box(y=df[df["fecha"].dt.year == year][TARGET_VARIABLE], name=str(year)))
fig_box.update_layout(template="plotly_dark", showlegend=False)
apply_neon_theme(fig_box)
chart_card(
    fig_box,
    chart_id="explo_outliers",
    title="Boxplot de outliers por año (método IQR)",
    icon="🚨",
    summary=[
        "<b>Eje X:</b> cada año del histórico. <b>Eje Y:</b> volumen importado, en kilogramos "
        "(kg). <b>Puntos sueltos fuera de los bigotes:</b> meses cuyo volumen se considera atípico "
        "según el método IQR (más de 1.5 veces el rango intercuartílico por encima o por debajo).",
        "Igual que el boxplot de la página de carga de datos, cada caja resume un año "
        "completo con su mediana, cuartiles y 'bigotes'. El método <b>IQR</b> (rango "
        "intercuartílico) define como atípico cualquier valor que quede más de 1.5 veces ese "
        "rango por encima o por debajo de la caja.",
        "Sirve para <b>marcar automáticamente</b> meses cuyo volumen se sale claramente del "
        "comportamiento habitual de ese año — útil para revisar si son errores de carga de "
        "datos o eventos reales (paros, crisis, campañas puntuales) que conviene documentar "
        "antes de entrenar un modelo.",
    ],
)

if not outliers.empty:
    st.dataframe(outliers[["fecha", TARGET_VARIABLE]], use_container_width=True)
else:
    st.success("No se detectaron outliers significativos (método IQR).")

# IA inline: interpretacion de outliers
from components.ai_panel import render_ai_insight
render_ai_insight(
    pagina="exploracion", subtipo="outliers",
    contexto={
        "n_outliers": len(outliers),
        "fechas_outliers": ", ".join(outliers["fecha"].dt.strftime("%Y-%m").tolist()[:5]) if not outliers.empty else "Ninguna",
    },
    label="IA - ANALISIS DE OUTLIERS",
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 6: DISTRIBUCIÓN ---
st.markdown("#### Distribución estadística de la variable objetivo")
col_h, col_q = st.columns(2)
with col_h:
    fig_hist = go.Figure(go.Histogram(x=df[TARGET_VARIABLE], histnorm="probability density",
                                       marker_color=CHART_SLATE, opacity=0.85))
    fig_hist.update_layout(template="plotly_dark")
    apply_neon_theme(fig_hist)
    chart_card(
        fig_hist,
        chart_id="explo_hist_densidad",
        title="Distribución de frecuencia de la variable objetivo",
        icon="📊",
        summary=[
            "<b>Eje X:</b> volumen importado en kilogramos (kg), dividido en intervalos. "
            "<b>Eje Y:</b> densidad de probabilidad — no es un conteo de meses sino la "
            "concentración relativa de datos en cada intervalo (el área total de las barras suma 1).",
            "Este histograma normalizado (<b>densidad de probabilidad</b>) muestra la forma "
            "general de la distribución del volumen importado usando todo el histórico, no "
            "solo el dataset procesado.",
            "Sirve para evaluar visualmente si los datos se comportan de forma razonablemente "
            "'campanada' (similar a una normal) o si presentan sesgo, colas pesadas o varios "
            "picos — información clave para decidir si conviene transformar la variable antes "
            "de modelar.",
        ],
    )
with col_q:
    qq = stats.probplot(df[TARGET_VARIABLE], dist="norm")
    fig_qq = go.Figure()
    fig_qq.add_trace(go.Scatter(x=qq[0][0], y=qq[0][1], mode="markers", marker=dict(color=CHART_ROSE)))
    fig_qq.add_trace(go.Scatter(x=qq[0][0], y=qq[0][0]*qq[1][0]+qq[1][1], mode="lines",
                                 line=dict(color=CHART_SLATE)))
    fig_qq.update_layout(template="plotly_dark", showlegend=False)
    apply_neon_theme(fig_qq)
    chart_card(
        fig_qq,
        chart_id="explo_qqplot",
        title="QQ-Plot: prueba visual de normalidad",
        icon="📐",
        summary=[
            "<b>Eje X:</b> cuantiles teóricos de una distribución normal perfecta (en unidades "
            "de desviación estándar). <b>Eje Y:</b> cuantiles reales de tus datos, en kilogramos "
            "(kg). <b>Cada punto rosa:</b> un mes del histórico; <b>la línea recta:</b> dónde "
            "estarían los puntos si los datos fueran perfectamente normales.",
            "Un <b>QQ-Plot</b> (quantile-quantile plot) compara los cuantiles de los datos "
            "reales (puntos) contra los cuantiles que tendría una distribución normal perfecta "
            "(la línea recta).",
            "Sirve para juzgar la <b>normalidad</b> de la variable a simple vista: mientras más "
            "se pegan los puntos a la línea, más se parece la variable a una distribución "
            "normal; desviaciones sistemáticas en los extremos indican colas más pesadas o "
            "sesgo.",
            "Es el complemento visual de la prueba de <b>Shapiro-Wilk</b> que se muestra más "
            "abajo: si el valor p es bajo Y aquí los puntos se alejan de la línea, hay evidencia "
            "consistente de que la variable no es normal.",
        ],
    )

shapiro_stat, shapiro_p = stats.shapiro(df[TARGET_VARIABLE])
desc = df[TARGET_VARIABLE].describe()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Media", f"{desc['mean']:,.0f}")
c2.metric("Mediana", f"{df[TARGET_VARIABLE].median():,.0f}")
c3.metric("Desv. Estándar", f"{desc['std']:,.0f}")
c4.metric("Asimetría", f"{df[TARGET_VARIABLE].skew():.2f}")
c5.metric("Shapiro-Wilk (p)", f"{shapiro_p:.4f}")

st.page_link("pages/04_entrenamiento.py", label="Continuar a Entrenamiento →", icon="🧠")

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Interpretación del análisis exploratorio
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

_df_e = st.session_state.get("dataset_processed")
_ai_ctx_eda = {}

if _df_e is not None:
    import numpy as np
    from config.settings import TARGET_VARIABLE
    from src.ai.chart_knowledge import describe_correlation_matrix
    _serie = _df_e[TARGET_VARIABLE]
    _pct_cambio = ((_serie.iloc[-1] - _serie.iloc[0]) / _serie.iloc[0] * 100) if len(_serie) > 1 else 0
    _mes_cols = ["mes"] if "mes" in _df_e.columns else []
    if _mes_cols:
        _por_mes = _df_e.groupby("mes")[TARGET_VARIABLE].mean()
        _mes_mayor = int(_por_mes.idxmax())
        _mes_menor = int(_por_mes.idxmin())
    else:
        _mes_mayor = "N/D"
        _mes_menor = "N/D"

    _corr_trm = _df_e[TARGET_VARIABLE].corr(_df_e["trm_peso_dolar"]) if "trm_peso_dolar" in _df_e.columns else 0
    _corr_ipc = _df_e[TARGET_VARIABLE].corr(_df_e["ipc_variacion_mensual"]) if "ipc_variacion_mensual" in _df_e.columns else 0

    # Descriptor enriquecido: calcula TODAS las correlaciones contra el
    # objetivo (no solo TRM/IPC/top1), igual que la matriz de calor completa.
    # Esto permite que el chat responda sobre CUALQUIER variable que el
    # usuario mencione, no solo las 2-3 que se calculaban antes a mano.
    _numeric_cols = _df_e.select_dtypes(include=[np.number]).columns.tolist()
    _desc_corr = describe_correlation_matrix(_df_e[_numeric_cols], TARGET_VARIABLE)
    _var_top = _desc_corr.get("variable_mas_correlacionada", "N/D")
    _corr_top = _desc_corr.get("correlacion_top", 0)

    _ai_ctx_eda = {
        "tendencia": "creciente" if _pct_cambio > 5 else ("decreciente" if _pct_cambio < -5 else "estacionaria"),
        "pct_cambio_total": _pct_cambio,
        "mes_mayor_promedio": str(_mes_mayor),
        "mes_menor_promedio": str(_mes_menor),
        "anio_pico": str(_df_e.loc[_serie.idxmax(), "anio"]) if "anio" in _df_e.columns else "N/D",
        "correlacion_trm": _corr_trm,
        "correlacion_ipc": _corr_ipc,
        "variable_mas_correlacionada": _var_top,
        "correlacion_top": _corr_top,
        "resumen_todas_correlaciones": _desc_corr.get("resumen", ""),
    }

render_ai_panel(
    pagina="exploracion",
    contexto=_ai_ctx_eda,
    auto_trigger=(_df_e is not None),
    preguntas_sugeridas=[
        "¿Qué explica la estacionalidad observada en los volúmenes de importación?",
        "¿Por qué la TRM afecta el volumen de importación de insumos?",
        "¿Cómo se interpreta la descomposición de la serie de tiempo?",
    ],
    modo="expander",
)
