"""
components/download_card.py
Tarjeta de descarga para la pagina de Reporte: icono con insignia de
color, titulo, formato del archivo y una descripcion de qué contiene
el documento -- en vez de un simple st.download_button suelto.

Uso:
    download_card(
        icon="📊", color="blue",
        title="Comparativa de modelos",
        file_format="Archivo Excel (.xlsx)",
        description="Tabla con el desempeño de cada modelo evaluado...",
        data=xlsx_bytes,
        file_name="reporte_comparativa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_comparativa",
    )
"""
import streamlit as st


def download_card(*, icon, color, title, file_format, description, data, file_name, mime, key):
    """Dibuja una card con icono/insignia de color, titulo, formato,
    descripcion del contenido y un boton de descarga real.

    - color: uno de "blue", "green", "amber", "violet" (define el
      color de la insignia y del boton de descarga).
    """
    container = st.container(border=True)
    with container:
        st.markdown(f'<span class="download-card-marker {color}"></span>', unsafe_allow_html=True)
        st.markdown(
            f'''<div class="download-card-header">
                    <div class="download-card-icon {color}">{icon}</div>
                    <div>
                        <div class="download-card-title">{title}</div>
                        <div class="download-card-format">{file_format}</div>
                    </div>
                </div>
                <div class="download-card-desc">{description}</div>''',
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️  Descargar",
            data,
            file_name,
            mime,
            use_container_width=True,
            key=key,
        )
