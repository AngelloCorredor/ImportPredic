"""src/utils/helpers.py — Funciones auxiliares reutilizables."""
import plotly.graph_objects as go
from config.theme import get_plotly_theme

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def format_kg(value: float) -> str:
    return f"{value:,.0f} kg"


def format_usd(value: float) -> str:
    return f"US$ {value:,.0f}"


def format_pct(value: float) -> str:
    return f"{value:+.2f}%"


def apply_neon_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**get_plotly_theme())
    return fig


def mes_nombre(mes_num: int) -> str:
    return MESES_ES.get(int(mes_num), str(mes_num))
