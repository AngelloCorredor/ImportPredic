"""
components/chart_card.py
Envuelve una grafica de Plotly en una "card" con sombra/glow tematica
(coherente con el modo claro/oscuro activo). La card tiene un pequeño
boton de icono (ℹ️) en la esquina que, al hacer click, abre un
**modal nativo de Streamlit** (st.dialog): el fondo de la app se
oscurece automaticamente, la grafica se muestra ampliada a un lado y
la explicación (qué es, cómo se lee, para qué sirve) aparece al otro
lado. Para cerrar el modal se usa la "×" nativa de Streamlit (no hay
boton propio "volver": st.rerun() tiene un costo de primera-ejecucion
por las llamadas de IA de la pagina, y la "×" nativa ya hace lo mismo
sin ese costo).

Uso:
    from components.chart_card import chart_card

    chart_card(
        fig,
        chart_id="hist_volumen",
        title="Distribución del volumen de importación",
        icon="📊",
        summary=[
            "Un <b>histograma</b> agrupa los valores de la variable en "
            "barras ('bins') y muestra cuantas observaciones caen en "
            "cada rango.",
            "Sirve para ver de un vistazo la <b>forma de la distribución</b>.",
        ],
    )
"""
import streamlit as st


def chart_card(fig, chart_id: str, title: str, summary, icon: str = "📊"):
    """Dibuja `fig` dentro de una card con glow tematico y un boton de
    icono que abre un dialogo modal (fondo oscurecido) con la grafica
    ampliada y su explicación al lado.

    - fig: figura de Plotly ya construida (se muestra tanto en la card
      como, ampliada, dentro del modal).
    - chart_id: identificador unico y estable (para las keys de los
      widgets involucrados).
    - title: titulo mostrado en la cabecera de la card y del modal.
    - summary: string o lista de strings (un parrafo cada uno) con la
      explicación de la grafica. Puede incluir <b> para resaltar.
    - icon: emoji mostrado junto al titulo de la explicación.
    """
    paragraphs = summary if isinstance(summary, (list, tuple)) else [summary]
    body_html = "".join(f"<p>{p}</p>" for p in paragraphs)

    @st.dialog(title, width="large")
    def _open_explanation():
        col_chart, col_text = st.columns([1.5, 1], gap="large")
        with col_chart:
            st.plotly_chart(fig, use_container_width=True, key=f"chart_card_dialog__{chart_id}")
        with col_text:
            st.markdown(
                f'''<div class="chart-explain-dialog">
                        <div class="chart-explain-dialog-icon">{icon}</div>
                        <div class="chart-explain-dialog-title">¿Qué muestra esta gráfica?</div>
                        <div class="chart-explain-dialog-body">{body_html}</div>
                    </div>''',
                unsafe_allow_html=True,
            )

    container = st.container(border=True)
    with container:
        st.markdown('<span class="chart-card-marker"></span>', unsafe_allow_html=True)
        col_title, col_btn = st.columns([10, 1])
        with col_title:
            st.markdown(f'<div class="chart-card-title">{title}</div>', unsafe_allow_html=True)
        with col_btn:
            if st.button("ℹ️", key=f"chart_card_open__{chart_id}",
                         help="Ver explicación de esta gráfica"):
                _open_explanation()
        st.plotly_chart(fig, use_container_width=True, key=f"chart_card_inline__{chart_id}")
