"""
src/reports/charts.py
Graficas estaticas (matplotlib) para incrustar en el reporte PDF.
Se usa matplotlib en vez de las graficas Plotly de la app para no
depender de un navegador/Chrome (kaleido) al exportar el PDF -- esto
hace que la generacion del reporte funcione en cualquier entorno,
incluidos servidores sin navegador instalado.
"""
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

# ---- Paleta del reporte (coherente con la identidad de la app, ----
# ---- afinada para verse bien impresa sobre fondo blanco)        ----
NAVY = "#26303A"
SLATE = "#6E808C"
GOLD = "#C4943C"
ROSE = "#B05460"
SAGE = "#568C6C"
DENIM = "#4C7A9E"
GRID = "#E8E6F0"
TEXT = "#3A3A46"
TICK = "#6E6E7C"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#CCCAD8",
    "axes.labelcolor": TEXT,
    "text.color": TEXT,
    "xtick.color": TICK,
    "ytick.color": TICK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "axes.axisbelow": True,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.size": 10,
})

_TMP_FILES = []


def _new_tmp_path():
    fd, path = tempfile.mkstemp(suffix=".png", prefix="importpredic_report_")
    os.close(fd)
    _TMP_FILES.append(path)
    return path


def cleanup_temp_charts():
    """Borra todos los PNG temporales generados en esta sesion de reporte."""
    for p in _TMP_FILES:
        try:
            os.remove(p)
        except OSError:
            pass
    _TMP_FILES.clear()


def _clean_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(length=0)


def chart_histogram(series: pd.Series, xlabel="Volumen importado (kg)") -> str:
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
    n, bins, patches = ax.hist(series.dropna(), bins=14, color=SLATE, edgecolor="white", linewidth=0.6)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frecuencia (meses)")
    ax.set_ylim(top=ax.get_ylim()[1] * 1.14)
    mean_val = series.mean()
    ax.axvline(mean_val, color=GOLD, linewidth=1.8, linestyle="--")
    ax.text(mean_val, ax.get_ylim()[1] * 0.97, f"  Media: {mean_val:,.0f}", color=GOLD, fontsize=9, va="top")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    _clean_axes(ax)
    fig.tight_layout()
    path = _new_tmp_path()
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_model_comparison(results_df: pd.DataFrame, best_model_name: str) -> str:
    df = results_df.sort_values("RMSE", ascending=True)
    colors = [GOLD if m == best_model_name else (ROSE if m == "ARIMA" else SLATE) for m in df["Modelo"]]
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
    bars = ax.barh(df["Modelo"], df["RMSE"], color=colors, height=0.58)
    ax.invert_yaxis()
    ax.set_xlabel("RMSE (kg) — menor es mejor")
    for bar, val in zip(bars, df["RMSE"]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2, f"{val:,.0f}",
                va="center", fontsize=8.5, color=TEXT)
    _clean_axes(ax)
    fig.tight_layout()
    path = _new_tmp_path()
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_shap_importance(shap_df: pd.DataFrame, top_n: int = 10) -> str:
    df = shap_df.head(top_n).sort_values("mean_abs_shap", ascending=True)
    fig, ax = plt.subplots(figsize=(6.4, 3.8), dpi=200)
    norm = (df["mean_abs_shap"] - df["mean_abs_shap"].min()) / (
        df["mean_abs_shap"].max() - df["mean_abs_shap"].min() + 1e-9)
    colors = [_blend(SLATE, GOLD, v) for v in norm]
    bars = ax.barh(df["variable"], df["mean_abs_shap"], color=colors, height=0.6)
    ax.set_xlabel("Importancia media |SHAP|")
    for bar, val in zip(bars, df["mean_abs_shap"]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2, f"{val:.3f}",
                va="center", fontsize=8.5, color=TEXT)
    _clean_axes(ax)
    fig.tight_layout()
    path = _new_tmp_path()
    fig.savefig(path)
    plt.close(fig)
    return path


def _blend(hex1, hex2, t):
    c1 = np.array([int(hex1[i:i+2], 16) for i in (1, 3, 5)])
    c2 = np.array([int(hex2[i:i+2], 16) for i in (1, 3, 5)])
    c = (c1 + (c2 - c1) * t).astype(int)
    return "#%02X%02X%02X" % tuple(c)


def chart_forecast(hist_dates, hist_values, future_df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(6.6, 3.6), dpi=200)
    hist_dates = pd.to_datetime(pd.Series(hist_dates))
    cutoff = hist_dates.iloc[-24] if len(hist_dates) > 24 else hist_dates.iloc[0]
    mask = hist_dates >= cutoff
    ax.plot(hist_dates[mask], np.asarray(hist_values)[mask.values], color=SLATE, linewidth=1.8, label="Histórico")

    fut_dates = pd.to_datetime(future_df["fecha"])
    ax.plot(fut_dates, future_df["prediccion"], color=GOLD, linewidth=2, marker="o", markersize=3,
            label="Pronóstico")
    if "limite_inferior" in future_df and "limite_superior" in future_df:
        ax.fill_between(fut_dates, future_df["limite_inferior"], future_df["limite_superior"],
                         color=GOLD, alpha=0.18, label="Intervalo 95%")
    ax.axvline(hist_dates.iloc[-1], color=SLATE, linewidth=0.9, linestyle=":")
    ax.set_ylabel("Volumen (kg)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    fig.autofmt_xdate(rotation=25)
    _clean_axes(ax)
    fig.tight_layout()
    path = _new_tmp_path()
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_real_vs_pred(dates_test, y_test, y_pred_model, y_pred_arima, model_name) -> str:
    fig, ax = plt.subplots(figsize=(6.6, 3.6), dpi=200)
    dates_test = pd.to_datetime(pd.Series(dates_test))
    ax.plot(dates_test, y_test, color=NAVY, linewidth=1.8, label="Real")
    ax.plot(dates_test, y_pred_model, color=GOLD, linewidth=1.8, label=model_name)
    ax.plot(dates_test, y_pred_arima, color=ROSE, linewidth=1.4, linestyle="--", label="ARIMA")
    ax.set_ylabel("Volumen (kg)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    fig.autofmt_xdate(rotation=25)
    _clean_axes(ax)
    fig.tight_layout()
    path = _new_tmp_path()
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_residuals(dates_test, residuals) -> str:
    fig, ax = plt.subplots(figsize=(6.6, 3.2), dpi=200)
    dates_test = pd.to_datetime(pd.Series(dates_test))
    residuals = np.asarray(residuals)
    colors = np.where(residuals >= 0, DENIM, ROSE)
    ax.bar(dates_test, residuals, color=list(colors), width=20)
    ax.axhline(0, color=TEXT, linewidth=0.8)
    ax.set_ylabel("Residuo (kg)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate(rotation=25)
    _clean_axes(ax)
    fig.tight_layout()
    path = _new_tmp_path()
    fig.savefig(path)
    plt.close(fig)
    return path
