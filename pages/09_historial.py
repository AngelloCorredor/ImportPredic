"""
pages/09_historial.py
Historial de corridas del usuario (guardadas en la base de datos) y
comparación entre corridas.
"""
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.page_setup import setup_page

user = setup_page("Historial", "💾")

from config.settings import MODEL_COLORS
from src.data.persistence import (
    current_snapshot_id, delete_snapshot, list_snapshots, load_snapshot, rename_snapshot,
)
from src.db import repository as repo
from src.utils.helpers import apply_neon_theme

st.markdown("## 💾 Mis corridas")
st.caption(
    "Cada conjunto de datos que procesas en **Carga de Datos** queda guardado en tu cuenta junto "
    "con su modelo, pronósticos y evaluaciones. Solo tú puedes ver estas corridas, y puedes "
    "retomarlas desde cualquier equipo."
)

snapshots = list_snapshots()
active_id = current_snapshot_id()

if not snapshots:
    st.info(
        "Todavía no tienes corridas guardadas. Ve a **Carga de Datos**, procesa un conjunto de "
        "datos y aparecerá aquí automáticamente."
    )
    st.page_link("pages/02_carga_datos.py", label="Ir a Carga de Datos", icon="📥")
    st.stop()


def _fmt_bytes(n: int) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:,.0f} {unidad}"
        n /= 1024
    return f"{n:,.1f} TB"


def _chip(texto: str, clase: str = "") -> str:
    return f'<span class="run-chip {clase}">{html.escape(texto)}</span>'


tab_lista, tab_comparar = st.tabs([f"📦 Corridas ({len(snapshots)})", "📊 Comparar corridas"])

# =============================================================================
# LISTA
# =============================================================================
with tab_lista:
    filtro = st.text_input("Buscar por nombre", placeholder="Ej.: demostración, 2024…",
                           label_visibility="collapsed")
    visibles = [s for s in snapshots if filtro.lower() in s["nombre"].lower()] if filtro else snapshots
    if not visibles:
        st.caption("Ninguna corrida coincide con la búsqueda.")

    for snap in visibles:
        sid = snap["id"]
        is_active = sid == active_id
        with st.container(border=True):
            st.markdown('<span class="chart-card-marker"></span>', unsafe_allow_html=True)
            col_info, col_actions = st.columns([3.2, 1])
            with col_info:
                estado = ('<span class="status-indicator ok"></span> Activa en esta sesión'
                          if is_active else '<span class="status-indicator pending"></span> Guardada')
                st.markdown(
                    f'<div class="chart-card-title">📦 {html.escape(snap["nombre"])}</div>'
                    f'<div style="margin-top:4px;font-size:0.82rem;color:var(--text-secondary);">{estado}</div>',
                    unsafe_allow_html=True,
                )
                chips = [
                    _chip(snap["rango_fechas"] or "Sin fechas"),
                    _chip(f'{snap["n_filas"]} meses'),
                    _chip("Partidas: " + (", ".join(snap["partidas"]) or "—")),
                ]
                if snap["mejor_modelo"]:
                    chips.append(_chip(f'🏆 {snap["mejor_modelo"]}'))
                    if snap["rmse"] is not None:
                        chips.append(_chip(f'RMSE {snap["rmse"]:,.0f} kg'))
                    if snap["mejora_vs_arima"] is not None:
                        chips.append(_chip(f'{snap["mejora_vs_arima"]:+.1f}% vs ARIMA'))
                    if snap["hipotesis_confirmada"] is not None:
                        chips.append(_chip("✓ Criterio 15 % cumplido", "ok") if snap["hipotesis_confirmada"]
                                     else _chip("✗ Criterio 15 % no cumplido", "bad"))
                    if snap["metodo_validacion"] == "walk_forward":
                        chips.append(_chip("Walk-forward"))
                else:
                    chips.append(_chip("Sin modelo entrenado", "warn"))
                if snap["tiene_pronosticos"]:
                    chips.append(_chip("📈 Con pronósticos"))
                st.markdown(f'<div class="run-meta">{"".join(chips)}</div>', unsafe_allow_html=True)
                origen = f' · Origen: {snap["origen_datos"]}' if snap.get("origen_datos") else ""
                st.caption(
                    f'Actualizada: {snap["actualizado_en"]:%Y-%m-%d %H:%M} UTC · '
                    f'{_fmt_bytes(snap["tamano_bytes"])}{origen}'
                )

            with col_actions:
                if not is_active:
                    if st.button("📂 Cargar", key=f"load_{sid}", use_container_width=True, type="primary"):
                        if load_snapshot(sid):
                            st.toast("Corrida cargada. Ya puedes navegar por los demás módulos.", icon="✅")
                            st.rerun()
                        else:
                            st.error("No se encontró la corrida.")
                else:
                    st.button("✓ En uso", key=f"active_{sid}", use_container_width=True, disabled=True)

                with st.popover("✏️ Renombrar", use_container_width=True):
                    nuevo = st.text_input("Nuevo nombre", value=snap["nombre"], max_chars=120, key=f"rn_in_{sid}")
                    if st.button("Guardar", key=f"rn_{sid}"):
                        if rename_snapshot(sid, nuevo):
                            st.rerun()
                        st.error("Nombre no válido.")

                with st.popover("🗑️ Eliminar", use_container_width=True):
                    st.markdown(f"¿Eliminar **{html.escape(snap['nombre'])}**? Se borrarán su modelo, "
                                "pronósticos y evaluaciones. **No se puede deshacer.**")
                    if st.button("Sí, eliminar", key=f"del_{sid}", type="primary"):
                        delete_snapshot(sid)
                        st.rerun()

# =============================================================================
# COMPARAR
# =============================================================================
with tab_comparar:
    entrenadas = [s for s in snapshots if s["mejor_modelo"]]
    if len(entrenadas) < 2:
        st.info("Necesitas al menos **dos corridas con modelo entrenado** para compararlas.")
    else:
        etiquetas = {s["id"]: f'{s["nombre"]} (#{s["id"]})' for s in entrenadas}
        elegidas = st.multiselect(
            "Corridas a comparar", options=list(etiquetas), format_func=etiquetas.get,
            default=[s["id"] for s in entrenadas[:2]], max_selections=6,
        )
        if len(elegidas) >= 2:
            sel = [s for s in entrenadas if s["id"] in elegidas]

            st.markdown("#### Resumen por corrida")
            resumen = pd.DataFrame([{
                "Corrida": s["nombre"], "Periodo": s["rango_fechas"], "Meses": s["n_filas"],
                "Mejor modelo": s["mejor_modelo"], "RMSE": s["rmse"], "MAE": s["mae"],
                "R²": s["r2"], "MAPE %": s["mape"], "% Mejora vs ARIMA": s["mejora_vs_arima"],
                "Criterio 15 %": "✓" if s["hipotesis_confirmada"] else "✗",
            } for s in sel])
            st.dataframe(
                resumen.style.format({"RMSE": "{:,.0f}", "MAE": "{:,.0f}", "R²": "{:.3f}",
                                      "MAPE %": "{:.2f}", "% Mejora vs ARIMA": "{:+.1f}"}, na_rep="—"),
                use_container_width=True, hide_index=True,
            )

            res = repo.resultados_comparados(user["id"], elegidas)
            if not res.empty:
                st.markdown("#### RMSE de cada modelo en cada corrida")
                fig = go.Figure()
                for modelo, grupo in res.groupby("Modelo", sort=False):
                    fig.add_trace(go.Bar(x=grupo["Corrida"], y=grupo["RMSE"], name=modelo,
                                         marker_color=MODEL_COLORS.get(modelo)))
                fig.update_layout(barmode="group", template="plotly_dark", yaxis_title="RMSE (kg)",
                                  xaxis_title="Corrida")
                apply_neon_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Barras más bajas = menor error. Permite ver si el ranking de modelos se "
                           "mantiene cuando cambian los datos de entrada.")

            pron = repo.pronosticos_comparados(user["id"], elegidas)
            if not pron.empty:
                st.markdown("#### Pronósticos guardados")
                fig2 = go.Figure()
                for nombre, grupo in pron.groupby("Corrida", sort=False):
                    fig2.add_trace(go.Scatter(x=grupo["fecha"], y=grupo["prediccion"],
                                              mode="lines+markers", name=nombre))
                fig2.update_layout(template="plotly_dark", yaxis_title="Volumen pronosticado (kg)")
                apply_neon_theme(fig2)
                st.plotly_chart(fig2, use_container_width=True)

            st.download_button(
                "⬇️ Descargar comparación (CSV)",
                res.drop(columns=["corrida_id"]).to_csv(index=False).encode("utf-8-sig") if not res.empty
                else resumen.to_csv(index=False).encode("utf-8-sig"),
                file_name="comparacion_corridas.csv", mime="text/csv",
            )
        else:
            st.caption("Selecciona al menos dos corridas.")
