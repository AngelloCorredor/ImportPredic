from datetime import datetime

import pandas as pd
import streamlit as st

from config.settings import ACADEMIC_INFO, INSUMOS_CRITICOS, TARGET_VARIABLE, MODEL_COLORS
from src.reports.pdf_report import build_report_pdf
from src.reports.excel_report import (
    build_comparativa_excel, build_datos_excel, build_pronosticos_excel, build_metadata_excel,
)

from components.page_setup import setup_page
user = setup_page("Reporte", "📄")


st.markdown("## 📄 Reporte Final del Proyecto")

if st.session_state.get("best_model_info") is None:
    st.warning("Primero entrena un modelo en el módulo **Entrenamiento**.")
    st.page_link("pages/04_entrenamiento.py", label="Ir a Entrenamiento", icon="🧠")
    st.stop()

best_info = st.session_state["best_model_info"]
results_df = st.session_state["comparison_results"]

# --- SECCIÓN 1: RESUMEN EJECUTIVO ---
st.markdown("#### Resumen ejecutivo")
st.markdown(
    f'''<div class="card-futurista">
    <p><b>Período analizado:</b> {ACADEMIC_INFO["periodo_analisis"]}</p>
    <p><b>Insumos críticos:</b> {", ".join(INSUMOS_CRITICOS.keys())}</p>
    <p><b>Mejor modelo:</b> <span class="neon-text-cyan">{best_info["best_model_name"]}</span></p>
    <p><b>RMSE:</b> {best_info["metrics"]["RMSE"]:,.0f} kg · <b>MAE:</b> {best_info["metrics"]["MAE"]:,.0f} kg ·
       <b>R²:</b> {best_info["metrics"]["R2"]:.3f} · <b>MAPE:</b> {best_info["metrics"]["MAPE"]:.2f}%</p>
    <p><b>Mejora vs ARIMA (RMSE):</b> {best_info["metrics"]["% Mejora vs ARIMA (RMSE)"]:.1f}%</p>
    <p><b>Criterio de mejora del 15 %:</b> {"✓ Cumplido" if best_info["hypothesis_confirmed"] else "✗ No cumplido"} &nbsp;·&nbsp; <b>Hipótesis (pruebas estadísticas):</b> {("✓ Confirmada" if st.session_state["hyp_results"]["hypothesis_confirmed"] else "✗ No confirmada (p ≥ 0,05)") if st.session_state.get("hyp_results") else "ver módulo Evaluación"}</p>
    </div>''',
    unsafe_allow_html=True,
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 2: CONFIGURACIÓN DEL REPORTE ---
st.markdown("#### Configuración del reporte")
report_name = st.text_input("Nombre del reporte", value="ImportPredic_Reporte_Final")
sections = st.multiselect(
    "Secciones a incluir",
    ["Estadísticas descriptivas", "Métricas del modelo", "Pruebas estadísticas",
     "Importancia de variables", "Pronósticos futuros"],
    default=["Estadísticas descriptivas", "Métricas del modelo", "Pruebas estadísticas",
             "Importancia de variables", "Pronósticos futuros"],
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 3: REPORTE PDF PROFESIONAL ---
st.markdown("#### Generar reporte PDF")
st.caption(
    "Documento profesional multi-página: portada, resumen ejecutivo, estadísticas, "
    "métricas del modelo, pruebas de hipótesis, importancia de variables, pronósticos "
    "y metodología — listo para anexar al documento del proyecto de grado."
)

generar = st.button("📄 Generar Reporte PDF Profesional", type="primary", use_container_width=True)

if generar:
    with st.spinner("Ensamblando el reporte (portada, gráficas y tablas)..."):
        try:
            pdf_bytes = build_report_pdf(
                report_name=report_name,
                academic_info=ACADEMIC_INFO,
                insumos_criticos=INSUMOS_CRITICOS,
                best_info=best_info,
                results_df=results_df,
                dataset_processed=st.session_state["dataset_processed"],
                target_col=TARGET_VARIABLE,
                sections=sections,
                predictions_future=st.session_state.get("predictions_future"),
                shap_df=st.session_state.get("shap_importance_df"),
                hyp_results=st.session_state.get("hyp_results"),
                res_analysis=st.session_state.get("residuals_analysis"),
            )
            st.session_state["_pdf_report_bytes"] = pdf_bytes
            st.success("Reporte generado correctamente.")
        except Exception as e:
            st.error(f"No fue posible generar el reporte: {e}")

if st.session_state.get("_pdf_report_bytes"):
    faltantes = []
    if "Pruebas estadísticas" in sections and st.session_state.get("hyp_results") is None:
        faltantes.append("Pruebas estadísticas (visita primero el módulo **Evaluación**)")
    if "Importancia de variables" in sections and st.session_state.get("shap_importance_df") is None:
        faltantes.append("Importancia de variables (visita primero el módulo **Interpretabilidad**)")
    if "Pronósticos futuros" in sections and st.session_state.get("predictions_future") is None:
        faltantes.append("Pronósticos futuros (visita primero el módulo **Predicción**)")
    if faltantes:
        st.info("Secciones omitidas por falta de datos: " + "; ".join(faltantes) + ".")

    st.download_button(
        "⬇️ Descargar Reporte PDF",
        st.session_state["_pdf_report_bytes"],
        f"{report_name}.pdf",
        "application/pdf",
        type="primary",
        use_container_width=True,
    )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 4: DESCARGAS ADICIONALES (Excel) ---
st.markdown("#### 📎 Descargas adicionales")
st.caption(
    "Cada archivo se genera en Excel con formato de dashboard (tarjetas de KPI, "
    "tablas con color y gráficos) para que se vea profesional al abrirlo."
)

from components.download_card import download_card

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    xlsx_comp = build_comparativa_excel(results_df, best_info, report_name, MODEL_COLORS)
    download_card(
        icon="📊", color="blue",
        title="Comparativa de modelos",
        file_format="Archivo Excel (.xlsx)",
        description=(
            "Desempeño de cada modelo evaluado (MAE, RMSE, R² y MAPE) y cuánto "
            "mejora cada uno frente a ARIMA. El modelo ganador aparece resaltado."
        ),
        data=xlsx_comp, file_name=f"{report_name}_comparativa.xlsx", mime=XLSX_MIME,
        key="dl_comparativa",
    )

with row1_col2:
    if st.session_state.get("dataset_processed") is not None:
        xlsx_datos = build_datos_excel(st.session_state["dataset_processed"], TARGET_VARIABLE, report_name)
        download_card(
            icon="🗂️", color="green",
            title="Datos procesados",
            file_format="Archivo Excel (.xlsx)",
            description=(
                "El histórico completo ya limpio y listo para análisis: volumen "
                "importado, variables macroeconómicas y variables creadas "
                "(rezagos, promedios móviles)."
            ),
            data=xlsx_datos, file_name=f"{report_name}_datos.xlsx", mime=XLSX_MIME,
            key="dl_datos",
        )

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    if st.session_state.get("predictions_future") is not None:
        xlsx_pred = build_pronosticos_excel(st.session_state["predictions_future"], best_info, report_name)
        download_card(
            icon="📈", color="amber",
            title="Pronósticos futuros",
            file_format="Archivo Excel (.xlsx)",
            description=(
                "Proyección mes a mes del modelo ganador, con su intervalo de "
                "confianza del 95% (límite inferior y superior) para cada mes."
            ),
            data=xlsx_pred, file_name=f"{report_name}_pronosticos.xlsx", mime=XLSX_MIME,
            key="dl_pronosticos",
        )
    else:
        st.caption("📈 Genera pronósticos primero en el módulo **Predicción** para habilitar esta descarga.")

with row2_col2:
    metadata = {
        "reporte": report_name,
        "generado_en": datetime.now().isoformat(),
        "modelo": best_info["best_model_name"],
        "metricas": best_info["metrics"],
        "hipotesis_confirmada": best_info["hypothesis_confirmed"],
        "info_academica": ACADEMIC_INFO,
    }
    xlsx_meta = build_metadata_excel(metadata, ACADEMIC_INFO, report_name)
    download_card(
        icon="📋", color="violet",
        title="Ficha del proyecto",
        file_format="Archivo Excel (.xlsx)",
        description=(
            "Resumen de una página: información académica, modelo seleccionado, "
            "métricas clave y conclusión de la hipótesis — ideal para anexar o "
            "compartir rápidamente."
        ),
        data=xlsx_meta, file_name=f"{report_name}_ficha.xlsx", mime=XLSX_MIME,
        key="dl_ficha",
    )

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# --- SECCIÓN 5: INFORMACIÓN ACADÉMICA ---
st.markdown("#### Información académica")
st.markdown(
    f'''<div class="card-futurista">
    <p><b>Universidad:</b> {ACADEMIC_INFO["universidad"]}</p>
    <p><b>Programa:</b> {ACADEMIC_INFO["programa"]}</p>
    <p><b>Línea de investigación:</b> {ACADEMIC_INFO["linea_investigacion"]}</p>
    <p><b>Director:</b> {ACADEMIC_INFO["director"]}</p>
    <p><b>Autor:</b> {ACADEMIC_INFO["autor"]}</p>
    <p style="color:var(--text-secondary);font-size:0.8rem;">Reporte generado el {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </div>''',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Resumen ejecutivo y consultas finales
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

_best_r = st.session_state.get("best_model_info")
_df_r = st.session_state.get("dataset_processed")

_ai_ctx_rep = {}
if _best_r is not None:
    _m = _best_r.get("metrics", {})
    # Usar la variable principal real calculada por SHAP (guardada en
    # session_state por la pagina de Interpretabilidad), en vez de un
    # fallback hardcodeado a "trm_peso_dolar" que puede ser incorrecto.
    _shap_guardado = st.session_state.get("shap_importance_df")
    if _shap_guardado is not None and len(_shap_guardado) > 0:
        _var_princ = _shap_guardado.iloc[0]["variable"]
    else:
        _importancias = _best_r.get("feature_importances", {})
        _var_princ = max(_importancias, key=_importancias.get) if _importancias else "N/D"

    _ai_ctx_rep = {
        "mejor_modelo": _best_r.get("best_model_name", "N/D"),
        "rmse_mejor": _m.get("RMSE", 0),
        "mejora_pct": _m.get("% Mejora vs ARIMA (RMSE)", 0),
        "hipotesis_confirmada": _best_r.get("hypothesis_confirmed", False),
        "variable_principal": _var_princ,
        "periodo": "enero 2015 — diciembre 2024",
        "total_registros": len(_df_r) if _df_r is not None else 0,
    }

render_ai_panel(
    pagina="reporte",
    contexto=_ai_ctx_rep,
    auto_trigger=(_best_r is not None),
    preguntas_sugeridas=[
        "¿Cómo presento los resultados del modelo en formato APA 7?",
        "¿Qué limitaciones del modelo debo mencionar en el documento final?",
        "Resume los hallazgos más importantes para presentar al director de proyecto.",
    ],
    modo="expander",
)