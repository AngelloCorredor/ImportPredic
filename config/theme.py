"""
config/theme.py
Paleta de colores, fuentes y funciones para inyectar CSS en la app de
Streamlit. Las graficas de Plotly usan siempre template="plotly_dark"
(fijado a nivel de cada pagina, independiente del interruptor claro/
oscuro de la app), asi que get_plotly_theme() esta afinado para verse
bien sobre ese fondo oscuro: colores tomados de la paleta "Atardecer de
pizarra" (crema + azules pizarra) de la imagen de referencia del usuario.
"""
import os

# ---- Paleta para graficos (colorway + acentos puntuales) ----
CHART_SLATE = "#7C8B96"    # azul pizarra — serie principal
CHART_ROSE = "#E0798A"     # terracota suave — serie secundaria / alerta
CHART_SAGE = "#5FB98A"     # verde salvia — serie positiva
CHART_GOLD = "#D9A44E"     # dorado calido — acento / franjas de aviso
CHART_DENIM = "#6FA0C6"    # azul denim — serie de apoyo
CHART_CREAM = "#D8C39C"    # crema/dorado palido — acento ink
CHART_NEUTRAL_MID = "#2A333B"  # pizarra oscura — punto medio para escalas divergentes

# Alias retrocompatibles (mismo nombre, nuevos valores)
NEON_CYAN = CHART_SLATE
NEON_MAGENTA = CHART_ROSE
NEON_GREEN = CHART_SAGE
NEON_PURPLE = CHART_CREAM
NEON_ORANGE = CHART_GOLD
NEON_BLUE = CHART_DENIM
NEON_YELLOW = CHART_GOLD

# Texto y grid pensados para tarjetas oscuras (fondo del plot transparente)
TEXT_PRIMARY = "#EDE7DA"     # crema calido — texto principal del grafico
TEXT_SECONDARY = "#C7C0B2"   # crema atenuado — ticks de los ejes
GRID_LINE = "rgba(237, 231, 218, 0.10)"     # lineas de grilla, muy sutiles
AXIS_LINE = "rgba(237, 231, 218, 0.28)"     # eje/linea cero, algo mas visibles
LEGEND_BG = "rgba(26, 28, 34, 0.88)"        # "card" oscura para la leyenda
LEGEND_BORDER = "rgba(237, 231, 218, 0.16)"

# Retrocompatibles (ya no se usan dentro de este archivo, se conservan
# por si algun modulo externo llegara a importarlos)
DARK_BG = "#15171D"
DARK_CARD = "#1E2028"
DARK_BORDER = "#2E3540"
DARK_SURFACE = "#262A34"
DARK_HOVER = "#2A333B"

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


def _read(*parts):
    path = os.path.join(_STATIC_DIR, *parts)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def get_css():
    """Retorna el CSS completo (variables + main + animations + components)."""
    return "\n".join([
        _read("css", "variables.css"),
        _read("css", "main.css"),
        _read("css", "animations.css"),
        _read("css", "components.css"),
    ])


def get_plotly_theme():
    """Diccionario de layout para aplicar el tema oscuro "Atardecer de
    pizarra" a los graficos Plotly (que siempre usan template="plotly_dark").
    """
    axis_common = dict(
        gridcolor=GRID_LINE,
        linecolor=AXIS_LINE,
        zerolinecolor=AXIS_LINE,
        tickfont=dict(color=TEXT_SECONDARY),
        title=dict(font=dict(color=TEXT_SECONDARY)),
    )
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT_PRIMARY, size=12),
        xaxis=axis_common,
        yaxis=axis_common,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(gridcolor=GRID_LINE, linecolor=AXIS_LINE, tickfont=dict(color=TEXT_SECONDARY)),
            angularaxis=dict(gridcolor=GRID_LINE, linecolor=AXIS_LINE, tickfont=dict(color=TEXT_PRIMARY)),
        ),
        legend=dict(bgcolor=LEGEND_BG, bordercolor=LEGEND_BORDER, borderwidth=1, font=dict(color=TEXT_PRIMARY)),
        margin=dict(t=40, l=10, r=10, b=10),
        colorway=[CHART_SLATE, CHART_ROSE, CHART_SAGE, CHART_GOLD, CHART_DENIM, CHART_CREAM],
    )


def inject_three_js_scene(height=460):
    """Retorna el HTML autónomo con la escena Three.js para st.components.v1.html()."""
    return _read("js", "three_scene.html")
