import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import TARGET_VARIABLE, HORIZONTE_PREDICCION_MESES
from src.utils.helpers import apply_neon_theme

from components.page_setup import setup_page
user = setup_page("Predicción", "📈")

from src.data.persistence import save_current_snapshot

st.markdown("## 📈 Generación de Pronósticos")

if st.session_state.get("best_model_info") is None:
    st.warning("Primero entrena un modelo en el módulo **Entrenamiento**.")
    st.page_link("pages/04_entrenamiento.py", label="Ir a Entrenamiento", icon="🧠")
    st.stop()

best_info = st.session_state["best_model_info"]
model_name = best_info["best_model_name"]
model_wrapper = best_info["best_model"]
feature_cols = st.session_state["feature_cols"]
df = st.session_state["dataset_processed"].copy()
df["fecha"] = pd.to_datetime(df["fecha"])
scaler = st.session_state.get("scaler")

st.info(f"Modelo activo: **{model_name}**")

# --- SECCIÓN 1: CONFIGURACIÓN ---
st.markdown("#### Configuración del pronóstico")
col1, col2 = st.columns(2)
with col1:
    horizon = st.slider("Horizonte de predicción (meses)", 1, 24, HORIZONTE_PREDICCION_MESES)
with col2:
    manual_macro = st.checkbox("Ajustar manualmente variables macroeconómicas futuras")

manual_values = {}
if manual_macro:
    st.markdown("**Valores esperados (constantes durante el horizonte):**")
    cols = st.columns(4)
    macro_vars = [c for c in ["trm_peso_dolar", "ipc_variacion_mensual", "tasa_interes_referencia", "ipi_manufacturero"] if c in feature_cols]
    for i, var in enumerate(macro_vars):
        with cols[i % 4]:
            manual_values[var] = st.number_input(var, value=float(df[var].iloc[-1]))

generate = st.button("🎯 GENERAR PRONÓSTICO", type="primary", use_container_width=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

if generate or st.session_state.get("predictions_future") is not None:
    if generate:
        history = df[TARGET_VARIABLE].tolist()
        last_date = df["fecha"].max()

        future_rows = []
        for step in range(1, horizon + 1):
            next_date = last_date + pd.DateOffset(months=step)
            row = {}
            row["mes"] = next_date.month
            row["anio"] = next_date.year

            for var in ["trm_peso_dolar", "ipc_variacion_mensual", "tasa_interes_referencia", "ipi_manufacturero"]:
                if var in feature_cols:
                    row[var] = manual_values.get(var, df[var].tail(6).mean())
            if "valor_fob_usd" in feature_cols:
                row["valor_fob_usd"] = df["valor_fob_usd"].tail(6).mean()

            row["lag_1"] = history[-1]
            row["lag_3"] = history[-3] if len(history) >= 3 else history[-1]
            row["lag_12"] = history[-12] if len(history) >= 12 else history[-1]
            row["rolling_mean_3"] = np.mean(history[-3:])
            row["rolling_std_6"] = np.std(history[-6:]) if len(history) >= 6 else np.std(history)

            X_row = pd.DataFrame([{c: row.get(c, 0) for c in feature_cols}])
            if scaler is not None:
                X_row_scaled = pd.DataFrame(scaler.transform(X_row), columns=feature_cols)
            else:
                X_row_scaled = X_row

            y_pred = float(model_wrapper.predict(X_row_scaled)[0])
            history.append(y_pred)
            future_rows.append({"fecha": next_date, "prediccion": y_pred})

        future_df = pd.DataFrame(future_rows)
        rmse = best_info["metrics"]["RMSE"]
        future_df["limite_inferior"] = (future_df["prediccion"] - 1.96 * rmse).clip(lower=0)
        future_df["limite_superior"] = future_df["prediccion"] + 1.96 * rmse
        future_df["variacion_mensual_%"] = future_df["prediccion"].pct_change().fillna(0) * 100
        st.session_state["predictions_future"] = future_df
        save_current_snapshot()
    else:
        future_df = st.session_state["predictions_future"]

    # ---------------------------------------------------------------
    # CONTEXTO IA — se define ANTES de cualquier render_ai_insight
    # ---------------------------------------------------------------
    _best_p = st.session_state.get("best_model_info")
    _rmse = _best_p.get("metrics", {}).get("RMSE", 0) if _best_p else 0
    _banda_ancho = 2 * 1.96 * _rmse
    _total_kg = float(future_df["prediccion"].sum())
    _ai_ctx_pred = {
        "modelo_usado":              model_name,
        "horizonte_meses":           len(future_df),
        "total_proyectado_kg":       _total_kg,
        "mes_mayor_pronostico":      str(future_df.loc[future_df["prediccion"].idxmax(), "fecha"]),
        "mes_menor_pronostico":      str(future_df.loc[future_df["prediccion"].idxmin(), "fecha"]),
        "variacion_vs_anio_anterior_pct": 0,
        "incertidumbre_promedio_pct": round(_banda_ancho / _total_kg * 100, 1) if _total_kg else 0,
        "escenario":                 "base",
        "rmse_modelo":               _rmse,
        "ancho_promedio_banda":      _banda_ancho,
        "mes_mayor_incertidumbre":   str(future_df["fecha"].iloc[-1]),
    }

    # --- SECCIÓN 2: GRÁFICO PRINCIPAL ---
    st.markdown("#### Pronóstico de volumen de importación")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df[TARGET_VARIABLE],
        name="Histórico", line=dict(color="#94A3B8"),
    ))
    fig.add_trace(go.Scatter(
        x=future_df["fecha"], y=future_df["limite_superior"],
        line=dict(width=0), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=future_df["fecha"], y=future_df["limite_inferior"],
        fill="tonexty", fillcolor="rgba(108,99,255,0.14)",
        line=dict(width=0), name="Banda de confianza 95%",
    ))
    fig.add_trace(go.Scatter(
        x=future_df["fecha"], y=future_df["prediccion"],
        name="Pronóstico", line=dict(color="#6C63FF", width=3),
    ))
    fig.add_vline(
        x=df["fecha"].max().timestamp() * 1000,
        line_dash="dash", line_color="#FF6B81",
    )
    fig.update_layout(template="plotly_dark", title=f"Horizonte de {horizon} meses")
    apply_neon_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- SECCIÓN 3: TABLA ---
    st.markdown("#### Tabla de pronósticos detallada")
    display_df = future_df.copy()
    display_df["fecha"] = display_df["fecha"].dt.strftime("%Y-%m")
    display_df.columns = [
        "Mes", "Volumen Estimado (kg)",
        "Límite Inferior", "Límite Superior",
        "Variación % vs mes anterior",
    ]
    st.dataframe(
        display_df.style.format({
            "Volumen Estimado (kg)":       "{:,.0f}",
            "Límite Inferior":             "{:,.0f}",
            "Límite Superior":             "{:,.0f}",
            "Variación % vs mes anterior": "{:+.1f}%",
        }),
        use_container_width=True,
    )

    csv = future_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar pronósticos (CSV)",
        csv, "pronosticos_importpredic.csv", "text/csv",
    )

    total_year = future_df["prediccion"].sum()
    last_year_actual = df[
        df["fecha"] >= df["fecha"].max() - pd.DateOffset(months=12)
    ][TARGET_VARIABLE].sum()
    variation = (
        (total_year - last_year_actual) / last_year_actual * 100
        if last_year_actual else 0
    )
    st.metric(
        "Total proyectado del horizonte",
        f"{total_year:,.0f} kg",
        f"{variation:+.1f}% vs 12 meses previos",
    )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- SECCIÓN 4: RECOMENDACIONES ---
    st.markdown("#### Recomendaciones de abastecimiento")
    top_month = future_df.loc[future_df["prediccion"].idxmax()]
    wide_band = future_df.loc[
        (future_df["limite_superior"] - future_df["limite_inferior"]).idxmax()
    ]
    st.markdown(
        f"- Para **{top_month['fecha'].strftime('%B %Y')}**, se proyecta el mayor volumen "
        f"del horizonte: aproximadamente **{top_month['prediccion']:,.0f} kg**. "
        f"Se recomienda planificar la importación con anticipación.\n"
        f"- El mes con mayor incertidumbre en el pronóstico es "
        f"**{wide_band['fecha'].strftime('%B %Y')}** (banda de confianza más amplia)."
    )

    # IA inline: analisis de la banda de confianza
    # _ai_ctx_pred ya esta definido arriba — sin NameError
    from components.ai_panel import render_ai_insight
    render_ai_insight(
        pagina="prediccion",
        subtipo="banda",
        contexto=_ai_ctx_pred,
        label="IA - Banda de Confianza 95%",
    )

    st.page_link("pages/06_evaluacion.py", label="Continuar a Evaluación →", icon="✅")

# ---------------------------------------------------------------------------
# PANEL IA PRINCIPAL
# _ai_ctx_pred puede no existir si no hay predicciones aun — se protege
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

_pred_panel = st.session_state.get("predictions_future")
_best_panel  = st.session_state.get("best_model_info")

# Construir contexto solo si hay datos — evita NameError en cualquier escenario
if _pred_panel is not None and _best_panel is not None:
    _rmse_p    = _best_panel.get("metrics", {}).get("RMSE", 0)
    _banda_p   = 2 * 1.96 * _rmse_p
    _total_p   = float(_pred_panel["prediccion"].sum())
    _ctx_panel = {
        "modelo_usado":              _best_panel.get("best_model_name", "N/D"),
        "horizonte_meses":           len(_pred_panel),
        "total_proyectado_kg":       _total_p,
        "mes_mayor_pronostico":      str(_pred_panel.loc[_pred_panel["prediccion"].idxmax(), "fecha"]),
        "mes_menor_pronostico":      str(_pred_panel.loc[_pred_panel["prediccion"].idxmin(), "fecha"]),
        "variacion_vs_anio_anterior_pct": 0,
        "incertidumbre_promedio_pct": round(_banda_p / _total_p * 100, 1) if _total_p else 0,
        "escenario":                 "base",
        "rmse_modelo":               _rmse_p,
        "ancho_promedio_banda":      _banda_p,
        "mes_mayor_incertidumbre":   str(_pred_panel["fecha"].iloc[-1]),
    }
    _auto = True
else:
    _ctx_panel = {}
    _auto = False

render_ai_panel(
    pagina="prediccion",
    contexto=_ctx_panel,
    auto_trigger=_auto,
    preguntas_sugeridas=[
        "¿En qué meses se recomienda anticipar los pedidos de compresores herméticos?",
        "¿Cómo afecta una subida del dólar al volumen proyectado de importaciones?",
        "¿Qué significa la banda de confianza del 95% en el pronóstico?",
    ],
    modo="expander",
)