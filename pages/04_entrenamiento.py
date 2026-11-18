import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import (
    TARGET_VARIABLE, FEATURE_COLUMNS, MODELOS_CANDIDATOS, TRAIN_TEST_SPLIT_DATE,
    MODEL_COLORS, UMBRAL_MEJORA_RMSE,
)
from src.data.preprocessor import DataPreprocessor
from src.models.model_selector import ModelSelector, walk_forward_validation
from src.utils.helpers import apply_neon_theme
from src.utils.serializer import build_model_bundle_bytes

from components.page_setup import setup_page
user = setup_page("Entrenamiento", "🧠")

from src.data.persistence import save_current_snapshot, reset_downstream

st.markdown("## 🧠 Entrenamiento y Comparación de Modelos")

if st.session_state.get("dataset_processed") is None:
    st.warning("Primero carga y procesa los datos en el módulo **Carga de Datos**.")
    st.page_link("pages/02_carga_datos.py", label="Ir a Carga de Datos", icon="📥")
    st.stop()

df = st.session_state["dataset_processed"].copy()
df["fecha"] = pd.to_datetime(df["fecha"])

# --- SECCIÓN 1: CONFIGURACIÓN ---
st.markdown("#### Configuración del entrenamiento")
available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
col1, col2 = st.columns([2, 1])
with col1:
    selected_features = st.multiselect("Variables predictoras", available_features, default=available_features)
with col2:
    split_date = st.date_input("Fecha de corte train/test", pd.to_datetime(TRAIN_TEST_SPLIT_DATE))

col3, col4 = st.columns(2)
with col3:
    validation_method = st.radio("Método de validación", ["Hold-out temporal (recomendado)", "Walk-forward (5 splits)"])
with col4:
    selected_models = st.multiselect("Modelos a entrenar", MODELOS_CANDIDATOS, default=MODELOS_CANDIDATOS)

start_training = st.button("🚀 INICIAR ENTRENAMIENTO", type="primary", use_container_width=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

if start_training:
    if not selected_features or not selected_models:
        st.error("Selecciona al menos una variable predictora y un modelo.")
        st.stop()

    n_train = int((df["fecha"] < pd.to_datetime(split_date)).sum())
    n_test = len(df) - n_train
    if n_train < 12 or n_test < 3:
        st.error("El período de entrenamiento/prueba es demasiado corto. Ajusta la fecha de corte.")
        st.stop()

    pre = DataPreprocessor(TARGET_VARIABLE)
    # El escalado se ajusta SOLO con el periodo de entrenamiento (sin fuga de datos)
    df_scaled, scaler = pre.scale_features(df, selected_features, fit_before_date=split_date)
    X_train, X_test, y_train, y_test, dates_train, dates_test = pre.split_temporal(
        df_scaled, str(split_date), selected_features
    )

    # Un modelo nuevo invalida pronósticos, pruebas y SHAP del modelo anterior
    reset_downstream("entrenamiento")
    st.session_state.update({
        "X_train": X_train, "X_test": X_test, "y_train": y_train, "y_test": y_test,
        "dates_train": dates_train, "dates_test": dates_test,
        "feature_cols": selected_features, "preprocessor": pre, "scaler": scaler,
        "validation_method": "walk_forward" if validation_method.startswith("Walk") else "hold_out",
        "walk_forward_results": None,
    })

    progress_bar = st.progress(0, text="Iniciando entrenamiento...")
    log_box = st.empty()

    def progress_cb(step, total, name):
        pct = int(step / total * 100)
        progress_bar.progress(pct, text=f"Entrenando {name} — Modelo {step} de {total}")
        log_box.markdown(f'<div class="card-futurista" style="font-family:var(--font-mono);font-size:0.8rem;">'
                          f'✓ {name} entrenado y evaluado.</div>', unsafe_allow_html=True)
        time.sleep(0.15)

    selector = ModelSelector()
    with st.spinner("Ejecutando pipeline de entrenamiento..."):
        results_df = selector.compare_all_models(
            X_train, X_test, y_train, y_test,
            selected_models=selected_models, progress_callback=progress_cb,
        )
    progress_bar.progress(100, text="Entrenamiento completado ✓")

    best_info = selector.select_best_model()
    st.session_state["model_selector"] = selector
    st.session_state["comparison_results"] = results_df
    st.session_state["best_model_info"] = best_info

    if validation_method.startswith("Walk"):
        wf_bar = st.progress(0, text="Validación walk-forward...")
        try:
            wf = walk_forward_validation(
                df, selected_features, TARGET_VARIABLE, selected_models, n_splits=5,
                progress_callback=lambda s, tot, name: wf_bar.progress(
                    int(s / tot * 100), text=f"Walk-forward — {name}"),
            )
            st.session_state["walk_forward_results"] = wf
            wf_bar.progress(100, text="Walk-forward completado ✓")
        except ValueError as e:
            wf_bar.empty()
            st.warning(f"No se pudo hacer walk-forward: {e}")

    save_current_snapshot()
    st.success(f"✓ Modelo **{best_info['best_model_name']}** entrenado y guardado en tu historial.")

# --- SECCIÓN 3: RESULTADOS ---
if st.session_state.get("comparison_results") is not None:
    st.markdown("#### Resultados de la comparativa")
    results_df = st.session_state["comparison_results"]
    best_info = st.session_state["best_model_info"]

    def highlight_rows(row):
        if row["Modelo"] == "ARIMA":
            return ["background-color: rgba(128,128,176,0.15)"] * len(row)
        if row["Modelo"] == best_info["best_model_name"]:
            return ["background-color: rgba(108,99,255,0.14); border: 1px solid #6C63FF"] * len(row)
        return [""] * len(row)

    st.dataframe(results_df.style.apply(highlight_rows, axis=1), use_container_width=True)

    improvement = best_info["metrics"]["% Mejora vs ARIMA (RMSE)"]
    if best_info["hypothesis_confirmed"]:
        st.markdown(
            f'''<div class="metric-card improved">
            <strong>CRITERIO DEL 15 % CUMPLIDO</strong><br>
            El mejor modelo (<b>{best_info["best_model_name"]}</b>) mejora el RMSE en
            <b>{improvement:.1f}%</b> frente a ARIMA (umbral minimo: {UMBRAL_MEJORA_RMSE*100:.0f}%). La significancia estadistica de esta mejora se verifica en el modulo <b>Evaluacion</b>.
            </div>''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'''<div class="metric-card degraded">
            <strong>CRITERIO DEL 15 % NO CUMPLIDO</strong><br>
            El mejor modelo (<b>{best_info["best_model_name"]}</b>) mejora el RMSE en solo
            <b>{improvement:.1f}%</b> frente a ARIMA — no alcanza el umbral del {UMBRAL_MEJORA_RMSE*100:.0f}%.
            </div>''',
            unsafe_allow_html=True,
        )

    # --- Validación walk-forward (si se eligió) ---
    wf = st.session_state.get("walk_forward_results")
    if wf:
        st.markdown(f"#### Validación walk-forward — {wf['n_splits']} pliegues de {wf['horizonte']} meses")
        st.caption(
            "Cada pliegue entrena con todo el historial anterior y predice los meses siguientes. "
            "Un modelo robusto mantiene un RMSE bajo y estable (desviación pequeña) en todos los "
            "pliegues, no solo en el periodo de prueba único del hold-out."
        )
        st.dataframe(wf["resumen"], use_container_width=True, hide_index=True)
        ganador_wf = wf["resumen"][wf["resumen"]["Modelo"] != "ARIMA"].iloc[0]
        if ganador_wf["Modelo"] == best_info["best_model_name"]:
            st.success(f"El ganador del hold-out (**{best_info['best_model_name']}**) también tiene "
                       f"el menor RMSE medio en walk-forward: el resultado es consistente.")
        else:
            st.info(f"En walk-forward el menor RMSE medio lo obtiene **{ganador_wf['Modelo']}**, "
                    f"mientras que en hold-out gana **{best_info['best_model_name']}**. Conviene "
                    "mencionarlo en la discusión de resultados.")
        with st.expander("Ver detalle por pliegue"):
            st.dataframe(wf["detalle"], use_container_width=True, hide_index=True)

    # --- Descarga del modelo entrenado ---
    _bundle = build_model_bundle_bytes(
        best_info["best_model"], st.session_state.get("scaler"),
        st.session_state.get("feature_cols") or [], best_info["metrics"], best_info["best_model_name"],
    )
    st.download_button(
        "⬇️ Descargar modelo entrenado (.joblib)", _bundle,
        file_name=f"importpredic_{best_info['best_model_name'].replace(' ', '_').lower()}.joblib",
        mime="application/octet-stream",
        help="Incluye el modelo, el escalador, las variables usadas y sus métricas.",
    )

    # Gráfico de barras comparativo
    fig_bar = go.Figure()
    for metric in ["MAE", "RMSE"]:
        fig_bar.add_trace(go.Bar(
            x=results_df["Modelo"], y=results_df[metric], name=metric,
            marker_color=["#6C63FF" if metric == "RMSE" else "#FF6B81"] * len(results_df),
        ))
    fig_bar.update_layout(barmode="group", template="plotly_dark", title="Comparativa MAE / RMSE por modelo")
    apply_neon_theme(fig_bar)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- DETALLE DEL MEJOR MODELO ---
    st.markdown(f"#### Detalle del mejor modelo — {best_info['best_model_name']}")
    selector = st.session_state["model_selector"]
    y_test = st.session_state["y_test"]
    dates_test = st.session_state["dates_test"]
    y_pred_best = selector.predictions[best_info["best_model_name"]]

    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(x=dates_test, y=y_test, name="Real", line=dict(color="#94A3B8")))
    fig_pred.add_trace(go.Scatter(x=dates_test, y=y_pred_best, name="Predicho",
                                   line=dict(color=MODEL_COLORS.get(best_info["best_model_name"], "#6C63FF"))))
    fig_pred.update_layout(template="plotly_dark", title="Predicciones vs valores reales (test)")
    apply_neon_theme(fig_pred)
    st.plotly_chart(fig_pred, use_container_width=True)

    residuals = y_test.values - y_pred_best
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        fig_res = go.Figure(go.Scatter(x=dates_test, y=residuals, mode="lines+markers",
                                        line=dict(color="#2ECC8F")))
        fig_res.update_layout(template="plotly_dark", title="Residuos vs tiempo")
        apply_neon_theme(fig_res)
        st.plotly_chart(fig_res, use_container_width=True)
    with col_r2:
        fig_res_hist = go.Figure(go.Histogram(x=residuals, marker_color="#8B5CF6"))
        fig_res_hist.update_layout(template="plotly_dark", title="Histograma de residuos")
        apply_neon_theme(fig_res_hist)
        st.plotly_chart(fig_res_hist, use_container_width=True)

    st.page_link("pages/05_prediccion.py", label="Continuar a Predicción →", icon="📈")

# IA inline: interpretacion de residuos
from components.ai_panel import render_ai_insight
from src.ai.chart_knowledge import describe_residuos_vs_tiempo
if st.session_state.get("best_model_info"):
    _bi = st.session_state["best_model_info"]
    _res = y_test.values - y_pred_best if 'y_pred_best' in dir() else []
    import numpy as np
    from statsmodels.stats.stattools import durbin_watson as _dw

    # Descriptor enriquecido: tendencia, heterocedasticidad, fecha del
    # peor residuo y outliers -- no solo media/std sueltos como antes.
    _desc_res = describe_residuos_vs_tiempo(_res, dates_test) if len(_res) else {"resumen": "Sin datos"}

    render_ai_insight(
        pagina="entrenamiento", subtipo="residuos",
        contexto={
            "modelo": _bi.get("best_model_name","N/D"),
            "media_residuos": _desc_res.get("media_residuos", 0),
            "std_residuos": _desc_res.get("std_residuos", 0),
            "durbin_watson": float(_dw(_res)) if len(_res) > 2 else 2.0,
            "resumen_residuos": _desc_res.get("resumen", ""),
        },
        label="IA - ANALISIS DE RESIDUOS",
    )

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Interpretación del entrenamiento
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

_best = st.session_state.get("best_model_info")
_results = st.session_state.get("comparison_results")

_ai_ctx_train = {}
if _best and _results is not None:
    _ranking = [
        {"modelo": row["Modelo"], "rmse": row.get("RMSE", 0)}
        for _, row in _results.iterrows()
    ]
    _ai_ctx_train = {
        "mejor_modelo": _best.get("best_model_name", "N/D"),
        "rmse_mejor": _best.get("metrics", {}).get("RMSE", 0),
        "mae_mejor": _best.get("metrics", {}).get("MAE", 0),
        "r2_mejor": _best.get("metrics", {}).get("R2", 0),
        # FIX: antes se leía una clave inexistente ("RMSE_ARIMA") y la IA
        # siempre recibía 0 como RMSE de ARIMA.
        "rmse_arima": float(_results.loc[_results["Modelo"] == "ARIMA", "RMSE"].iloc[0])
        if (_results["Modelo"] == "ARIMA").any() else 0,
        "mejora_rmse_pct": _best.get("metrics", {}).get("% Mejora vs ARIMA (RMSE)", 0),
        "hipotesis_confirmada": _best.get("hypothesis_confirmed", False),
        "ranking": _ranking,
    }

render_ai_panel(
    pagina="entrenamiento",
    contexto=_ai_ctx_train,
    auto_trigger=(_best is not None),
    preguntas_sugeridas=[
        "¿Por qué XGBoost tiende a superar a los modelos lineales en series de tiempo?",
        "¿Qué significa el R² en el contexto de este modelo predictivo?",
        "¿Cómo se interpreta la curva de residuos del mejor modelo?",
    ],
    modo="expander",
)