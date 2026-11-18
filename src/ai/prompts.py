# -*- coding: utf-8 -*-
"""
src/ai/prompts.py - VERSION 1.3.2 (completa y consistente con assistant.py)

Prompts del asistente IA por pagina. Lenguaje academico universitario colombiano.
Version reconstruida completa tras deteccion de AttributeError por funcion
faltante (prompt_evaluacion_residuos_detalle), para garantizar que TODAS
las funciones que assistant.py invoca existan en este archivo.

Reglas de redaccion aplicadas en SYSTEM_BASE:
  1. Idioma: siempre espanol, nunca ingles (reforzado tambien contra
     chain-of-thought en ingles).
  2. Anti chain-of-thought: prohibido mostrar razonamiento interno,
     tanto en espanol como en ingles.
  3. Respuesta directa: la primera palabra debe ser contenido util.
  4. Respuesta completa: nunca dejar ideas a medias.
"""

# ---------------------------------------------------------------------------
# SYSTEM PROMPT BASE
# ---------------------------------------------------------------------------
SYSTEM_BASE = (
    "INSTRUCCION CRITICA: Responde SIEMPRE en ESPANOL. NUNCA en ingles. "
    "NUNCA muestres tu proceso de pensamiento. "
    "NUNCA escribas frases como: 'Okay', 'Let me', 'I should', 'Need to', "
    "'Check if', 'I will', 'The user is asking', 'Let me recall', "
    "'I need to', 'Possible structure', 'Avoid phrases'. "
    "Responde DIRECTAMENTE con la respuesta final en espanol.\n\n"

    "REGLA ABSOLUTA NUMERO 1: TODO en espanol con tildes. CERO ingles, "
    "ni siquiera para razonar internamente.\n\n"

    "REGLA ABSOLUTA NUMERO 2: PROHIBIDO MOSTRAR TU RAZONAMIENTO INTERNO. "
    "Nunca escribas frases como: 'el usuario pregunta...', 'permítame recordar...', "
    "'bien, el usuario quiere...', 'el contexto dice...', 'debo verificar...', "
    "'espera...', 'revisando el contexto...', 'analizando...', 'recapitulando...', "
    "'voy a responder...', 'la pregunta es...', 'segun el contexto...' "
    "Estas frases revelan tu proceso interno y estan PROHIBIDAS.\n\n"

    "REGLA ABSOLUTA NUMERO 2B: LO MISMO APLICA EN INGLES. "
    "PROHIBIDO escribir: 'Okay, let's tackle this', 'the user is asking', "
    "'I need to', 'let me recall', 'first, I need to', 'wait, the context says', "
    "'given that', 'so, the target variable', 'let me check', 'I should', "
    "'the user wants', o cualquier razonamiento en ingles antes de responder. "
    "Si detectas que estas a punto de escribir una de estas frases en cualquier "
    "idioma, DETENTE y responde directamente en espanol sin ese texto previo.\n\n"

    "REGLA ABSOLUTA NUMERO 3: Primera palabra = contenido util. Sin introduccion.\n\n"

    "REGLA ABSOLUTA NUMERO 4: Maximo 320 palabras. Parrafos fluidos, sin listas "
    "con guion salvo que sean imprescindibles. Nunca dejes una respuesta a medias; "
    "si necesitas mas espacio, resume pero siempre llega a una conclusion.\n\n"

    "REGLA ABSOLUTA NUMERO 5 - PROHIBIDO INVENTAR DATOS, PERO SI EXPLICAR CONCEPTOS "
    "(LA MAS IMPORTANTE): Distingue SIEMPRE entre dos tipos de preguntas:\n"
    "  TIPO A (conceptual/explicativa): 'que representa el histograma', 'que es "
    "Durbin-Watson', 'como se interpreta un boxplot', 'que significa un p-valor', "
    "'para que sirve esta grafica'. Estas preguntas NO piden un dato especifico "
    "del sistema, piden que EXPLIQUES un concepto, una grafica o una metodologia "
    "en general. A estas SIEMPRE debes responder con una explicacion clara y "
    "completa usando tu conocimiento de estadistica y ciencia de datos, "
    "relacionandola con el contexto de ImportPredic cuando sea posible (ejemplo: "
    "explicar que el histograma muestra la distribucion de frecuencias del "
    "volumen de importacion, que permite ver si hay sesgo o concentracion de "
    "valores). NUNCA respondas 'no calculo ese dato' a una pregunta conceptual: "
    "esa respuesta es un ERROR cuando lo que piden es una explicacion, no un numero.\n"
    "  TIPO B (dato especifico): 'cual es el sesgo exacto', 'que p-valor dio "
    "Breusch-Pagan', 'cual fue el RMSE del tercer cuatrimestre'. Estas preguntas "
    "SI piden un numero, fecha o resultado concreto. Solo para este tipo de "
    "pregunta aplica la restriccion: si el dato EXACTO no esta en el contexto "
    "proporcionado en este mensaje, responde que el sistema no calcula ese dato "
    "especifico, sin inventar cifras, fechas, o nombres de pruebas no mencionadas "
    "en el contexto. Nunca fabriques un numero plausible que parezca real.\n"
    "En caso de duda entre ambos tipos, prioriza dar una explicacion util del "
    "concepto o la grafica en cuestion: es preferible explicar de mas que negarse "
    "a ayudar. Esta regla tiene PRIORIDAD sobre sonar completo o seguro: la "
    "precision sobre datos reales del sistema es innegociable, pero la "
    "explicacion de conceptos y graficas siempre debe darse.\n\n"

    "IDENTIDAD: Eres el asistente academico de ImportPredic, plataforma de "
    "prediccion del volumen de importacion de insumos criticos para "
    "refrigeradores en Colombia. Proyecto de grado de Angello Andre Corredor "
    "Rangel, Ingenieria de Sistemas, Universidad de Investigacion y Desarrollo "
    "(UDI), Barrancabermeja. Director: Marino Rodriguez Palacios.\n\n"

    "El sistema usa datos DIAN, DANE y Banco de la Republica con variables "
    "macroeconomicas (TRM, IPC, tasa de interes, IPI). Modelos: XGBoost, "
    "Gradient Boosting, Random Forest, Ridge, Lasso vs ARIMA.\n\n"

    "Insumos: compresores 8414.30, gases 2903.39, tarjetas 8537.10, plastico 3926.90.\n"
    "Hipotesis: el modelo ML superara al ARIMA en al menos 15% de reduccion en RMSE.\n\n"

    "ESTILO: lenguaje academico universitario colombiano, tercera persona."
)


def _m(user_text):
    return [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": user_text},
    ]


def _mh(user_text, historial, extra_ctx=""):
    sys = SYSTEM_BASE
    if extra_ctx:
        sys += "\n\nCONTEXTO ACTUAL: " + extra_ctx
    msgs = [{"role": "system", "content": sys}]
    msgs.extend(historial[-6:])
    msgs.append({"role": "user", "content": user_text})
    return msgs


# ---------------------------------------------------------------------------
# PAGINA 1 - INICIO
# ---------------------------------------------------------------------------
def prompt_inicio_bienvenida():
    return _m(
        "Genera un mensaje de bienvenida academico para ImportPredic con tres "
        "partes: 1) que es el sistema y su proposito academico, 2) que datos "
        "necesita el usuario para comenzar, 3) el flujo de trabajo en tres "
        "pasos simples. Directo, motivador y en espanol."
    )


def prompt_inicio_chat(pregunta, historial):
    return _mh(pregunta, historial)


# ---------------------------------------------------------------------------
# PAGINA 2 - CARGA DE DATOS
# ---------------------------------------------------------------------------
def prompt_carga_analisis(ctx):
    nulos = ctx.get("nulos_por_columna", {})
    nulos_txt = ", ".join(
        "{}: {} mes(es)".format(c, n) for c, n in nulos.items() if n > 0
    ) or "ninguno"
    estadisticas = ctx.get("estadisticas_objetivo", {})
    media = estadisticas.get("media", "N/D")
    std = estadisticas.get("std", "N/D")

    return _m(
        "Analiza la calidad de los datos cargados y presenta los hallazgos "
        "academicamente. Responde en espanol directamente sin introduccion previa.\n\n"
        "Registros originales: {orig} | Procesados: {proc} | Periodo: {per}\n"
        "Valores faltantes: {nulos} | Outliers winsorizados: {out}\n"
        "Variables: {vars}\n"
        "Volumen promedio: {med} kg/mes | Desviacion estandar: {std} kg/mes\n\n"
        "Concluye si la calidad es adecuada para entrenar el modelo predictivo "
        "y menciona precauciones metodologicas relevantes.".format(
            orig=ctx.get("filas_totales", "N/D"),
            proc=ctx.get("filas_procesadas", "N/D"),
            per=ctx.get("rango_fechas", "N/D"),
            nulos=nulos_txt,
            out=ctx.get("outliers_detectados", 0),
            vars=", ".join(ctx.get("variables_disponibles", [])) or "N/D",
            med="{:,.0f}".format(media) if isinstance(media, (int, float)) else media,
            std="{:,.0f}".format(std) if isinstance(std, (int, float)) else std,
        )
    )


def prompt_carga_chat(pregunta, ctx, historial):
    extra = (
        "{} registros, periodo {}, variables: {}. "
        "Graficas disponibles en esta pagina: histograma de distribucion del "
        "volumen de importacion, boxplot por año, y tabla de completitud de "
        "datos por columna. Si preguntan que representa o como se interpreta "
        "alguna de estas graficas, explica el concepto claramente (que muestra "
        "un histograma, que es un boxplot, etc.) y relacionalo con estos datos "
        "reales cuando sea posible.".format(
            ctx.get("filas_procesadas", "N/D"),
            ctx.get("rango_fechas", "N/D"),
            ", ".join(ctx.get("variables_disponibles", [])) or "N/D",
        )
    )
    return _mh(pregunta, historial, extra)


# ---------------------------------------------------------------------------
# PAGINA 3 - EXPLORACION
# ---------------------------------------------------------------------------
def prompt_eda_serie_tiempo(ctx):
    return _m(
        "Interpreta la serie de tiempo de importaciones (2015-2024). "
        "Responde directamente en espanol.\n\n"
        "Tendencia: {}\n"
        "Cambio total: {:.1f}%\n"
        "Mes mayor volumen: {}\n"
        "Mes menor volumen: {}\n"
        "Anio pico: {}\n"
        "Correlacion TRM: {:.3f}\n"
        "Correlacion IPC: {:.3f}\n\n"
        "Explica que revelan estos patrones, relaciona las correlaciones con "
        "la hipotesis del proyecto y justifica por que se deben incorporar "
        "variables exogenas al modelo.".format(
            ctx.get("tendencia", "N/D"),
            ctx.get("pct_cambio_total", 0),
            ctx.get("mes_mayor_promedio", "N/D"),
            ctx.get("mes_menor_promedio", "N/D"),
            ctx.get("anio_pico", "N/D"),
            ctx.get("correlacion_trm", 0),
            ctx.get("correlacion_ipc", 0),
        )
    )


def prompt_eda_correlaciones(ctx):
    cors = ctx.get("top_correlaciones", [])
    txt = " | ".join(
        "{} con {}: r={:.3f}".format(v.get("var1"), v.get("var2"), v.get("r", 0))
        for v in cors[:5]
    ) or "No disponibles"
    return _m(
        "Interpreta la matriz de correlaciones del dataset de ImportPredic. "
        "Responde directamente en espanol.\n\n"
        "Correlaciones relevantes: {}\n\n"
        "Explica cuales variables tienen mayor relacion con el volumen de "
        "importacion, si son coherentes con la teoria economica y que "
        "implican para los predictores del modelo.".format(txt)
    )


def prompt_eda_descomposicion(ctx):
    return _m(
        "Interpreta la descomposicion STL de la serie de importaciones. "
        "Responde directamente en espanol.\n\n"
        "Cambio en tendencia: {:.1f}% | Mes mayor estacionalidad: {} | Fuerza: {}\n\n"
        "Explica que significa cada componente (tendencia, estacionalidad, "
        "residuo) y relaciona la estacionalidad con los ciclos del sector "
        "de electrodomesticos colombiano.".format(
            ctx.get("cambio_tendencia_pct", 0),
            ctx.get("mes_mayor_estacional", "N/D"),
            ctx.get("fuerza_estacional", "media"),
        )
    )


def prompt_eda_outliers(ctx):
    return _m(
        "Analiza los valores atipicos de la serie de importaciones. "
        "Responde directamente en espanol.\n\n"
        "Outliers detectados: {} | Fechas: {}\n\n"
        "Explica posibles causas (pandemia 2020, crisis cambiaria 2022, "
        "disrupciones globales). Justifica por que se aplica winzorizacion "
        "en lugar de eliminacion.".format(
            ctx.get("n_outliers", 0),
            ctx.get("fechas_outliers", "No disponibles"),
        )
    )


def prompt_eda_chat(pregunta, ctx, historial):
    """
    Chat de Exploracion. Incluye tendencia, correlaciones TRM/IPC y el
    resumen completo de TODAS las correlaciones (no solo top1), para que
    el chat pueda responder o corregir preguntas sobre cualquier variable.
    """
    top_var = ctx.get("variable_mas_correlacionada", "N/D")
    top_r = ctx.get("correlacion_top", None)
    top_r_txt = "{:.3f}".format(top_r) if isinstance(top_r, (int, float)) else "N/D"
    resumen_todas = ctx.get("resumen_todas_correlaciones", "")

    extra = (
        "Tendencia: {} ({:+.1f}% en el periodo) | "
        "Mes de mayor volumen: {} | "
        "Correlacion con TRM: {:.3f} | Correlacion con IPC: {:.3f} | "
        "Variable mas correlacionada con el volumen de importacion: {} (r={}). "
        "{}\n"
        "Si el usuario pregunta o afirma algo sobre correlaciones de "
        "CUALQUIER variable (no solo TRM o IPC), usa el listado completo "
        "de arriba para responder o corregir la afirmacion con el valor "
        "real exacto.".format(
            ctx.get("tendencia", "N/D"),
            ctx.get("pct_cambio_total", 0),
            ctx.get("mes_mayor_promedio", "N/D"),
            ctx.get("correlacion_trm", 0),
            ctx.get("correlacion_ipc", 0),
            top_var,
            top_r_txt,
            resumen_todas,
        )
    )
    return _mh(pregunta, historial, extra)


# ---------------------------------------------------------------------------
# PAGINA 4 - ENTRENAMIENTO
# ---------------------------------------------------------------------------
def prompt_entrenamiento_resultado(ctx):
    ranking = ctx.get("ranking", [])
    rank_txt = " | ".join(
        "{}.{}: RMSE={:,.0f}".format(i + 1, r.get("modelo"), r.get("rmse", 0))
        for i, r in enumerate(ranking)
    ) or "No disponible"
    confirmada = ctx.get("hipotesis_confirmada", False)

    return _m(
        "Presenta los resultados del entrenamiento de modelos ImportPredic. "
        "Lenguaje academico directo en espanol.\n\n"
        "Ranking: {}\n"
        "Mejor modelo: {} | RMSE: {:,.0f} kg/mes | MAE: {:,.0f} | "
        "R2: {:.4f} | MAPE: {:.2f}%\n"
        "ARIMA referencia: {:,.0f} kg/mes | Mejora: {:.1f}%\n"
        "Hipotesis: {}\n\n"
        "Explica por que el modelo ganador logro el mejor desempeno, que "
        "implica la mejora para el abastecimiento y la conclusion sobre la "
        "hipotesis del proyecto de grado.".format(
            rank_txt,
            ctx.get("mejor_modelo", "N/D"),
            ctx.get("rmse_mejor", 0),
            ctx.get("mae_mejor", 0),
            ctx.get("r2_mejor", 0),
            ctx.get("mape_mejor", 0),
            ctx.get("rmse_arima", 0),
            ctx.get("mejora_rmse_pct", 0),
            "CONFIRMADA: mejora supera el 15%" if confirmada else "NO CONFIRMADA: mejora insuficiente",
        )
    )


def prompt_entrenamiento_residuos(ctx):
    """
    Version enriquecida: usa el resumen completo generado por
    describe_residuos_vs_tiempo() en chart_knowledge.py, que incluye
    tendencia detectada, heterocedasticidad, fecha del peor residuo,
    y cantidad de outliers. Esto permite que la IA describa lo que
    REALMENTE se observa en el grafico, no teoria generica de residuos.
    """
    resumen_datos = ctx.get("resumen_residuos", "")
    durbin_watson = ctx.get("durbin_watson", 2.0)

    contexto_extra = (
        "Datos reales calculados sobre el grafico de residuos vs tiempo del "
        "modelo {}:\n{}\nEstadistico Durbin-Watson: {:.2f} "
        "(cercano a 2 indica ausencia de autocorrelacion; menor a 1.5 sugiere "
        "autocorrelacion positiva; mayor a 2.5 sugiere autocorrelacion negativa)."
    ).format(ctx.get("modelo", "N/D"), resumen_datos, durbin_watson)

    return _m(
        "Interpreta el grafico de RESIDUOS VS TIEMPO del modelo {} en "
        "ImportPredic, basandote UNICAMENTE en los datos reales proporcionados "
        "a continuacion, no en teoria generica. Responde directamente en "
        "espanol, en un solo parrafo fluido y completo (no lo dejes a medias).\n\n"
        "{}\n\n"
        "Explica: 1) si hay o no una tendencia sistematica visible en los "
        "residuos y que implica para el modelo, 2) si la dispersion de los "
        "errores es estable o cambia con el tiempo (heterocedasticidad), "
        "3) en que fecha ocurrio el error mas grande y una posible "
        "explicacion economica, 4) que dice el Durbin-Watson sobre la "
        "independencia de los errores, y 5) una conclusion sobre si el "
        "modelo es confiable para generar pronosticos.".format(
            ctx.get("modelo", "N/D"),
            contexto_extra,
        )
    )


def prompt_entrenamiento_chat(pregunta, ctx, historial):
    extra = (
        "Mejor modelo: {}, RMSE {:,.0f} kg, mejora {:.1f}% vs ARIMA, "
        "hipotesis {}.".format(
            ctx.get("mejor_modelo", "N/D"),
            ctx.get("rmse_mejor", 0),
            ctx.get("mejora_rmse_pct", 0),
            "confirmada" if ctx.get("hipotesis_confirmada") else "no confirmada",
        )
    )
    return _mh(pregunta, historial, extra)


# ---------------------------------------------------------------------------
# PAGINA 5 - PREDICCION
# ---------------------------------------------------------------------------
def prompt_prediccion_resultado(ctx):
    var = ctx.get("variacion_vs_anio_anterior_pct", 0)
    return _m(
        "Interpreta el pronostico de {} para {} meses en ImportPredic. "
        "Responde directamente en espanol.\n\n"
        "Volumen proyectado: {:,.0f} kg | Mes mayor: {} | Mes menor: {}\n"
        "Variacion vs anio anterior: {:+.1f}% | Incertidumbre banda 95%: "
        "{:.1f}% | Escenario: {}\n\n"
        "Explica las implicaciones para la planificacion del abastecimiento "
        "y menciona en que meses se deben anticipar los pedidos de "
        "importacion.".format(
            ctx.get("modelo_usado", "N/D"),
            ctx.get("horizonte_meses", 12),
            ctx.get("total_proyectado_kg", 0),
            ctx.get("mes_mayor_pronostico", "N/D"),
            ctx.get("mes_menor_pronostico", "N/D"),
            var,
            ctx.get("incertidumbre_promedio_pct", 0),
            ctx.get("escenario", "base"),
        )
    )


def prompt_prediccion_banda_confianza(ctx):
    return _m(
        "Explica la banda de confianza del pronostico en ImportPredic. "
        "Responde directamente en espanol.\n\n"
        "RMSE modelo: {:,.0f} kg | Ancho promedio banda: {:,.0f} kg | "
        "Mes mayor incertidumbre: {}\n\n"
        "Explica que significa la banda del 95%, que factores la amplian y "
        "como debe usarse para decisiones prudentes de abastecimiento.".format(
            ctx.get("rmse_modelo", 0),
            ctx.get("ancho_promedio_banda", 0),
            ctx.get("mes_mayor_incertidumbre", "N/D"),
        )
    )


def prompt_prediccion_chat(pregunta, ctx, historial):
    extra = (
        "Pronostico: modelo {}, {} meses, {:,.0f} kg proyectados.".format(
            ctx.get("modelo_usado", "N/D"),
            ctx.get("horizonte_meses", 12),
            ctx.get("total_proyectado_kg", 0),
        )
    )
    return _mh(pregunta, historial, extra)


# ---------------------------------------------------------------------------
# PAGINA 6 - EVALUACION
# ---------------------------------------------------------------------------
def prompt_evaluacion_metricas(ctx):
    dm_p = ctx.get("p_valor_dm", 1.0)
    confirmada = ctx.get("hipotesis_confirmada", False)

    return _m(
        "Interpreta metricas y pruebas estadisticas del modelo {} en "
        "ImportPredic.\n\n"
        "MODELO: MAE={:,.0f} | RMSE={:,.0f} | R2={:.4f} | MAPE={:.2f}%\n"
        "ARIMA: MAE={:,.0f} | RMSE={:,.0f} | Mejora: {:.1f}%\n"
        "Diebold-Mariano: p={:.4f} -> {}\n"
        "{}: p={:.4f}\n"
        "Hipotesis: {}\n\n"
        "Explica cada metrica, por que MAE y RMSE son complementarios, como "
        "se interpreta Diebold-Mariano y la conclusion definitiva sobre la "
        "hipotesis. Responde directamente en espanol.".format(
            ctx.get("modelo", "N/D"),
            ctx.get("mae", 0), ctx.get("rmse", 0),
            ctx.get("r2", 0), ctx.get("mape", 0),
            ctx.get("mae_arima", 0), ctx.get("rmse_arima", 0),
            ctx.get("mejora_rmse_pct", 0),
            dm_p,
            "rechaza H0: ML superior" if dm_p < 0.05 else "no rechaza H0",
            ctx.get("prueba_normalidad", "Shapiro-Wilk"),
            ctx.get("p_valor_normalidad", 0),
            "SE CONFIRMA con respaldo estadistico" if confirmada else "NO SE CONFIRMA",
        )
    )


def prompt_evaluacion_estabilidad(ctx):
    desglose = ctx.get("desglose_completo_cuatrimestres", "")
    return _m(
        "Analiza la estabilidad temporal del modelo en ImportPredic. "
        "Responde directamente en espanol, usando UNICAMENTE los datos "
        "reales proporcionados.\n\n"
        "Degradacion RMSE: {:.1f}% | RMSE inicial: {:,.0f} kg | RMSE final: {:,.0f} kg\n"
        "Desglose completo por cuatrimestre: {}\n\n"
        "Explica el concepto de concept drift, si el modelo mantiene su "
        "capacidad predictiva citando los valores reales del desglose, y "
        "que acciones se recomiendan para preservar el desempeno en "
        "produccion. Si te preguntan por un cuatrimestre que no aparece "
        "en el desglose, indica que no dispones de ese dato especifico.".format(
            ctx.get("degradacion_pct", 0),
            ctx.get("rmse_inicial", 0),
            ctx.get("rmse_final", 0),
            desglose or "no disponible",
        )
    )


def prompt_evaluacion_residuos_detalle(ctx):
    """
    Funcion que faltaba y causaba el AttributeError.
    Version enriquecida usando el resumen de chart_knowledge.describe_residuos_vs_tiempo(),
    igual que en Entrenamiento: describe lo que realmente se ve en el
    grafico (tendencia, heterocedasticidad, fecha del peor error), no
    teoria generica de residuos.
    """
    resumen_datos = ctx.get("resumen_residuos", "")
    return _m(
        "Interpreta el grafico de residuos y su histograma para el modelo "
        "{} en ImportPredic, basandote UNICAMENTE en los datos reales "
        "proporcionados. Responde en espanol, en un parrafo completo.\n\n"
        "Datos reales: {}\n"
        "Durbin-Watson: {:.2f}\n\n"
        "Explica si hay patron sistematico en los residuos, si la "
        "distribucion parece simetrica o sesgada, y que implica esto para "
        "la confiabilidad de las predicciones del modelo en produccion.".format(
            ctx.get("modelo", "N/D"),
            resumen_datos,
            ctx.get("durbin_watson", 2.0),
        )
    )


def prompt_evaluacion_chat(pregunta, ctx, historial):
    extra = (
        "Evaluacion: {}, RMSE {:,.0f}, mejora {:.1f}%, hipotesis {}. "
        "Residuos: {} Durbin-Watson: {:.2f}, asimetria: {:.2f}. "
        "RMSE por cuatrimestre: {}. "
        "Pruebas estadisticas disponibles en el sistema: {}".format(
            ctx.get("modelo", "N/D"),
            ctx.get("rmse", 0),
            ctx.get("mejora_rmse_pct", 0),
            "confirmada" if ctx.get("hipotesis_confirmada") else "no confirmada",
            ctx.get("resumen_residuos", ""),
            ctx.get("durbin_watson", 0),
            ctx.get("asimetria_residuos", 0),
            ctx.get("desglose_cuatrimestres", "no disponible"),
            ctx.get("pruebas_disponibles_en_sistema", ""),
        )
    )
    return _mh(pregunta, historial, extra)


# ---------------------------------------------------------------------------
# PAGINA 7 - INTERPRETABILIDAD
# ---------------------------------------------------------------------------
def prompt_interpretabilidad_shap(ctx):
    top = ctx.get("top_variables", [])
    top_txt = " | ".join(
        "{}.{}: {:.4f}".format(i + 1, v.get("variable"), v.get("importancia", 0))
        for i, v in enumerate(top[:5])
    ) or "No disponibles"
    resumen_shap = ctx.get("resumen_shap", "")

    return _m(
        "Interpreta el analisis de importancia SHAP del modelo {} en "
        "ImportPredic. Responde directamente en espanol, en un parrafo "
        "completo (no lo dejes a medias).\n\n"
        "Top 5 variables: {}\n"
        "Variable principal: {} (relacion {} con el volumen)\n"
        "{}\n\n"
        "Explica el significado de SHAP values. Para las top 3 variables "
        "describe como afectan el volumen de importacion y si son "
        "coherentes con la teoria economica. Menciona implicaciones para "
        "la toma de decisiones de abastecimiento.".format(
            ctx.get("modelo", "N/D"),
            top_txt,
            ctx.get("variable_principal", "N/D"),
            ctx.get("direccion_principal", "positiva"),
            resumen_shap,
        )
    )


def prompt_interpretabilidad_waterfall(ctx):
    return _m(
        "Explica el grafico de cascada SHAP para la observacion de {} en "
        "ImportPredic. Responde directamente en espanol.\n\n"
        "Prediccion final: {:,.0f} kg | Valor base: {:,.0f} kg\n"
        "Variables que aumentaron: {} | Variables que redujeron: {}\n\n"
        "Explica que significa esta descomposicion y como ayuda a validar "
        "que el modelo captura relaciones economicamente coherentes.".format(
            ctx.get("fecha_observacion", "N/D"),
            ctx.get("prediccion_final", 0),
            ctx.get("valor_base", 0),
            ctx.get("variables_positivas", "N/D"),
            ctx.get("variables_negativas", "N/D"),
        )
    )


def prompt_interpretabilidad_shap_summary(ctx):
    """
    Nueva funcion para la grafica SHAP Summary Plot, que antes no tenia
    ningun prompt ni render_ai_insight conectado (causaba respuestas
    vacias o inventadas cuando el usuario preguntaba sobre ella).
    """
    return _m(
        "Interpreta el SHAP Summary Plot de la variable {} para el modelo "
        "{} en ImportPredic. Responde directamente en espanol, basandote "
        "UNICAMENTE en los datos reales proporcionados.\n\n"
        "Correlacion entre el valor de la variable y su SHAP value: {:.3f}\n"
        "Relacion detectada: {}\n"
        "Rango de SHAP values observado: {:.2f} a {:.2f}\n"
        "Numero de observaciones graficadas: {}\n\n"
        "Explica que significa esta correlacion en terminos practicos: "
        "como varia el impacto en la prediccion segun el valor de la "
        "variable, y que implica esto para la interpretacion economica "
        "del modelo.".format(
            ctx.get("variable_analizada", "N/D"),
            ctx.get("modelo", "N/D"),
            ctx.get("correlacion_valor_shap", 0),
            ctx.get("direccion_relacion", "N/D"),
            ctx.get("shap_min", 0),
            ctx.get("shap_max", 0),
            ctx.get("n_observaciones", 0),
        )
    )


def prompt_interpretabilidad_coeficientes(ctx):
    return _m(
        "Interpreta los coeficientes del modelo {} en ImportPredic. "
        "Responde directamente en espanol.\n\n"
        "Coeficientes: {}\n\n"
        "Explica que significa cada coeficiente economicamente. Si Lasso "
        "elimino variables (coef=0), explica que implica para la "
        "seleccion de predictores.".format(
            ctx.get("modelo", "N/D"),
            ctx.get("coeficientes_texto", "No disponibles"),
        )
    )


def prompt_interpretabilidad_chat(pregunta, ctx, historial):
    top = ctx.get("top_variables", [])
    ranking_txt = " | ".join(
        "{}: {:.4f}".format(v.get("variable"), v.get("importancia", 0)) for v in top[:5]
    )
    extra = (
        "SHAP de {}. Variable principal: {}. Ranking completo: {}. "
        "Graficas disponibles en este modulo: importancia global SHAP, "
        "SHAP summary plot de la variable principal, waterfall de una "
        "observacion individual, y coeficientes si el modelo es lineal "
        "(Ridge/Lasso). No hay graficas de dependencia (dependence plots) "
        "ni interaccion entre variables en este modulo.".format(
            ctx.get("modelo", "N/D"),
            ctx.get("variable_principal", "N/D"),
            ranking_txt or "no disponible",
        )
    )
    return _mh(pregunta, historial, extra)


# ---------------------------------------------------------------------------
# PAGINA 8 - REPORTE
# ---------------------------------------------------------------------------
def prompt_reporte_resumen(ctx):
    confirmada = ctx.get("hipotesis_confirmada", False)
    return _m(
        "Genera el resumen ejecutivo de ImportPredic con cinco secciones: "
        "problema y objetivo, metodologia, resultados, conclusion hipotesis, "
        "recomendaciones. Maximo 420 palabras. Espanol academico formal.\n\n"
        "Datos: periodo={}, registros={:,}, mejor modelo={}, RMSE={:,.0f} "
        "kg/mes, mejora={:.1f}%, variable principal={}, hipotesis={}.".format(
            ctx.get("periodo", "enero 2015 - diciembre 2024"),
            ctx.get("total_registros", 0),
            ctx.get("mejor_modelo", "N/D"),
            ctx.get("rmse_mejor", 0),
            ctx.get("mejora_pct", 0),
            ctx.get("variable_principal", "N/D"),
            "CONFIRMADA" if confirmada else "NO CONFIRMADA",
        )
    )


def prompt_reporte_chat(pregunta, ctx, historial):
    return _mh(pregunta, historial)