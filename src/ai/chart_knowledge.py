# -*- coding: utf-8 -*-
"""
src/ai/chart_knowledge.py

Base de conocimiento centralizada de TODAS las graficas del sistema
ImportPredic. Este modulo resuelve el problema de que la IA no puede
"ver" las imagenes de Plotly: en su lugar, calcula estadisticas reales
sobre los mismos datos que alimentan cada grafica, y le entrega a la IA
un resumen numerico preciso de lo que efectivamente se dibujo.

FIX v1.3.2: Se corrigio un KeyError en describe_residuos_vs_tiempo()
que ocurria cuando 'dates' llegaba como pd.Series con un indice no
reseteado (por ejemplo, tras un train/test split que conserva los
indices originales del DataFrame). El acceso dates[idx_max] intentaba
buscar la ETIQUETA idx_max en el indice de la Serie, no la posicion,
lanzando KeyError cuando esa etiqueta no existia. Ahora se normaliza
siempre a una lista plana indexada desde 0 antes de acceder por posicion.
"""

import numpy as np
import pandas as pd


CHART_REGISTRY = {
    "serie_tiempo_principal": {
        "pagina": "exploracion",
        "que_es": (
            "Grafico de linea temporal que muestra el volumen de importacion "
            "mes a mes desde 2015 hasta 2024, con marcadores verticales en "
            "eventos economicos relevantes (pandemia, crisis cambiaria)."
        ),
        "como_leerla": (
            "El eje X es el tiempo (fecha), el eje Y es el volumen en kg. "
            "Se debe identificar la direccion general (sube/baja/estable), "
            "la presencia de ciclos repetitivos (estacionalidad), y "
            "desviaciones puntuales coincidentes con eventos marcados."
        ),
    },
    "descomposicion_stl": {
        "pagina": "exploracion",
        "que_es": (
            "Descomposicion STL de la serie en 3 componentes superpuestos: "
            "Tendencia (linea suave de largo plazo), Estacionalidad (patron "
            "ciclico que se repite cada 12 meses) y Residuo (lo que sobra "
            "tras remover tendencia y estacionalidad)."
        ),
        "como_leerla": (
            "La tendencia debe verse como una linea suave sin saltos. La "
            "estacionalidad debe oscilar de forma regular y simetrica "
            "alrededor de cero. El residuo debe verse como ruido aleatorio "
            "sin patron; picos grandes en el residuo señalan eventos que "
            "el modelo STL no pudo explicar (outliers)."
        ),
    },
    "matriz_correlacion": {
        "pagina": "exploracion",
        "que_es": (
            "Mapa de calor (heatmap) con el coeficiente de correlacion de "
            "Pearson entre todas las variables numericas del dataset, "
            "incluyendo variables derivadas (lags, rolling means)."
        ),
        "como_leerla": (
            "Colores intensos (rojo/rosado) indican correlacion positiva "
            "fuerte cercana a 1. Colores frios (cyan/azul) indican "
            "correlacion negativa fuerte cercana a -1. Colores oscuros "
            "cercanos al centro de la escala indican correlacion casi nula."
        ),
    },
    "estacionalidad_radial": {
        "pagina": "exploracion",
        "que_es": (
            "Grafico radial (tipo radar) que muestra el volumen promedio "
            "de cada mes del año, permitiendo ver el patron estacional "
            "de forma circular."
        ),
        "como_leerla": (
            "Los meses con mayor 'extension' del poligono hacia afuera son "
            "los de mayor demanda historica promedio. Un poligono perfectamente "
            "circular indicaria ausencia de estacionalidad."
        ),
    },
    "comparacion_anio_a_anio": {
        "pagina": "exploracion",
        "que_es": (
            "Multiples lineas superpuestas, una por cada año (2015-2024), "
            "mostrando el volumen mes a mes para comparar si el patron "
            "estacional se mantiene year-over-year."
        ),
        "como_leerla": (
            "Si las lineas tienen formas similares (mismos picos y valles "
            "en los mismos meses) pero a diferentes alturas, confirma "
            "estacionalidad estable con tendencia de crecimiento."
        ),
    },
    "boxplot_outliers": {
        "pagina": "exploracion",
        "que_es": (
            "Diagramas de caja (boxplot) por año, mostrando la mediana, "
            "los cuartiles y los valores atipicos (outliers) detectados "
            "por el metodo del rango intercuartilico (IQR)."
        ),
        "como_leerla": (
            "La caja representa el 50% central de los datos. Los puntos "
            "fuera de los 'bigotes' son outliers. Cajas de diferente "
            "altura entre años indican diferente variabilidad."
        ),
    },
    "histograma_qqplot": {
        "pagina": "exploracion",
        "que_es": (
            "Histograma con curva de densidad y QQ-Plot (grafico "
            "cuantil-cuantil) para evaluar si el volumen de importacion "
            "sigue una distribucion normal."
        ),
        "como_leerla": (
            "En el histograma, una forma de campana simetrica sugiere "
            "normalidad. En el QQ-Plot, los puntos deben seguir la linea "
            "diagonal de referencia; desviaciones en los extremos indican "
            "colas pesadas o asimetria."
        ),
    },
    "comparativa_modelos_barras": {
        "pagina": "entrenamiento",
        "que_es": (
            "Grafico de barras agrupadas comparando MAE y RMSE de cada "
            "modelo entrenado (XGBoost, Gradient Boosting, Random Forest, "
            "Ridge, Lasso, ARIMA)."
        ),
        "como_leerla": (
            "Barras mas bajas indican mejor desempeño (menor error). El "
            "modelo ganador es el de menor RMSE. La diferencia de altura "
            "entre el mejor modelo y ARIMA representa la mejora obtenida."
        ),
    },
    "predicciones_vs_reales": {
        "pagina": "entrenamiento",
        "que_es": (
            "Linea de valores reales superpuesta con la linea de valores "
            "predichos por el mejor modelo, sobre el periodo de prueba."
        ),
        "como_leerla": (
            "Cuanto mas se superpongan ambas lineas, mejor es el ajuste. "
            "Separaciones sistematicas (predicho siempre por encima o "
            "debajo del real) indican sesgo del modelo."
        ),
    },
    "residuos_vs_tiempo": {
        "pagina": "entrenamiento_y_evaluacion",
        "que_es": (
            "Grafico de linea que muestra el residuo (valor real menos "
            "valor predicho) para cada fecha del periodo de prueba."
        ),
        "como_leerla": (
            "Los residuos deben oscilar aleatoriamente alrededor de cero, "
            "sin tendencia ni patron ciclico. Una tendencia visible indica "
            "que el modelo no capturo toda la señal. Un ensanchamiento de "
            "la dispersion hacia el final indica heterocedasticidad."
        ),
    },
    "histograma_residuos": {
        "pagina": "entrenamiento_y_evaluacion",
        "que_es": (
            "Histograma de la distribucion de los residuos del modelo."
        ),
        "como_leerla": (
            "Una forma de campana centrada en cero sugiere errores bien "
            "comportados (insesgados). Asimetria hacia un lado indica que "
            "el modelo tiende a sobreestimar o subestimar sistematicamente."
        ),
    },
    "pronostico_horizonte": {
        "pagina": "prediccion",
        "que_es": (
            "Serie historica completa (gris) seguida de la proyeccion "
            "futura (cyan) con una banda de confianza del 95% sombreada, "
            "separada por una linea vertical punteada magenta."
        ),
        "como_leerla": (
            "El ancho de la banda de confianza indica la incertidumbre: "
            "bandas mas anchas en meses mas lejanos son normales. La "
            "pendiente de la linea de pronostico indica si se espera "
            "crecimiento o caida en el volumen futuro."
        ),
    },
    "rmse_por_cuatrimestre": {
        "pagina": "evaluacion",
        "que_es": (
            "Grafico de barras o linea que muestra el RMSE calculado "
            "por separado en distintos cuatrimestres del periodo de "
            "prueba, para evaluar estabilidad temporal (concept drift)."
        ),
        "como_leerla": (
            "Si el RMSE crece progresivamente entre cuatrimestres, el "
            "modelo esta perdiendo precision con el tiempo (deriva del "
            "modelo). Un RMSE estable indica un modelo robusto."
        ),
    },
    "shap_importancia_global": {
        "pagina": "interpretabilidad",
        "que_es": (
            "Grafico de barras horizontales con el valor absoluto medio "
            "de SHAP para cada variable, ordenado de mayor a menor "
            "influencia sobre la prediccion del modelo."
        ),
        "como_leerla": (
            "Barras mas largas indican variables con mayor peso promedio "
            "en las predicciones del modelo, sin importar la direccion "
            "del efecto (solo magnitud de influencia)."
        ),
    },
    "shap_summary_plot": {
        "pagina": "interpretabilidad",
        "que_es": (
            "Grafico de dispersion (scatter) que muestra, para la "
            "variable mas importante, como el SHAP value (impacto en la "
            "prediccion) se relaciona con el valor real de esa variable."
        ),
        "como_leerla": (
            "Puntos a la derecha del cero aumentan la prediccion, a la "
            "izquierda la disminuyen. El color o posicion de los puntos "
            "segun el valor de la variable revela si la relacion es "
            "positiva o negativa."
        ),
    },
    "shap_waterfall": {
        "pagina": "interpretabilidad",
        "que_es": (
            "Grafico de cascada que descompone UNA prediccion individual, "
            "mostrando como cada variable empuja el resultado desde el "
            "valor base (promedio general) hasta la prediccion final."
        ),
        "como_leerla": (
            "Barras verdes o hacia la derecha aumentan la prediccion, "
            "barras magenta o hacia la izquierda la reducen. La suma de "
            "todas las contribuciones mas el valor base da la prediccion final."
        ),
    },
    "coeficientes_modelo_lineal": {
        "pagina": "interpretabilidad",
        "que_es": (
            "Grafico de barras con los coeficientes del modelo Ridge o "
            "Lasso, mostrando el peso y direccion (positivo/negativo) "
            "de cada variable predictora."
        ),
        "como_leerla": (
            "Coeficientes positivos aumentan la prediccion cuando la "
            "variable sube; negativos la reducen. En Lasso, coeficientes "
            "exactamente en cero indican variables eliminadas del modelo."
        ),
    },
}


def _fmt(x, decimales=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "N/D"
    return "{:,.{}f}".format(x, decimales)


def _normalizar_fechas(dates):
    """
    Normaliza 'dates' a una lista plana indexada desde 0, sin importar
    si llega como pd.Series (con indice propio no reseteado), lista,
    DatetimeIndex o array de numpy.

    Este es el fix del KeyError: antes se accedia dates[idx_max]
    directamente, lo cual en una pd.Series busca por ETIQUETA de indice,
    no por POSICION. Si la Serie viene de un train/test split que
    conserva los indices originales del DataFrame (ej. indices 84-119
    en vez de 0-35), dates[6] fallaba con KeyError: 6 porque esa
    etiqueta no existe en el indice real de la Serie.
    """
    if isinstance(dates, pd.Series):
        return dates.reset_index(drop=True).tolist()
    if isinstance(dates, pd.DatetimeIndex):
        return list(dates)
    if isinstance(dates, (list, tuple, np.ndarray)):
        return list(dates)
    # Fallback generico para cualquier otro iterable
    return list(dates)


def describe_residuos_vs_tiempo(residuals, dates):
    """
    Calcula estadisticas reales de los residuos para describir
    exactamente lo que se ve en el grafico de residuos vs tiempo.

    Parametros:
        residuals: array-like de residuos (y_real - y_pred)
        dates: array-like de fechas correspondientes (Series, lista,
               DatetimeIndex o array; se normaliza internamente)
    """
    residuals = np.asarray(residuals, dtype=float)
    n = len(residuals)
    if n == 0:
        return {"resumen": "Sin datos de residuos disponibles."}

    dates_list = _normalizar_fechas(dates)

    media = float(np.mean(residuals))
    std = float(np.std(residuals))
    idx_max = int(np.argmax(np.abs(residuals)))

    if len(dates_list) > idx_max:
        try:
            peor_fecha = str(pd.Timestamp(dates_list[idx_max]).strftime("%Y-%m"))
        except (ValueError, TypeError):
            peor_fecha = str(dates_list[idx_max])
    else:
        peor_fecha = "N/D"

    peor_valor = float(residuals[idx_max])

    x = np.arange(n)
    if n > 2:
        pendiente = float(np.polyfit(x, residuals, 1)[0])
    else:
        pendiente = 0.0

    mitad = n // 2
    std_primera = float(np.std(residuals[:mitad])) if mitad > 1 else std
    std_segunda = float(np.std(residuals[mitad:])) if (n - mitad) > 1 else std
    cambio_dispersión_pct = (
        (std_segunda - std_primera) / std_primera * 100 if std_primera > 0 else 0
    )

    outliers_resid = int(np.sum(np.abs(residuals - media) > 2 * std)) if std > 0 else 0

    return {
        "n_observaciones": n,
        "media_residuos": media,
        "std_residuos": std,
        "residuo_maximo_absoluto": peor_valor,
        "fecha_peor_residuo": peor_fecha,
        "pendiente_tendencia_residuos": pendiente,
        "tiene_tendencia_visible": abs(pendiente) > (std * 0.01) if std > 0 else False,
        "cambio_dispersion_pct": cambio_dispersión_pct,
        "heterocedasticidad_detectada": abs(cambio_dispersión_pct) > 30,
        "outliers_en_residuos": outliers_resid,
        "resumen": (
            "Residuos con media {} kg y desviacion estandar {} kg sobre {} observaciones. "
            "El residuo mas grande fue {} kg en {}. "
            "{} La dispersion {} un {}% entre la primera y segunda mitad del periodo. "
            "Se detectaron {} residuos fuera de 2 desviaciones estandar."
        ).format(
            _fmt(media, 0), _fmt(std, 0), n,
            _fmt(peor_valor, 0), peor_fecha,
            "Se observa una tendencia sistematica en los residuos." if (std > 0 and abs(pendiente) > (std * 0.01))
                else "No se observa tendencia sistematica relevante en los residuos.",
            "aumento" if cambio_dispersión_pct > 0 else "disminuyo",
            _fmt(abs(cambio_dispersión_pct), 1),
            outliers_resid,
        ),
    }


def describe_correlation_matrix(df_numeric, target_col):
    """
    Calcula las correlaciones reales de TODAS las variables contra el
    objetivo, para que la IA pueda hablar de cualquier variable del
    heatmap, no solo de TRM e IPC.
    """
    if target_col not in df_numeric.columns:
        return {"resumen": "Variable objetivo no encontrada."}

    corrs = df_numeric.corr()[target_col].drop(target_col).sort_values(ascending=False)
    top3_pos = corrs.head(3)
    top3_neg = corrs.tail(3)

    return {
        "todas_las_correlaciones": {k: float(v) for k, v in corrs.items()},
        "top3_positivas": {k: float(v) for k, v in top3_pos.items()},
        "top3_negativas": {k: float(v) for k, v in top3_neg.items()},
        "variable_mas_correlacionada": corrs.index[0],
        "correlacion_top": float(corrs.iloc[0]),
        "resumen": (
            "Las 3 variables con correlacion mas fuerte y positiva son: {}. "
            "Las variables con correlacion mas negativa (o menos positiva) son: {}."
        ).format(
            ", ".join("{} (r={:.3f})".format(k, v) for k, v in top3_pos.items()),
            ", ".join("{} (r={:.3f})".format(k, v) for k, v in top3_neg.items()),
        ),
    }


def describe_shap_importance(importancias_dict):
    """
    Recibe {variable: importancia_shap} y genera un resumen ordenado
    con la magnitud relativa de cada variable, no solo el top 1.
    """
    if not importancias_dict:
        return {"resumen": "Sin datos de importancia SHAP disponibles.", "ranking_completo": [], "variable_principal": "N/D"}

    ordenado = sorted(importancias_dict.items(), key=lambda x: x[1], reverse=True)
    top = ordenado[0]
    total = sum(v for _, v in ordenado) or 1
    pct_top = top[1] / total * 100

    return {
        "ranking_completo": ordenado,
        "variable_principal": top[0],
        "importancia_principal": top[1],
        "pct_del_total": pct_top,
        "resumen": (
            "La variable con mayor importancia SHAP es {} con un valor de {:.4f}, "
            "representando aproximadamente el {:.0f}% de la importancia total sumada "
            "entre todas las variables. El ranking completo de mayor a menor es: {}."
        ).format(
            top[0], top[1], pct_top,
            ", ".join("{} ({:.4f})".format(k, v) for k, v in ordenado),
        ),
    }


def describe_model_comparison(ranking_list, rmse_arima):
    """
    Recibe la lista de {modelo, rmse} y calcula el ranking completo
    con la mejora de cada uno vs ARIMA, no solo el ganador.
    """
    if not ranking_list:
        return {"resumen": "Sin datos de comparativa disponibles."}

    filas = []
    for r in ranking_list:
        mejora = (rmse_arima - r["rmse"]) / rmse_arima * 100 if rmse_arima else 0
        filas.append({"modelo": r["modelo"], "rmse": r["rmse"], "mejora_vs_arima_pct": mejora})

    filas.sort(key=lambda x: x["rmse"])

    return {
        "ranking_con_mejoras": filas,
        "mejor_modelo": filas[0]["modelo"],
        "peor_modelo": filas[-1]["modelo"],
        "resumen": (
            "Ranking completo ordenado por RMSE (mejor a peor): {}. "
            "El modelo {} tuvo el mejor desempeño con una mejora del {:.1f}% "
            "frente a ARIMA, mientras que {} tuvo el peor desempeño relativo."
        ).format(
            ", ".join(
                "{} (RMSE={:,.0f}, mejora={:+.1f}%)".format(
                    f["modelo"], f["rmse"], f["mejora_vs_arima_pct"]
                ) for f in filas
            ),
            filas[0]["modelo"], filas[0]["mejora_vs_arima_pct"],
            filas[-1]["modelo"],
        ),
    }


def get_chart_info(chart_key):
    """Retorna la ficha tecnica de una grafica del registro central."""
    return CHART_REGISTRY.get(chart_key, {
        "que_es": "Grafica no registrada en el sistema de conocimiento.",
        "como_leerla": "Sin guia de lectura disponible.",
    })