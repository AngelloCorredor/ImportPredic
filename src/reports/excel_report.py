"""
src/reports/excel_report.py
Generador de descargas en Excel (.xlsx) con estética de dashboard
profesional: encabezados de marca, tarjetas KPI, bandas alternas,
fila del mejor modelo resaltada y formato condicional. Solo tablas,
sin gráficos incrustados.

Reutiliza la paleta "Atardecer de pizarra" del reporte PDF
(src/reports/pdf_report.py y src/reports/charts.py) para que todas
las descargas del proyecto (PDF + Excel) se vean como un mismo
sistema visual coherente.
"""
import io
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule

# ---- Paleta (igual a src/reports/charts.py — "Atardecer de pizarra") ----
NAVY = "26303A"
GOLD = "C4943C"
ROSE = "B05460"
SAGE = "568C6C"
DENIM = "4C7A9E"
INK = "2D303A"
TEXT_SECONDARY = "6E6E7A"
LIGHT_BG = "F5F4FA"
CARD_BORDER = "E4E2EC"
WHITE = "FFFFFF"
BAND = "F7F7FB"

THIN = Side(style="thin", color=CARD_BORDER)
BORDER_ALL = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

_FONT = "Calibri"


# ---------------------------------------------------------------------------
# Helpers de estilo reutilizables
# ---------------------------------------------------------------------------
def _title(ws, row, col_span, text, subtitle=None):
    """Banner de título (fondo navy, texto blanco) + subtítulo opcional.
    Devuelve la fila donde debe continuar el contenido."""
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=col_span)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=_FONT, size=16, bold=True, color=WHITE)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for col in range(1, col_span + 1):
        ws.cell(row=row, column=col).fill = PatternFill("solid", fgColor=NAVY)
    ws.row_dimensions[row].height = 30

    next_row = row + 1
    if subtitle:
        ws.merge_cells(start_row=next_row, start_column=1, end_row=next_row, end_column=col_span)
        c2 = ws.cell(row=next_row, column=1, value=subtitle)
        c2.font = Font(name=_FONT, size=10, italic=True, color=TEXT_SECONDARY)
        c2.alignment = Alignment(horizontal="left", indent=1)
        ws.row_dimensions[next_row].height = 18
        next_row += 1
    return next_row


def _kpi_card(ws, row, col_start, col_end, label, value, fill_hex):
    """Tarjeta KPI de 2 filas: etiqueta pequeña arriba, valor grande abajo."""
    ws.merge_cells(start_row=row, start_column=col_start, end_row=row, end_column=col_end)
    ws.merge_cells(start_row=row + 1, start_column=col_start, end_row=row + 2, end_column=col_end)

    lc = ws.cell(row=row, column=col_start, value=str(label).upper())
    lc.font = Font(name=_FONT, size=9, bold=True, color=WHITE)
    lc.alignment = Alignment(horizontal="center", vertical="center")

    vc = ws.cell(row=row + 1, column=col_start, value=value)
    vc.font = Font(name=_FONT, size=17, bold=True, color=WHITE)
    vc.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r in (row, row + 1, row + 2):
        for c in range(col_start, col_end + 1):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=fill_hex)
    ws.row_dimensions[row].height = 16
    ws.row_dimensions[row + 1].height = 28
    ws.row_dimensions[row + 2].height = 6


def _header_row(ws, row, headers, start_col=1):
    for i, h in enumerate(headers):
        c = ws.cell(row=row, column=start_col + i, value=h)
        c.font = Font(name=_FONT, size=10.5, bold=True, color=WHITE)
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER_ALL
    ws.row_dimensions[row].height = 28


def _autosize(ws, ncols, start_col=1, min_w=11, max_w=42):
    for i in range(ncols):
        col_letter = get_column_letter(start_col + i)
        longest = 0
        for cell in ws[col_letter]:
            v = cell.value
            if v is not None:
                longest = max(longest, len(str(v)))
        ws.column_dimensions[col_letter].width = max(min_w, min(max_w, longest + 4))


def _band_fill(row_offset):
    return PatternFill("solid", fgColor=BAND if row_offset % 2 else WHITE)


# ---------------------------------------------------------------------------
# 1) Comparativa de modelos
# ---------------------------------------------------------------------------
def build_comparativa_excel(results_df, best_info, report_name, model_colors=None):
    model_colors = model_colors or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparativa"

    ncols = 7  # swatch + Modelo + MAE + RMSE + R2 + MAPE + % Mejora
    next_row = _title(
        ws, 1, ncols, "🏆 Comparativa de Modelos — ImportPredic",
        f"Reporte: {report_name}  ·  Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    best_row = results_df.loc[results_df["Modelo"] == best_info["best_model_name"]].iloc[0]
    row = next_row + 1
    _kpi_card(ws, row, 1, 2, "Mejor modelo", best_info["best_model_name"], DENIM)
    _kpi_card(ws, row, 3, 4, "RMSE", f"{best_row['RMSE']:,.0f} kg", SAGE)
    _kpi_card(
        ws, row, 5, 7, "Mejora vs ARIMA",
        f"{best_row['% Mejora vs ARIMA (RMSE)']:.1f}%",
        SAGE if best_info["hypothesis_confirmed"] else ROSE,
    )
    row += 4

    headers = ["", "Modelo", "MAE", "RMSE", "R²", "MAPE (%)", "Mejora vs ARIMA (%)"]
    header_row_idx = row
    _header_row(ws, row, headers)
    row += 1
    first_data_row = row

    for offset, (_, r) in enumerate(results_df.sort_values("RMSE").iterrows()):
        is_best = r["Modelo"] == best_info["best_model_name"]
        is_baseline = r["Modelo"] == "ARIMA"

        swatch = ws.cell(row=row, column=1, value="")
        swatch.fill = PatternFill("solid", fgColor=model_colors.get(r["Modelo"], "#94A3B8").lstrip("#"))
        swatch.border = BORDER_ALL

        vals = [r["Modelo"], r["MAE"], r["RMSE"], r["R2"], r["MAPE"], r["% Mejora vs ARIMA (RMSE)"]]
        for i, v in enumerate(vals, start=2):
            c = ws.cell(row=row, column=i, value=v)
            c.border = BORDER_ALL
            c.alignment = Alignment(horizontal="left" if i == 2 else "center", vertical="center")
            if i in (3, 4):
                c.number_format = "#,##0"
            elif i == 5:
                c.number_format = "0.000"
            elif i in (6, 7):
                c.number_format = '0.00"%"'

            if is_best:
                c.fill = PatternFill("solid", fgColor=SAGE)
                c.font = Font(name=_FONT, bold=True, color=WHITE)
            else:
                c.fill = _band_fill(offset)
                if is_baseline:
                    c.font = Font(name=_FONT, italic=True, color=TEXT_SECONDARY)
        row += 1

    last_data_row = row - 1
    ws.freeze_panes = ws.cell(row=header_row_idx + 1, column=2)
    ws.auto_filter.ref = f"B{header_row_idx}:G{last_data_row}"
    _autosize(ws, ncols)
    ws.column_dimensions["A"].width = 3

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 2) Datos procesados
# ---------------------------------------------------------------------------
# Columnas que son códigos/identificadores, no cantidades — se muestran
# como texto plano (sin separador de miles ni decimales forzados).
_CODE_LIKE_COLUMNS = {"partida_arancelaria", "codigo_partida", "hs_code"}


def _resolve_column_format(col, series):
    """Determina el formato numérico correcto para una columna completa,
    en vez de adivinar celda por celda (evita, p. ej., que un código
    arancelario como 2903.39 se muestre como si fuera dinero: 2,903.39)."""
    if col == "fecha":
        return "yyyy-mm-dd"
    if col in _CODE_LIKE_COLUMNS:
        return None
    if pd.api.types.is_integer_dtype(series):
        return "#,##0"
    if pd.api.types.is_float_dtype(series):
        return "#,##0.00" if series.abs().max() < 1000 else "#,##0"
    return None


def build_datos_excel(df, target_col, report_name):
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"

    headers = list(df.columns)
    ncols = len(headers)
    col_formats = {h: _resolve_column_format(h, df[h]) for h in headers}

    fecha_min = fecha_max = "—"
    if "fecha" in df.columns:
        fechas = pd.to_datetime(df["fecha"])
        fecha_min, fecha_max = fechas.min().strftime("%b %Y"), fechas.max().strftime("%b %Y")

    next_row = _title(
        ws, 1, ncols, "🗂️ Datos Procesados — ImportPredic",
        f"Reporte: {report_name}  ·  {len(df):,} registros  ·  "
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    row = next_row + 1
    _kpi_card(ws, row, 1, 2, "Registros", f"{len(df):,}", DENIM)
    _kpi_card(ws, row, 3, 4, "Período", f"{fecha_min} – {fecha_max}", GOLD)
    if target_col in df.columns:
        _kpi_card(ws, row, 5, min(6, ncols), f"Promedio {target_col}", f"{df[target_col].mean():,.0f}", SAGE)
    row += 4

    header_row_idx = row
    _header_row(ws, row, headers)
    row += 1
    first_data_row = row

    for offset, (_, r) in enumerate(df.iterrows()):
        for i, col in enumerate(headers, start=1):
            v = r[col]
            if col == "fecha":
                v = pd.to_datetime(v)
            elif col in _CODE_LIKE_COLUMNS:
                v = str(v)
            c = ws.cell(row=row, column=i, value=v)
            c.border = BORDER_ALL
            c.alignment = Alignment(horizontal="center")
            c.fill = _band_fill(offset)
            fmt = col_formats.get(col)
            if fmt:
                c.number_format = fmt
        row += 1

    last_data_row = row - 1
    ws.freeze_panes = ws.cell(row=header_row_idx + 1, column=1)
    ws.auto_filter.ref = f"A{header_row_idx}:{get_column_letter(ncols)}{last_data_row}"
    _autosize(ws, ncols)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 3) Pronósticos futuros
# ---------------------------------------------------------------------------
def build_pronosticos_excel(future_df, best_info, report_name):
    wb = Workbook()
    ws = wb.active
    ws.title = "Pronosticos"

    ncols = 5
    next_row = _title(
        ws, 1, ncols, "📈 Pronósticos — ImportPredic",
        f"Reporte: {report_name}  ·  Modelo: {best_info['best_model_name']}  ·  "
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )

    horizonte = len(future_df)
    primero = future_df.iloc[0]
    var_acum = 0.0
    if len(future_df) > 1 and future_df["prediccion"].iloc[0] != 0:
        var_acum = (future_df["prediccion"].iloc[-1] / future_df["prediccion"].iloc[0] - 1) * 100

    row = next_row + 1
    _kpi_card(ws, row, 1, 1, "Horizonte", f"{horizonte} meses", DENIM)
    _kpi_card(ws, row, 2, 3, "Próximo mes", f"{primero['prediccion']:,.0f} kg", SAGE)
    _kpi_card(ws, row, 4, 5, "Variación acumulada", f"{var_acum:+.1f}%", SAGE if var_acum >= 0 else ROSE)
    row += 4

    headers = ["Fecha", "Pronóstico (kg)", "Límite inferior", "Límite superior", "Variación mensual (%)"]
    header_row_idx = row
    _header_row(ws, row, headers)
    row += 1
    first_data_row = row

    for offset, (_, r) in enumerate(future_df.iterrows()):
        vals = [
            pd.to_datetime(r["fecha"]), r["prediccion"], r["limite_inferior"],
            r["limite_superior"], r["variacion_mensual_%"],
        ]
        for i, v in enumerate(vals, start=1):
            c = ws.cell(row=row, column=i, value=v)
            c.border = BORDER_ALL
            c.alignment = Alignment(horizontal="center")
            c.fill = _band_fill(offset)
            if i == 1:
                c.number_format = "mmm yyyy"
            elif i in (2, 3, 4):
                c.number_format = "#,##0"
            elif i == 5:
                c.number_format = '+0.00"%";-0.00"%"'
        row += 1

    last_data_row = row - 1
    ws.freeze_panes = ws.cell(row=header_row_idx + 1, column=1)
    ws.auto_filter.ref = f"A{header_row_idx}:E{last_data_row}"

    rule = ColorScaleRule(
        start_type="min", start_color="F0A3AF",
        mid_type="percentile", mid_value=50, mid_color="FFFFFF",
        end_type="max", end_color="8FE0B6",
    )
    ws.conditional_formatting.add(f"E{first_data_row}:E{last_data_row}", rule)

    _autosize(ws, ncols)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 4) Ficha del proyecto (equivalente "bonito" del metadata.json)
# ---------------------------------------------------------------------------
def build_metadata_excel(metadata, academic_info, report_name):
    wb = Workbook()
    ws = wb.active
    ws.title = "Ficha del Proyecto"
    ncols = 2

    next_row = _title(
        ws, 1, ncols, "📋 Ficha del Proyecto — ImportPredic",
        f"Reporte: {report_name}  ·  Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    )
    row = next_row + 1

    def _section(title):
        nonlocal row
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        c = ws.cell(row=row, column=1, value=title)
        c.font = Font(name=_FONT, bold=True, color=WHITE, size=11)
        c.fill = PatternFill("solid", fgColor=DENIM)
        c.alignment = Alignment(indent=1, vertical="center")
        ws.row_dimensions[row].height = 22
        row += 1

    def _field(label, value):
        nonlocal row
        lc = ws.cell(row=row, column=1, value=label)
        lc.font = Font(name=_FONT, bold=True, color=INK)
        lc.fill = PatternFill("solid", fgColor=LIGHT_BG)
        lc.border = BORDER_ALL
        lc.alignment = Alignment(vertical="top", indent=1)

        is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        vc = ws.cell(row=row, column=2, value=value if is_numeric else str(value))
        vc.border = BORDER_ALL
        vc.alignment = Alignment(wrap_text=True, vertical="top", indent=1,
                                  horizontal="right" if is_numeric else "left")
        if is_numeric:
            vc.number_format = "#,##0.00" if isinstance(value, float) else "#,##0"
        row += 1

    _section("Información académica")
    _field("Universidad", academic_info["universidad"])
    _field("Programa", academic_info["programa"])
    _field("Línea de investigación", academic_info["linea_investigacion"])
    _field("Director", academic_info["director"])
    _field("Autor", academic_info["autor"])
    _field("Período analizado", academic_info["periodo_analisis"])
    row += 1

    _section("Resultados del modelo")
    _field("Modelo seleccionado", metadata["modelo"])
    metric_labels = {
        "MAE": "MAE", "RMSE": "RMSE", "R2": "R²", "MAPE": "MAPE (%)",
        "% Mejora vs ARIMA (RMSE)": "Mejora vs ARIMA (%)",
    }
    for k, v in metadata["metricas"].items():
        if k == "Modelo":
            continue
        if isinstance(v, float):
            v = round(v, 3)
        _field(metric_labels.get(k, k), v)
    _field("Criterio de mejora del 15 %", "Cumplido ✓" if metadata["hipotesis_confirmada"] else "No cumplido ✗")
    row += 1

    _section("Metadatos del reporte")
    _field("Nombre del reporte", metadata["reporte"])
    _field("Generado en", metadata["generado_en"])

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 62

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
