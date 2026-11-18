import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.theme import CHART_SLATE, CHART_ROSE
from config.settings import INSUMOS_CRITICOS, SAMPLE_DATA_PATH, TARGET_VARIABLE, TRAIN_TEST_SPLIT_DATE
from src.data.loader import load_file, validate_columns, data_quality_report
from src.data.sample_generator import generate_sample_dataset
from src.data.preprocessor import DataPreprocessor
from src.utils.helpers import apply_neon_theme
from components.chart_card import chart_card

from components.page_setup import setup_page
user = setup_page("Carga de Datos", "📥")

from src.data.persistence import start_new_snapshot, save_current_snapshot, reset_downstream


st.markdown("## 📥 Carga y Validación de Datos")

# --- SECCIÓN 1: ZONA DE CARGA ---
st.markdown("#### Zona de carga")
st.markdown('<div class="upload-zone">Arrastra tus archivos CSV/XLSX de DIAN, DANE o Banco de la República</div>',
            unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Selecciona uno o más archivos (CSV con coma o punto y coma, o XLSX — máx. 25 MB c/u)",
    type=["csv", "xlsx"], accept_multiple_files=True,
)

use_sample = st.button("⚡ Usar datos de ejemplo (demostración académica)")

df_raw = None
if use_sample:
    df_raw = generate_sample_dataset()
    st.session_state["dataset_raw"] = df_raw
    st.session_state["_data_origin"] = "Datos de demostración (sintéticos)"
    st.success(f"Datos de demostración generados: {len(df_raw)} filas, período 2015–2024.")
elif uploaded_files:
    dfs = []
    for f in uploaded_files:
        try:
            df_i = load_file(f)
            dfs.append(df_i)
            st.success(f"Archivo cargado: {f.name} ({len(df_i)} filas)")
        except Exception as e:
            st.error(f"Error al leer {f.name}: {e}")
    if dfs:
        df_raw = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
        st.session_state["dataset_raw"] = df_raw
        st.session_state["_data_origin"] = ", ".join(f.name for f in uploaded_files)[:250]
elif st.session_state.get("dataset_raw") is not None:
    df_raw = st.session_state["dataset_raw"]

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

if df_raw is not None:
    # --- SECCIÓN 2: CONFIGURACIÓN ---
    st.markdown("#### Configuración")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown("**Selecciona las partidas arancelarias a incluir:**")
        selected_partidas = []
        cols = st.columns(len(INSUMOS_CRITICOS))
        for i, (code, desc) in enumerate(INSUMOS_CRITICOS.items()):
            with cols[i]:
                checked = st.checkbox(f"{code}", value=True, help=desc, key=f"chk_{code}")
                if checked:
                    selected_partidas.append(code)
        st.session_state["selected_partidas"] = selected_partidas
    with col_b:
        test_split = st.date_input("Fecha de corte train/test", pd.to_datetime(TRAIN_TEST_SPLIT_DATE))

    # --- SECCIÓN 3: VALIDACIÓN ---
    st.markdown("#### Validación y calidad de datos")
    validation = validate_columns(df_raw)
    if validation["valid"]:
        st.success(f"Estructura válida — {validation['n_rows']} filas, {validation['n_cols']} columnas.")
    else:
        st.warning(f"Columnas faltantes: {validation['missing_columns']}")

    quality_df = data_quality_report(df_raw)
    st.dataframe(quality_df, use_container_width=True)

    low_quality = quality_df[quality_df["% completitud"] < 95]
    if not low_quality.empty:
        st.warning(f"⚠️ {len(low_quality)} columna(s) con más de 5% de valores nulos.")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- PROCESAR ---
    from datetime import datetime as _dt
    # Cada dataset nuevo usa una clave distinta para el campo del nombre, en
    # lugar de borrar la clave de un widget ya dibujado (frágil en Streamlit).
    _n = st.session_state.setdefault("_nombre_corrida_n", 0)
    nombre_corrida = st.text_input(
        "Nombre de esta corrida (para encontrarla luego en tu historial)",
        value=st.session_state.setdefault(f"_nombre_corrida_def_{_n}", f"Corrida {_dt.now():%Y-%m-%d %H:%M}"),
        max_chars=120, key=f"_nombre_corrida_{_n}",
    )
    puede_procesar = validation["valid"] and bool(st.session_state["selected_partidas"])
    if not st.session_state["selected_partidas"]:
        st.warning("Selecciona al menos una partida arancelaria.")
    if st.button("⚙️ Procesar y guardar datos", type="primary", disabled=not puede_procesar):
        with st.spinner("Ejecutando pipeline de preprocesamiento..."):
            pre = DataPreprocessor(TARGET_VARIABLE)
            try:
                df_processed, report = pre.run_full_pipeline(df_raw, st.session_state["selected_partidas"])
            except Exception as e:
                st.error(f"No se pudo procesar el archivo: {e}")
                st.stop()
            if df_processed.empty:
                st.error("Después del filtro no quedó ninguna fila. Revisa las partidas seleccionadas "
                         "y el formato de la columna partida_arancelaria.")
                st.stop()
            # Un dataset nuevo invalida modelos/pronósticos del dataset anterior
            # y abre una corrida NUEVA en la base de datos.
            reset_downstream("datos")
            st.session_state["dataset_processed"] = df_processed
            st.session_state["preprocessing_report"] = report
            st.session_state["preprocessor"] = pre
            start_new_snapshot()
            cid = save_current_snapshot(nombre=nombre_corrida,
                                        origen=st.session_state.get("_data_origin"))
        if cid:
            st.session_state["_nombre_corrida_n"] = _n + 1  # el próximo dataset recibe un nombre nuevo
            st.success(f"✓ Datos procesados y guardados en tu historial como «{nombre_corrida}».")
        else:
            st.warning("Datos procesados en la sesión, pero no se pudieron guardar en la base de datos.")

    # --- VISTA PREVIA ---
    if st.session_state.get("dataset_processed") is not None:
        df_p = st.session_state["dataset_processed"]
        report = st.session_state["preprocessing_report"]

        st.markdown("#### Vista previa del dataset procesado")
        c1, c2, c3 = st.columns(3)
        c1.metric("Filas procesadas", report["filas_procesadas"])
        c2.metric("Outliers winsorizados", report["outliers_detectados"])
        c3.metric("Rango de fechas", f"{report['rango_fechas'][0].year}–{report['rango_fechas'][1].year}")

        t1, t2 = st.tabs(["Primeras filas", "Últimas filas"])
        with t1:
            st.dataframe(df_p.head(10), use_container_width=True)
        with t2:
            st.dataframe(df_p.tail(10), use_container_width=True)

        col_h, col_b = st.columns(2)
        with col_h:
            fig = go.Figure(go.Histogram(x=df_p[TARGET_VARIABLE], marker_color=CHART_SLATE, opacity=0.85))
            fig.update_layout(template="plotly_dark")
            apply_neon_theme(fig)
            chart_card(
                fig,
                chart_id="carga_histograma_volumen",
                title="Distribución del volumen de importación",
                icon="📊",
                summary=[
                    "<b>Eje X:</b> rangos de volumen importado, en kilogramos (kg), divididos en "
                    "intervalos ('bins'). <b>Eje Y:</b> cantidad de meses del histórico cuyo "
                    "volumen cae dentro de cada intervalo.",
                    "Un <b>histograma</b> agrupa los valores del volumen importado en barras "
                    "('bins') y muestra cuántas observaciones (meses) caen en cada rango.",
                    "Sirve para ver de un vistazo la <b>forma de la distribución</b>: si es "
                    "simétrica, si tiene sesgo hacia valores altos o bajos, y en qué rango se "
                    "concentra la mayoría de los meses históricos.",
                    "Es un primer chequeo útil antes de entrenar un modelo: distribuciones muy "
                    "sesgadas o con colas largas pueden requerir transformaciones (log, "
                    "winsorización) para que el modelo prediga mejor.",
                ],
            )
        with col_b:
            df_p["anio"] = pd.to_datetime(df_p["fecha"]).dt.year
            fig2 = go.Figure()
            for year in sorted(df_p["anio"].unique()):
                fig2.add_trace(go.Box(y=df_p[df_p["anio"] == year][TARGET_VARIABLE], name=str(year),
                                       marker_color=CHART_ROSE))
            fig2.update_layout(template="plotly_dark", showlegend=False)
            apply_neon_theme(fig2)
            chart_card(
                fig2,
                chart_id="carga_boxplot_anio",
                title="Boxplot del volumen por año",
                icon="📦",
                summary=[
                    "<b>Eje X:</b> cada año del período analizado (2015-2024), uno al lado del "
                    "otro. <b>Eje Y:</b> volumen importado, en kilogramos (kg); cada caja resume "
                    "los 12 meses de ese año.",
                    "Un <b>boxplot</b> (diagrama de caja) resume la distribución de cada año con "
                    "cinco valores: mínimo, primer cuartil, mediana (línea central), tercer "
                    "cuartil y máximo. Los puntos fuera de los 'bigotes' son valores atípicos.",
                    "Comparar una caja por año permite ver de forma compacta cómo cambia el "
                    "<b>nivel</b> (la caja sube o baja) y la <b>variabilidad</b> (la caja se "
                    "agranda o achica) del volumen importado a lo largo del tiempo.",
                    "Es útil para detectar años atípicos o con mayor dispersión antes de pasar "
                    "a un análisis exploratorio más detallado.",
                ],
            )

        st.page_link("pages/03_exploracion.py", label="Continuar a Exploración →", icon="🔍")
else:
    st.info("Sube archivos o usa los datos de demostración para comenzar.")

# ---------------------------------------------------------------------------
# ASISTENTE DE IA — Análisis de calidad de datos
# ---------------------------------------------------------------------------
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
from components.ai_panel import render_ai_panel

# Construir contexto con los datos disponibles en esta sesión
_df_proc = st.session_state.get("dataset_processed")
_prep_report = st.session_state.get("preprocessing_report") or {}

_ai_ctx = {
    "filas_totales": _prep_report.get("filas_originales", 0),
    "filas_procesadas": len(_df_proc) if _df_proc is not None else 0,
    "rango_fechas": _prep_report.get("rango_fechas", "N/D"),
    "nulos_por_columna": _prep_report.get("nulos_por_columna", {}),
    "outliers_detectados": _prep_report.get("outliers_detectados", 0),
    "variables_disponibles": list(_df_proc.columns.tolist()) if _df_proc is not None else [],
    "estadisticas_objetivo": _prep_report.get("estadisticas_objetivo", {}),
}

render_ai_panel(
    pagina="carga",
    contexto=_ai_ctx,
    auto_trigger=(_df_proc is not None),
    preguntas_sugeridas=[
        "¿Por qué se imputan los datos faltantes con interpolación lineal?",
        "¿Qué es un outlier en el contexto de series de tiempo de importación?",
        "¿Cómo afecta la calidad de los datos al desempeño del modelo predictivo?",
    ],
    modo="expander",
)
