"""
src/reports/pdf_report.py
Generador del Reporte Final de Proyecto en PDF: documento profesional
de varias paginas (portada, resumen ejecutivo, estadisticas, metricas
del modelo, pruebas de hipotesis, importancia de variables,
pronosticos y metodologia), ensamblado con fpdf2 + graficas estaticas
de matplotlib (src/reports/charts.py) -- sin dependencias de
navegador.
"""
import os
from datetime import datetime

import matplotlib
import numpy as np
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src.reports import charts as ch

FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")

# ---- Paleta del reporte ----
NAVY = (38, 48, 58)
GOLD = (196, 148, 60)
ROSE = (176, 84, 96)
SAGE = (86, 140, 108)
DENIM = (76, 122, 158)
INK = (45, 48, 58)
TEXT_SECONDARY = (110, 110, 122)
LIGHT_BG = (245, 244, 250)
CARD_BORDER = (228, 226, 236)

PAGE_W = 210
MARGIN = 16
CONTENT_W = PAGE_W - 2 * MARGIN

_MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_larga_es(dt):
    return f"{dt.day} de {_MESES_ES[dt.month - 1]} de {dt.year}, {dt.strftime('%H:%M')}"


def _tint(rgb, factor):
    """Mezcla un color con blanco (factor 0 = color puro, 1 = blanco)."""
    return tuple(int(c + (255 - c) * factor) for c in rgb)


class ReportPDF(FPDF):
    def __init__(self, project_title="ImportPredic"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.project_title = project_title
        self.set_margins(MARGIN, 20, MARGIN)
        self.set_auto_page_break(auto=True, margin=24)
        self.add_font("DejaVu", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf"))
        self.set_font("DejaVu", "", 10.5)
        self.set_text_color(*INK)
        self.section_num = 0

    def header(self):
        # La portada es siempre la pagina 1: se comprueba directamente
        # por numero de pagina (mas fiable que una bandera "is_cover"
        # manual, ya que header()/footer() se ejecutan de forma
        # diferida -- al iniciar la SIGUIENTE pagina -- momento en el
        # que una bandera ya pudo haber sido reseteada).
        if self.page_no() == 1:
            return
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 14, style="F")
        self.set_xy(MARGIN, 3)
        self.set_font("DejaVu", "B", 10)
        self.set_text_color(255, 255, 255)
        self.cell(100, 8, self.project_title)
        self.set_xy(PAGE_W - MARGIN - 75, 3)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(215, 215, 222)
        self.cell(75, 8, "Reporte Final de Proyecto de Grado", align="R")
        self.set_y(20)
        self.set_text_color(*INK)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-16)
        self.set_draw_color(*CARD_BORDER)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-13)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_SECONDARY)
        self.cell(CONTENT_W / 2, 8, f"{self.project_title} \u2014 generado el {datetime.now().strftime('%d/%m/%Y')}")
        self.cell(CONTENT_W / 2, 8, f"P\u00e1gina {self.page_no() - 1}", align="R")

    # ---------------- helpers de contenido ----------------

    def section_title(self, title):
        self.section_num += 1
        self.ln(2)
        # Se verifica el espacio disponible ANTES de dibujar nada: el
        # rectangulo de acento (rect) no dispara el salto de pagina
        # automatico como si lo hace cell()/multi_cell(), asi que sin
        # este chequeo la barra de color podia quedar "huerfana" al
        # final de una pagina y el titulo aparecer solo en la siguiente.
        if self.get_y() + 14 > self.page_break_trigger:
            self.add_page()
        y = self.get_y()
        self.set_fill_color(*NAVY)
        self.rect(MARGIN, y + 0.5, 3.2, 7.5, style="F")
        self.set_xy(MARGIN + 6, y)
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(*NAVY)
        self.cell(0, 8.5, f"{self.section_num}.  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self.set_draw_color(*CARD_BORDER)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.ln(4)
        self.set_text_color(*INK)
        self.set_font("DejaVu", "", 10.5)

    def subsection_title(self, title):
        self.ln(1)
        self.set_font("DejaVu", "B", 11.5)
        self.set_text_color(*NAVY)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self.set_font("DejaVu", "", 10.5)
        self.set_text_color(*INK)

    def paragraph(self, text, size=10.5, color=INK, align="J"):
        self.set_font("DejaVu", "", size)
        self.set_text_color(*color)
        self.multi_cell(CONTENT_W, 5.6, text, align=align)
        self.ln(1.5)

    def bullet_list(self, items):
        self.set_font("DejaVu", "", 10.5)
        for it in items:
            x0, y0 = self.get_x(), self.get_y()
            self.set_text_color(*GOLD)
            self.cell(5, 5.6, "\u2022")
            self.set_text_color(*INK)
            self.set_xy(x0 + 5, y0)
            self.multi_cell(CONTENT_W - 5, 5.6, it)
            self.set_x(MARGIN)
        self.ln(1)

    def kpi_cards(self, items):
        """items: lista de (label, value, sublabel_o_None, color_rgb)"""
        n = len(items)
        gap = 4
        w = (CONTENT_W - gap * (n - 1)) / n
        h = 25
        if self.get_y() + h > self.page_break_trigger:
            self.add_page()
        y0 = self.get_y()
        for i, (label, value, sub, color) in enumerate(items):
            x = MARGIN + i * (w + gap)
            self.set_fill_color(*LIGHT_BG)
            self.set_draw_color(*CARD_BORDER)
            self.rect(x, y0, w, h, style="DF")
            self.set_fill_color(*color)
            self.rect(x, y0, 2, h, style="F")
            self.set_xy(x + 4.5, y0 + 3)
            self.set_font("DejaVu", "", 7.6)
            self.set_text_color(*TEXT_SECONDARY)
            self.multi_cell(w - 6, 3.4, label.upper())
            self.set_xy(x + 4.5, y0 + 10)
            self.set_font("DejaVu", "B", 14.5)
            self.set_text_color(*color)
            self.cell(w - 6, 8, str(value))
            if sub:
                self.set_xy(x + 4.5, y0 + 19)
                self.set_font("DejaVu", "", 7.2)
                self.set_text_color(*TEXT_SECONDARY)
                self.cell(w - 6, 4, sub)
        self.set_xy(MARGIN, y0 + h + 6)

    def table(self, headers, rows, col_widths=None, highlight_row=None, align_cols=None, line_h=5.0):
        n = len(headers)
        col_widths = col_widths or [CONTENT_W / n] * n
        align_cols = align_cols or ["L"] * n
        header_h = 7.2

        def _draw_header():
            self.set_font("DejaVu", "B", 8.8)
            self.set_fill_color(*NAVY)
            self.set_text_color(255, 255, 255)
            for w, htxt, al in zip(col_widths, headers, align_cols):
                self.cell(w, header_h, htxt, align=al, fill=True)
            self.ln(header_h)

        _draw_header()
        self.set_font("DejaVu", "", 8.8)

        for ridx, row in enumerate(rows):
            # Se calcula cuantas lineas necesita cada celda (dry run,
            # sin dibujar) para poder dar a TODA la fila el alto de su
            # celda mas larga -- evita que el texto largo (p.ej. las
            # conclusiones de las pruebas estadisticas) se corte o se
            # salga del margen de la pagina.
            lines_counts = []
            for w, val in zip(col_widths, row):
                lines = self.multi_cell(w - 2, line_h, str(val), align="L", dry_run=True, output="LINES")
                lines_counts.append(max(1, len(lines)))
            row_h = line_h * max(lines_counts)

            if self.get_y() + row_h > self.page_break_trigger:
                self.add_page()
                _draw_header()
                self.set_font("DejaVu", "", 8.8)

            is_best = (highlight_row is not None and ridx == highlight_row)
            if is_best:
                fill_color = _tint(GOLD, 0.80)
            elif ridx % 2 == 1:
                fill_color = LIGHT_BG
            else:
                fill_color = (255, 255, 255)

            x_row, y_row = self.get_x(), self.get_y()
            self.set_fill_color(*fill_color)
            self.rect(x_row, y_row, sum(col_widths), row_h, style="F")

            self.set_text_color(*(NAVY if is_best else INK))
            x = x_row
            for w, val, al in zip(col_widths, row, align_cols):
                self.set_xy(x, y_row)
                self.multi_cell(w, line_h, str(val), align=al)
                x += w
            self.set_xy(x_row, y_row + row_h)
        self.ln(3)

    def image_block(self, path, caption=None, w=None):
        w = w or CONTENT_W
        x = MARGIN + (CONTENT_W - w) / 2
        self.image(path, x=x, w=w)
        if caption:
            self.set_font("DejaVu", "I", 8.5)
            self.set_text_color(*TEXT_SECONDARY)
            self.cell(0, 5, caption, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def conclusion_badge(self, confirmed, text):
        color = SAGE if confirmed else ROSE
        self.set_font("DejaVu", "B", 10)
        lines = self.multi_cell(CONTENT_W - 8, 5.2, text, align="L", dry_run=True, output="LINES")
        h = 6 + 5.2 * len(lines)
        if self.get_y() + h > self.page_break_trigger:
            self.add_page()
        y0 = self.get_y()
        self.set_fill_color(*_tint(color, 0.85))
        self.set_draw_color(*color)
        self.rect(MARGIN, y0, CONTENT_W, h, style="DF")
        self.set_xy(MARGIN + 4, y0 + 3)
        self.set_text_color(*color)
        self.multi_cell(CONTENT_W - 8, 5.2, text)
        self.set_y(y0 + h + 5)


# ============================================================
# CONSTRUCCION DEL REPORTE
# ============================================================

def _cover_page(pdf, report_name, academic_info):
    # Se desactiva temporalmente el salto de pagina automatico: el
    # bloque final (fecha + nombre del reporte) queda muy cerca del
    # margen inferior y, con el salto automatico activo, esas dos
    # ultimas lineas se empujaban a una segunda pagina en blanco.
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, PAGE_W, 115, style="F")
    pdf.set_fill_color(*GOLD)
    pdf.rect(0, 115, PAGE_W, 2.4, style="F")

    pdf.set_xy(MARGIN, 42)
    pdf.set_font("DejaVu", "B", 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "ImportPredic", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(MARGIN)
    pdf.set_font("DejaVu", "", 12.5)
    pdf.set_text_color(222, 220, 232)
    pdf.multi_cell(CONTENT_W, 6.5,
                    "Sistema de pron\u00f3stico de importaciones cr\u00edticas mediante "
                    "modelos de Machine Learning")

    pdf.set_xy(MARGIN, 88)
    pdf.set_font("DejaVu", "B", 14.5)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 8, "Reporte Final de Proyecto de Grado", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    rows = [
        ("Universidad", academic_info.get("universidad", "")),
        ("Programa", academic_info.get("programa", "")),
        ("L\u00ednea de investigaci\u00f3n", academic_info.get("linea_investigacion", "")),
        ("Autor", academic_info.get("autor", "")),
        ("Director", academic_info.get("director", "")),
        ("Per\u00edodo analizado", academic_info.get("periodo_analisis", "")),
    ]
    y = 140
    pdf.set_xy(MARGIN, y)
    for label, value in rows:
        pdf.set_x(MARGIN)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(50, 7.5, label)
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(*INK)
        pdf.cell(CONTENT_W - 50, 7.5, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_draw_color(*CARD_BORDER)
    pdf.line(MARGIN, y - 4, PAGE_W - MARGIN, y - 4)

    pdf.set_y(-32)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*TEXT_SECONDARY)
    pdf.cell(0, 6, f"Reporte generado autom\u00e1ticamente el {_fecha_larga_es(datetime.now())}",
              align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("DejaVu", "I", 8.5)
    pdf.cell(0, 6, report_name, align="C")

    pdf.set_auto_page_break(auto=True, margin=24)


def _section_resumen_ejecutivo(pdf, best_info, academic_info, insumos_criticos):
    pdf.add_page()
    pdf.section_title("Resumen ejecutivo")

    m = best_info["metrics"]
    pdf.kpi_cards([
        ("Mejor modelo", best_info["best_model_name"], None, NAVY),
        ("RMSE", f"{m['RMSE']:,.0f} kg", "Error cuadr\u00e1tico medio", GOLD),
        ("R\u00b2", f"{m['R2']:.3f}", "Varianza explicada", DENIM),
        ("Mejora vs ARIMA", f"{m['% Mejora vs ARIMA (RMSE)']:+.1f}%", "en RMSE", SAGE),
    ])

    confirmed = best_info["hypothesis_confirmed"]
    pdf.conclusion_badge(
        confirmed,
        ("\u2713 CRITERIO DEL 15 % CUMPLIDO: " if confirmed else "\u2717 CRITERIO DEL 15 % NO CUMPLIDO: ")
        + f"el modelo {best_info['best_model_name']} "
        + (f"mejora el RMSE frente a ARIMA en {m['% Mejora vs ARIMA (RMSE)']:.1f}%, "
           f"superando el umbral objetivo del proyecto."
           if confirmed else
           f"obtiene una mejora de {m['% Mejora vs ARIMA (RMSE)']:.1f}% frente a ARIMA, "
           f"insuficiente frente al umbral objetivo del proyecto.")
    )

    pdf.subsection_title("Alcance del proyecto")
    pdf.paragraph(
        f"Este reporte documenta los resultados del sistema ImportPredic para el pron\u00f3stico "
        f"del volumen de importaci\u00f3n de insumos cr\u00edticos, desarrollado sobre el per\u00edodo "
        f"{academic_info.get('periodo_analisis', '')}. Se evaluaron m\u00faltiples algoritmos de "
        f"Machine Learning frente a un modelo estad\u00edstico de referencia (ARIMA). "
        f"Objetivo del proyecto: {academic_info.get('objetivo', 'mejorar la capacidad de pron\u00f3stico')}."
    )
    pdf.subsection_title("Insumos cr\u00edticos analizados")
    pdf.bullet_list([f"{cod} \u2014 {desc}" for cod, desc in insumos_criticos.items()])


def _section_estadisticas(pdf, df, target_col):
    pdf.section_title("Estad\u00edsticas descriptivas")
    serie = df[target_col].dropna()
    desc = serie.describe()
    pdf.subsection_title("Variable objetivo: volumen de importaci\u00f3n (kg)")
    pdf.table(
        ["M\u00e9trica", "Valor"],
        [
            ["N\u00famero de observaciones", f"{int(desc['count']):,}"],
            ["Media", f"{desc['mean']:,.1f} kg"],
            ["Mediana", f"{serie.median():,.1f} kg"],
            ["Desviaci\u00f3n est\u00e1ndar", f"{desc['std']:,.1f} kg"],
            ["M\u00ednimo", f"{desc['min']:,.1f} kg"],
            ["M\u00e1ximo", f"{desc['max']:,.1f} kg"],
            ["Asimetr\u00eda (skewness)", f"{serie.skew():.3f}"],
            ["Curtosis", f"{serie.kurt():.3f}"],
        ],
        col_widths=[CONTENT_W * 0.6, CONTENT_W * 0.4],
        align_cols=["L", "R"],
    )
    path = ch.chart_histogram(serie)
    pdf.image_block(path, caption="Distribuci\u00f3n del volumen de importaci\u00f3n mensual (2015\u20132024)",
                     w=CONTENT_W * 0.85)


def _section_metricas(pdf, results_df, best_info):
    pdf.section_title("M\u00e9tricas del modelo")
    pdf.subsection_title("Comparativa de todos los modelos evaluados")
    df = results_df.sort_values("RMSE").reset_index(drop=True)
    best_idx = df.index[df["Modelo"] == best_info["best_model_name"]][0]
    pdf.table(
        ["Modelo", "MAE", "RMSE", "R\u00b2", "MAPE", "Mejora vs ARIMA"],
        [[r["Modelo"], f"{r['MAE']:,.0f}", f"{r['RMSE']:,.0f}", f"{r['R2']:.3f}",
          f"{r['MAPE']:.2f}%", f"{r['% Mejora vs ARIMA (RMSE)']:+.1f}%"] for _, r in df.iterrows()],
        col_widths=[CONTENT_W * 0.24, CONTENT_W * 0.15, CONTENT_W * 0.15, CONTENT_W * 0.13,
                    CONTENT_W * 0.13, CONTENT_W * 0.20],
        align_cols=["L", "R", "R", "R", "R", "R"],
        highlight_row=int(best_idx),
    )
    path = ch.chart_model_comparison(df, best_info["best_model_name"])
    pdf.image_block(path, caption="RMSE por modelo (el modelo destacado en dorado es el seleccionado)",
                     w=CONTENT_W * 0.85)


def _section_pruebas(pdf, hyp_results, res_analysis):
    pdf.section_title("Pruebas estad\u00edsticas \u2014 verificaci\u00f3n de hip\u00f3tesis")
    sh = hyp_results["shapiro_wilk"]
    dm = hyp_results["diebold_mariano"]
    pt = hyp_results["parametric_test"]
    pdf.table(
        ["Prueba", "Estad\u00edstico", "p-valor", "Conclusi\u00f3n"],
        [
            ["Shapiro-Wilk (normalidad)", f"{sh['statistic']:.4f}", f"{sh['p_value']:.4f}", sh["conclusion"]],
            ["Diebold-Mariano (poder predictivo)", f"{dm['dm_stat']:.4f}", f"{dm['p_value']:.4f}", dm["conclusion"]],
            [hyp_results["test_used"], f"{pt.get('statistic', pt.get('t_statistic', 0)):.4f}",
             f"{pt['p_value']:.4f}", pt["conclusion"]],
        ],
        col_widths=[CONTENT_W * 0.28, CONTENT_W * 0.13, CONTENT_W * 0.13, CONTENT_W * 0.46],
        align_cols=["L", "R", "R", "L"],
    )
    pdf.conclusion_badge(hyp_results["hypothesis_confirmed"], hyp_results["final_conclusion"])

    if res_analysis is not None:
        pdf.subsection_title("An\u00e1lisis de residuos del mejor modelo")
        pdf.table(
            ["M\u00e9trica", "Valor", "Interpretaci\u00f3n"],
            [
                ["Media de residuos", f"{res_analysis['media']:.1f}",
                 "Cercana a 0 indica ausencia de sesgo sistem\u00e1tico"],
                ["Asimetr\u00eda", f"{res_analysis['skewness']:.3f}", "Cercana a 0 indica distribuci\u00f3n sim\u00e9trica"],
                ["Durbin-Watson", f"{res_analysis['durbin_watson']:.3f}",
                 "Cercano a 2 indica ausencia de autocorrelaci\u00f3n serial"],
            ],
            col_widths=[CONTENT_W * 0.28, CONTENT_W * 0.15, CONTENT_W * 0.57],
            align_cols=["L", "R", "L"],
        )


def _section_importancia(pdf, shap_df):
    pdf.section_title("Importancia de variables (SHAP)")
    pdf.paragraph(
        "Los valores SHAP (SHapley Additive exPlanations) cuantifican cu\u00e1nto aporta cada "
        "variable, en promedio, a las predicciones del modelo. Un valor m\u00e1s alto indica mayor "
        "influencia sobre el volumen de importaci\u00f3n pronosticado."
    )
    top = shap_df.head(10).reset_index(drop=True)
    pdf.table(
        ["#", "Variable", "Importancia media |SHAP|"],
        [[i + 1, r["variable"], f"{r['mean_abs_shap']:.4f}"] for i, r in top.iterrows()],
        col_widths=[CONTENT_W * 0.08, CONTENT_W * 0.62, CONTENT_W * 0.30],
        align_cols=["C", "L", "R"],
    )
    path = ch.chart_shap_importance(shap_df)
    pdf.image_block(path, caption="Top 10 variables por importancia media SHAP", w=CONTENT_W * 0.85)


def _section_pronosticos(pdf, future_df, dataset_processed, target_col):
    pdf.section_title("Pron\u00f3sticos futuros")
    pdf.paragraph(
        f"Proyecci\u00f3n del volumen de importaci\u00f3n para los pr\u00f3ximos {len(future_df)} meses, "
        f"con un intervalo de confianza del 95% calculado a partir del error hist\u00f3rico del modelo."
    )
    rows = []
    for _, r in future_df.iterrows():
        fecha = pd.to_datetime(r["fecha"]).strftime("%b %Y")
        rows.append([fecha, f"{r['prediccion']:,.0f}",
                     f"{r.get('limite_inferior', float('nan')):,.0f}",
                     f"{r.get('limite_superior', float('nan')):,.0f}"])
    pdf.table(
        ["Mes", "Pron\u00f3stico (kg)", "L\u00edmite inferior", "L\u00edmite superior"],
        rows,
        col_widths=[CONTENT_W * 0.22, CONTENT_W * 0.26, CONTENT_W * 0.26, CONTENT_W * 0.26],
        align_cols=["L", "R", "R", "R"],
    )
    path = ch.chart_forecast(dataset_processed["fecha"], dataset_processed[target_col], future_df)
    pdf.image_block(path, caption="Hist\u00f3rico reciente y pron\u00f3stico con intervalo de confianza del 95%",
                     w=CONTENT_W * 0.9)


def _section_metodologia(pdf, academic_info):
    pdf.section_title("Metodolog\u00eda y conclusiones")
    pdf.subsection_title("Enfoque metodol\u00f3gico")
    pdf.paragraph(
        "El desarrollo sigui\u00f3 un enfoque cuantitativo: carga y validaci\u00f3n de datos hist\u00f3ricos "
        "de importaci\u00f3n y variables macroecon\u00f3micas, an\u00e1lisis exploratorio y de estacionalidad, "
        "ingenier\u00eda de variables (rezagos y promedios m\u00f3viles), entrenamiento y comparaci\u00f3n de "
        "m\u00faltiples algoritmos de Machine Learning frente a un modelo ARIMA de referencia, y "
        "validaci\u00f3n mediante pruebas estad\u00edsticas formales de superioridad predictiva."
    )
    pdf.subsection_title("Limitaciones del estudio")
    pdf.bullet_list([
        "El modelo se entren\u00f3 con datos hist\u00f3ricos mensuales; eventos abruptos no representados "
        "en el hist\u00f3rico (crisis, cambios regulatorios) pueden afectar la precisi\u00f3n futura.",
        "Los pron\u00f3sticos asumen que las variables macroecon\u00f3micas independientes se mantienen "
        "dentro de rangos hist\u00f3ricos observados.",
        "El desempe\u00f1o fue validado sobre un \u00fanico corte temporal de prueba; se recomienda "
        "validaci\u00f3n continua con datos nuevos.",
    ])


def build_report_pdf(
    *, report_name, academic_info, insumos_criticos, best_info, results_df,
    dataset_processed, target_col, sections=None,
    predictions_future=None, shap_df=None, hyp_results=None, res_analysis=None,
):
    sections = sections or []
    pdf = ReportPDF()

    _cover_page(pdf, report_name, academic_info)
    _section_resumen_ejecutivo(pdf, best_info, academic_info, insumos_criticos)

    if "Estadísticas descriptivas" in sections:
        _section_estadisticas(pdf, dataset_processed, target_col)

    if "Métricas del modelo" in sections:
        _section_metricas(pdf, results_df, best_info)

    if "Pruebas estadísticas" in sections and hyp_results is not None:
        _section_pruebas(pdf, hyp_results, res_analysis)

    if "Importancia de variables" in sections and shap_df is not None and len(shap_df) > 0:
        _section_importancia(pdf, shap_df)

    if "Pronósticos futuros" in sections and predictions_future is not None and len(predictions_future) > 0:
        _section_pronosticos(pdf, predictions_future, dataset_processed, target_col)

    _section_metodologia(pdf, academic_info)

    out = bytes(pdf.output())
    ch.cleanup_temp_charts()
    return out
