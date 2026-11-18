import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import UMBRAL_MEJORA_RMSE
from src.evaluation.metrics import calculate_residuals_analysis
from src.evaluation.statistical_tests import run_complete_hypothesis_test
from src.utils.helpers import apply_neon_theme

from components.page_setup import setup_page
user = setup_page("Evaluación", "✅")

from src.data.persistence import save_current_snapshot

st.markdown("## ✅ Métricas y Pruebas Estadísticas")

if st.session_state.get("best_model_info") is None:
    st.warning("Primero entrena un modelo en el módulo **Entrenamiento**.")
    st.page_link("pages/04_entrenamiento.py", label="Ir a Entrenamiento", icon="🧠")
    st.stop()

best_info = st.session_state["best_model_info"]
selector = st.session_state["model_selector"]
y_test = st.session_state["y_test"]
dates_test = st.session_state["dates_test"]
model_name = best_info["best_model_name"]
y_pred_model = selector.predictions[model_name]
y_pred_arima = selector.predictions["ARIMA"]

# --- SECCIÓN 1: PANEL DE MÉTRICAS ---
st.markdown("#### Métricas principales")
m = best_info["metrics"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("MAE", f"{m['MAE']:,.0f} kg")
c2.metric("RMSE", f"{m['RMSE']:,.0f} kg", f"{m['% Mejora vs ARIMA (RMSE)']:+.1f}% vs ARIMA")
c3.metric("R²", f"{m['R2']:.3f}")
mape_color = "🟢" if m["MAPE"] < 10 else ("🟡" if m["MAPE"] < 20 else "🔴")
c4.metric("MAPE", f"{mape_color} {m['MAPE']:.2f}%")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 2: COMPARATIVA VISUAL ---
st.markdown("#### Comparativa visual: Modelo ML vs ARIMA")
fig = go.Figure()
fig.add_trace(go.Scatter(x=dates_test, y=y_test, name="Real", line=dict(color="#94A3B8", width=2)))
fig.add_trace(go.Scatter(x=dates_test, y=y_pred_model, name=model_name, line=dict(color="#6C63FF")))
fig.add_trace(go.Scatter(x=dates_test, y=y_pred_arima, name="ARIMA", line=dict(color="#8B5CF6", dash="dot")))
fig.update_layout(template="plotly_dark")
apply_neon_theme(fig)
st.plotly_chart(fig, use_container_width=True)

results_df = st.session_state["comparison_results"]
fig_metrics = go.Figure()
for metric in ["MAE", "RMSE"]:
    fig_metrics.add_trace(go.Bar(x=results_df["Modelo"], y=results_df[metric], name=metric))
fig_metrics.update_layout(barmode="group", template="plotly_dark")
apply_neon_theme(fig_metrics)
st.plotly_chart(fig_metrics, use_container_width=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 3: ANÁLISIS DE RESIDUOS ---
st.markdown("#### Análisis de residuos")
res_analysis = calculate_residuals_analysis(y_test.values, y_pred_model)
st.session_state["residuals_analysis"] = res_analysis
col1, col2 = st.columns(2)
with col1:
    fig_res = go.Figure(go.Scatter(x=dates_test, y=res_analysis["residuals"], mode="lines+markers",
                                    line=dict(color="#2ECC8F")))
    fig_res.update_layout(template="plotly_dark", title="Residuos en el tiempo")
    apply_neon_theme(fig_res)
    st.plotly_chart(fig_res, use_container_width=True)
with col2:
    fig_hist = go.Figure(go.Histogram(x=res_analysis["residuals"], marker_color="#FF6B81", histnorm="probability density"))
    fig_hist.update_layout(template="plotly_dark", title="Distribución de residuos")
    apply_neon_theme(fig_hist)
    st.plotly_chart(fig_hist, use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.metric("Media residuos", f"{res_analysis['media']:.1f}")
c2.metric("Asimetría", f"{res_analysis['skewness']:.2f}")
c3.metric("Durbin-Watson", f"{res_analysis['durbin_watson']:.2f}")
st.caption("Durbin-Watson cercano a 2 indica ausencia de autocorrelación serial en los residuos.")

# IA inline: descripcion real de residuos vs tiempo (mismo descriptor que Entrenamiento)
from components.ai_panel import render_ai_insight
from src.ai.chart_knowledge import describe_residuos_vs_tiempo
_desc_res_eval = describe_residuos_vs_tiempo(res_analysis["residuals"], dates_test)
render_ai_insight(
    pagina="evaluacion", subtipo="residuos_detalle",
    contexto={
        "modelo": model_name,
        "media_residuos": _desc_res_eval.get("media_residuos", 0),
        "std_residuos": _desc_res_eval.get("std_residuos", 0),
        "durbin_watson": float(res_analysis["durbin_watson"]),
        "resumen_residuos": _desc_res_eval.get("resumen", ""),
    },
    label="IA - Detalle de Residuos",
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 4: PRUEBAS ESTADÍSTICAS ---
st.markdown("#### Pruebas estadísticas — Verificación de hipótesis")
# Se calculan una sola vez por modelo entrenado (antes se recalculaban y se
# guardaban en disco en CADA interacción con la página).
if st.session_state.get("hyp_results") is None:
    with st.spinner("Ejecutando pruebas estadísticas..."):
        st.session_state["hyp_results"] = run_complete_hypothesis_test(
            y_test.values, y_pred_arima, y_pred_model
        )
        st.session_state["residuals_analysis"] = res_analysis
        save_current_snapshot()
hyp_results = st.session_state["hyp_results"]

test_table = pd.DataFrame([
    {"Prueba": "Shapiro-Wilk (normalidad de residuos)",
     "Estadístico": hyp_results["shapiro_wilk"]["statistic"],
     "p-valor": hyp_results["shapiro_wilk"]["p_value"],
     "Conclusión": hyp_results["shapiro_wilk"]["conclusion"]},
    {"Prueba": f"Diebold-Mariano (poder predictivo)",
     "Estadístico": hyp_results["diebold_mariano"]["dm_stat"],
     "p-valor": hyp_results["diebold_mariano"]["p_value"],
     "Conclusión": hyp_results["diebold_mariano"]["conclusion"]},
    {"Prueba": hyp_results["test_used"],
     "Estadístico": hyp_results["parametric_test"].get("statistic", hyp_results["parametric_test"].get("t_statistic")),
     "p-valor": hyp_results["parametric_test"]["p_value"],
     "Conclusión": hyp_results["parametric_test"]["conclusion"]},
])
st.dataframe(test_table, use_container_width=True)

if hyp_results["hypothesis_confirmed"]:
    st.markdown(
        f'''<div class="metric-card improved">
        <strong>HIPOTESIS CONFIRMADA</strong><br>
        {hyp_results["final_conclusion"]}
        </div>''',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'''<div class="metric-card degraded">
        <strong>HIPOTESIS NO CONFIRMADA</strong><br>
        {hyp_results["final_conclusion"]}
        </div>''',
        unsafe_allow_html=True,
    )

with st.expander("¿Qué significa cada prueba? (explicación no técnica)"):
    st.markdown(
        "- **Shapiro-Wilk**: verifica si los errores del modelo siguen una distribución normal, "
        "lo que determina qué prueba de comparación usar después.\n"
        "- **Diebold-Mariano**: compara directamente la precisión predictiva de dos modelos "
        "(el modelo ML vs ARIMA) y determina si la diferencia es estadísticamente significativa.\n"
        "- **t-test / Wilcoxon**: confirma si el error promedio del modelo ML es significativamente "
        "menor que el del ARIMA."
    )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 5: ESTABILIDAD ---
st.markdown("#### Análisis de estabilidad (concept drift)")
test_df = pd.DataFrame({"fecha": dates_test.values, "real": y_test.values, "pred": y_pred_model})
test_df["cuatrimestre"] = pd.to_datetime(test_df["fecha"]).dt.to_period("Q").astype(str)
stability = test_df.groupby("cuatrimestre").apply(
    lambda d: np.sqrt(np.mean((d["real"] - d["pred"]) ** 2))
).reset_index(name="RMSE")

fig_stab = go.Figure(go.Bar(x=stability["cuatrimestre"], y=stability["RMSE"], marker_color="#6C63FF"))
fig_stab.update_layout(template="plotly_dark", title="RMSE por cuatrimestre del período de prueba")
apply_neon_theme(fig_stab)
st.plotly_chart(fig_stab, use_container_width=True)

if len(stability) > 1:
    degradation = (stability["RMSE"].iloc[-1] - stability["RMSE"].iloc[0]) / stability["RMSE"].iloc[0] * 100
    if degradation > 20:
        st.warning(f"⚠️ El RMSE se degradó {degradation:.1f}% entre el primer y último cuatrimestre del test.")
    else:
        st.success(f"El desempeño del modelo se mantiene estable a lo largo del período de prueba ({degradation:+.1f}%).")

st.page_link("pages/07_interpretabilidad.py", label="Continuar a Interpretabilidad →", icon="🧩")

# IA inline: estabilidad del modelo
from components.ai_panel import render_ai_insight
if st.session_state.get("best_model_info") and len(stability) > 1:
    # Incluir el desglose COMPLETO por cuatrimestre, no solo inicial/final.
    # Sin esto, si el usuario pregunta por los valores intermedios, la IA
    # no tiene ese dato y puede inventarlo.
    _desglose_txt = " | ".join(
        "{}: RMSE={:,.0f} kg".format(row["cuatrimestre"], row["RMSE"])
        for _, row in stability.iterrows()
    )
    render_ai_insight(
        pagina="evaluacion", subtipo="estabilidad",
        contexto={
            "degradacion_pct": float(degradation) if 'degradation' in dir() else 0,
            "rmse_inicial": float(stability["RMSE"].iloc[0]),
            "rmse_final": float(stability["RMSE"].iloc[-1]),
            "desglose_completo_cuatrimestres": _desglose_txt,
        },
        label="IA - ESTABILIDAD TEMPORAL DEL MODELO",
    )

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Interpretación de métricas y pruebas estadísticas
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

_best_e = st.session_state.get("best_model_info")
_ai_ctx_eval = {}

if _best_e is not None:
    _m = _best_e.get("metrics", {})

    # Usar los valores REALES ya calculados por run_complete_hypothesis_test()
    # en esta misma pagina (hyp_results), en vez de claves MAE_ARIMA/RMSE_ARIMA
    # que no existen en el diccionario de metricas, y en vez del p-valor
    # con default falso de 0.05.
    _dm_pvalue = hyp_results["diebold_mariano"]["p_value"] if "hyp_results" in dir() else 1.0
    _dm_concl = hyp_results["diebold_mariano"]["conclusion"] if "hyp_results" in dir() else "N/D"
    _shapiro_pvalue = hyp_results["shapiro_wilk"]["p_value"] if "hyp_results" in dir() else 0

    # Buscar RMSE de ARIMA directamente en la tabla comparativa (results_df),
    # que es la fuente de verdad de todas las metricas por modelo.
    _rmse_arima_real = 0
    _mae_arima_real = 0
    if "results_df" in dir() and "ARIMA" in results_df["Modelo"].values:
        _fila_arima = results_df[results_df["Modelo"] == "ARIMA"].iloc[0]
        _rmse_arima_real = float(_fila_arima.get("RMSE", 0))
        _mae_arima_real = float(_fila_arima.get("MAE", 0))

    _ai_ctx_eval = {
        "modelo": _best_e.get("best_model_name", "N/D"),
        "mae": _m.get("MAE", 0),
        "rmse": _m.get("RMSE", 0),
        "r2": _m.get("R2", 0),
        "mape": _m.get("MAPE", 0),
        "mae_arima": _mae_arima_real,
        "rmse_arima": _rmse_arima_real,
        "mejora_rmse_pct": _m.get("% Mejora vs ARIMA (RMSE)", 0),
        "p_valor_dm": _dm_pvalue,
        "dm_conclusion": _dm_concl,
        "prueba_normalidad": "Shapiro-Wilk",
        "p_valor_normalidad": _shapiro_pvalue,
        "hipotesis_confirmada": _best_e.get("hypothesis_confirmed", False),
        # Datos adicionales para que el CHAT LIBRE tambien pueda responder
        # sobre residuos y estabilidad sin inventar, sin depender solo
        # de los render_ai_insight especificos de cada grafico.
        "resumen_residuos": _desc_res_eval.get("resumen", "") if "_desc_res_eval" in dir() else "",
        "durbin_watson": float(res_analysis["durbin_watson"]) if "res_analysis" in dir() else 0,
        "asimetria_residuos": float(res_analysis["skewness"]) if "res_analysis" in dir() else 0,
        "desglose_cuatrimestres": (
            " | ".join(
                "{}: RMSE={:,.0f} kg".format(row["cuatrimestre"], row["RMSE"])
                for _, row in stability.iterrows()
            ) if "stability" in dir() else "no disponible"
        ),
        "pruebas_disponibles_en_sistema": (
            "Shapiro-Wilk (normalidad), Diebold-Mariano (comparacion de modelos), "
            "Durbin-Watson (autocorrelacion de residuos). El sistema NO implementa "
            "Breusch-Pagan, White test, ni otras pruebas de heterocedasticidad formales."
        ),
    }

render_ai_panel(
    pagina="evaluacion",
    contexto=_ai_ctx_eval,
    auto_trigger=(_best_e is not None),
    preguntas_sugeridas=[
        "¿Qué significa el p-valor de la prueba Diebold-Mariano?",
        "¿Cómo se interpreta un R² de 0.85 en un modelo de series de tiempo?",
        "¿Qué implica confirmar la hipótesis para el proyecto de grado?",
    ],
    modo="expander",
)