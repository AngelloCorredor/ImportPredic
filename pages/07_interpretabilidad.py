import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.interpretability.feature_importance import (
    FeatureImportanceAnalyzer, TREE_MODELS, LINEAR_MODELS, get_linear_coefficients_interpretation,
)
from src.utils.helpers import apply_neon_theme

from components.page_setup import setup_page
user = setup_page("Interpretabilidad", "🧩")

from src.data.persistence import save_current_snapshot

st.markdown("## 🧩 Análisis de Interpretabilidad")

if st.session_state.get("best_model_info") is None:
    st.warning("Primero entrena un modelo en el módulo **Entrenamiento**.")
    st.page_link("pages/04_entrenamiento.py", label="Ir a Entrenamiento", icon="🧠")
    st.stop()

best_info = st.session_state["best_model_info"]
model_name = best_info["best_model_name"]
model_wrapper = best_info["best_model"]
X_train = st.session_state["X_train"]
X_test = st.session_state["X_test"]
dates_test = st.session_state["dates_test"]

if model_name in TREE_MODELS:
    st.markdown(f"#### Importancia global de variables — {model_name} (SHAP TreeExplainer)")
    with st.spinner("Calculando SHAP values..."):
        analyzer = FeatureImportanceAnalyzer(model_wrapper, model_name, X_train)
        shap_values = analyzer.compute_shap_values(X_test)
        importance_df = analyzer.get_global_importance()
        _ya_guardado = st.session_state.get("shap_importance_df") is not None
        st.session_state["shap_importance_df"] = importance_df
        if not _ya_guardado:
            save_current_snapshot()

    fig_imp = go.Figure(go.Bar(
        x=importance_df["mean_abs_shap"], y=importance_df["variable"], orientation="h",
        marker=dict(color=importance_df["mean_abs_shap"], colorscale=[[0, "#E4E1F7"], [1, "#6C63FF"]]),
    ))
    fig_imp.update_layout(template="plotly_dark", title="Importancia global (mean |SHAP value|)",
                           yaxis=dict(autorange="reversed"))
    apply_neon_theme(fig_imp)
    st.plotly_chart(fig_imp, use_container_width=True)

    top3 = importance_df.head(3)["variable"].tolist()
    st.markdown(
        " ".join([f'<span class="badge-insumo">🔥 {v}</span>' for v in top3]) +
        ' <span style="color:var(--text-secondary);">— variables de mayor influencia</span>',
        unsafe_allow_html=True,
    )

    # IA inline: importancia global real calculada por SHAP
    from components.ai_panel import render_ai_insight
    from src.ai.chart_knowledge import describe_shap_importance
    _shap_dict = dict(zip(importance_df["variable"], importance_df["mean_abs_shap"]))
    _desc_shap_global = describe_shap_importance(_shap_dict)
    render_ai_insight(
        pagina="interpretabilidad", subtipo="shap_global",
        contexto={
            "modelo": model_name,
            "top_variables": [{"variable": k, "importancia": v} for k, v in _desc_shap_global.get("ranking_completo", [])[:5]],
            "variable_principal": _desc_shap_global.get("variable_principal", "N/D"),
            "direccion_principal": "positiva",
            "resumen_shap": _desc_shap_global.get("resumen", ""),
        },
        label="IA - Importancia Global SHAP",
    )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # SHAP summary-like scatter
    st.markdown("#### SHAP Summary Plot")
    top_var = importance_df.iloc[0]["variable"]
    var_idx = list(X_test.columns).index(top_var)
    fig_summary = go.Figure(go.Scatter(
        x=shap_values[:, var_idx], y=X_test[top_var], mode="markers",
        marker=dict(color=X_test[top_var], colorscale=[[0, "#6C63FF"], [1, "#FF6B81"]], showscale=True),
    ))
    fig_summary.update_layout(template="plotly_dark", title=f"Impacto de '{top_var}' en la predicción",
                               xaxis_title="SHAP value", yaxis_title=f"Valor de {top_var} (escalado)")
    apply_neon_theme(fig_summary)
    st.plotly_chart(fig_summary, use_container_width=True)

    # IA inline: SHAP summary plot con datos reales (correlacion entre
    # el valor de la variable y su SHAP value, calculada sobre los
    # mismos datos del grafico). Antes esta grafica no tenia ningun
    # render_ai_insight conectado, por lo que preguntas sobre ella
    # causaban respuestas vacias o inventadas.
    import numpy as np
    _corr_shap_valor = float(np.corrcoef(shap_values[:, var_idx], X_test[top_var])[0, 1])
    _direccion_real = "positiva (valores altos de la variable aumentan la prediccion)" if _corr_shap_valor > 0 else "negativa (valores altos de la variable reducen la prediccion)"
    render_ai_insight(
        pagina="interpretabilidad", subtipo="shap_summary",
        contexto={
            "modelo": model_name,
            "variable_analizada": top_var,
            "correlacion_valor_shap": _corr_shap_valor,
            "direccion_relacion": _direccion_real,
            "n_observaciones": len(X_test),
            "shap_min": float(shap_values[:, var_idx].min()),
            "shap_max": float(shap_values[:, var_idx].max()),
        },
        label="IA - SHAP Summary Plot",
    )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Waterfall individual
    st.markdown("#### Análisis individual (SHAP Waterfall)")
    idx = st.selectbox("Selecciona una observación (fecha)", options=range(len(dates_test)),
                        format_func=lambda i: pd.to_datetime(dates_test.values[i]).strftime("%Y-%m"))
    wf = analyzer.get_waterfall_data(idx)
    fig_wf = go.Figure(go.Bar(
        x=wf["contributions"][:8], y=wf["variables"][:8], orientation="h",
        marker_color=["#2ECC8F" if c > 0 else "#FF6B81" for c in wf["contributions"][:8]],
    ))
    fig_wf.update_layout(template="plotly_dark", title=f"Contribución de variables — base: {wf['base_value']:,.0f} kg",
                          yaxis=dict(autorange="reversed"))
    apply_neon_theme(fig_wf)
    st.plotly_chart(fig_wf, use_container_width=True)

    # IA inline: waterfall individual con los datos reales de ESA
    # observacion especifica seleccionada por el usuario. Antes esta
    # grafica no tenia ningun render_ai_insight conectado.
    _fecha_obs = pd.to_datetime(dates_test.values[idx]).strftime("%Y-%m")
    _contribs_pos = [(v, c) for v, c in zip(wf["variables"][:8], wf["contributions"][:8]) if c > 0]
    _contribs_neg = [(v, c) for v, c in zip(wf["variables"][:8], wf["contributions"][:8]) if c < 0]
    _pred_final = wf["base_value"] + sum(wf["contributions"])
    render_ai_insight(
        pagina="interpretabilidad", subtipo="waterfall",
        contexto={
            "fecha_observacion": _fecha_obs,
            "valor_base": float(wf["base_value"]),
            "prediccion_final": float(_pred_final),
            "variables_positivas": ", ".join("{} (+{:,.0f})".format(v, c) for v, c in _contribs_pos) or "ninguna",
            "variables_negativas": ", ".join("{} ({:,.0f})".format(v, c) for v, c in _contribs_neg) or "ninguna",
        },
        label="IA - Waterfall Individual ({})".format(_fecha_obs),
    )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Interpretación narrativa
    st.markdown("#### Interpretación narrativa automática")
    narrative = analyzer.interpret_results(importance_df)
    st.markdown(f'<div class="card-futurista">{narrative}</div>', unsafe_allow_html=True)

elif model_name in LINEAR_MODELS:
    st.markdown(f"#### Coeficientes del modelo — {model_name}")
    if hasattr(model_wrapper, "get_coefficients"):
        coef_df = model_wrapper.get_coefficients(X_test.columns.tolist())
        fig_coef = go.Figure(go.Bar(
            x=coef_df["coeficiente"], y=coef_df["variable"], orientation="h",
            marker_color=["#2ECC8F" if c > 0 else "#FF6B81" for c in coef_df["coeficiente"]],
        ))
        fig_coef.update_layout(template="plotly_dark", title="Coeficientes del modelo lineal",
                                yaxis=dict(autorange="reversed"))
        apply_neon_theme(fig_coef)
        st.plotly_chart(fig_coef, use_container_width=True)
        st.markdown(f'<div class="card-futurista">{get_linear_coefficients_interpretation(coef_df)}</div>',
                     unsafe_allow_html=True)

st.page_link("pages/08_reporte.py", label="Continuar a Reporte Final →", icon="📄")

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Interpretación de SHAP values e importancia de variables
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

_best_i = st.session_state.get("best_model_info")
_ai_ctx_interp = {}

if _best_i is not None:
    _nombre = _best_i.get("best_model_name", "N/D")
    # Usar la importancia real calculada por SHAP en esta misma pagina
    # (importance_df), no un fallback hardcodeado a "trm_peso_dolar".
    from src.ai.chart_knowledge import describe_shap_importance
    _importancias_reales = {}
    if "importance_df" in dir() and importance_df is not None:
        _importancias_reales = dict(zip(importance_df["variable"], importance_df["mean_abs_shap"]))
    elif "coef_df" in dir() and coef_df is not None:
        _importancias_reales = dict(zip(coef_df["variable"], coef_df["coeficiente"].abs()))

    _desc_shap = describe_shap_importance(_importancias_reales)
    _top_vars = [
        {"variable": k, "importancia": v} for k, v in _desc_shap.get("ranking_completo", [])[:5]
    ]
    _var_principal = _desc_shap.get("variable_principal", "N/D")

    _ai_ctx_interp = {
        "modelo": _nombre,
        "top_variables": _top_vars,
        "variable_principal": _var_principal,
        "direccion_principal": "positiva" if _var_principal != "N/D" else "N/D",
        "resumen_shap": _desc_shap.get("resumen", ""),
    }

render_ai_panel(
    pagina="interpretabilidad",
    contexto=_ai_ctx_interp,
    auto_trigger=(_best_i is not None),
    preguntas_sugeridas=[
        "¿Por qué la TRM (tipo de cambio) tiene tanta influencia en las importaciones?",
        "¿Qué diferencia hay entre SHAP values e importancia por ganancia?",
        "¿Cómo uso estos resultados para mejorar la planificación del abastecimiento?",
    ],
    modo="expander",
)