"""
config/settings.py
Configuraciones globales del sistema ImportPredic: rutas, variables del modelo,
insumos críticos, período de análisis, modelos candidatos e hiperparámetros.
"""
import os

# ---------------------------------------------------------------------------
# RUTAS
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_PATH = os.path.join(BASE_DIR, "data", "raw")
DATA_PROCESSED_PATH = os.path.join(BASE_DIR, "data", "processed")
MODELS_SAVED_PATH = os.path.join(BASE_DIR, "models_saved")
SAMPLE_DATA_PATH = os.path.join(BASE_DIR, "data", "samples", "sample_data.csv")
DATA_HISTORY_PATH = os.path.join(BASE_DIR, "data", "history")

# ---------------------------------------------------------------------------
# VARIABLES DEL MODELO
# ---------------------------------------------------------------------------
TARGET_VARIABLE = "volumen_importacion_kg"

FEATURE_COLUMNS = [
    "trm_peso_dolar",
    "ipc_variacion_mensual",
    "tasa_interes_referencia",
    "ipi_manufacturero",
    "valor_fob_usd",
    "mes",
    "anio",
    "lag_1",
    "lag_3",
    "lag_12",
    "rolling_mean_3",
    "rolling_std_6",
]

# ---------------------------------------------------------------------------
# INSUMOS CRÍTICOS Y SUS PARTIDAS ARANCELARIAS
# ---------------------------------------------------------------------------
INSUMOS_CRITICOS = {
    "8414.30": "Compresores herméticos para refrigeración",
    "2903.39": "Gases refrigerantes (HFC-134a y mezclas)",
    "8537.10": "Tarjetas electrónicas de control y circuitos impresos",
    "3926.90": "Perfiles y piezas de plástico técnico",
}

# ---------------------------------------------------------------------------
# PERÍODO DE ANÁLISIS
# ---------------------------------------------------------------------------
FECHA_INICIO = "2015-01-01"
FECHA_FIN = "2024-12-31"
TRAIN_TEST_SPLIT_DATE = "2023-01-01"

# ---------------------------------------------------------------------------
# MODELOS CANDIDATOS
# ---------------------------------------------------------------------------
MODELOS_CANDIDATOS = ["XGBoost", "Gradient Boosting", "Random Forest", "Ridge", "Lasso"]
MODELO_REFERENCIA = "ARIMA"

MODEL_COLORS = {
    "XGBoost": "#6C63FF",
    "Gradient Boosting": "#FF6B81",
    "Random Forest": "#2ECC8F",
    "Ridge": "#FFB648",
    "Lasso": "#8B5CF6",
    "ARIMA": "#94A3B8",
}

# ---------------------------------------------------------------------------
# MÉTRICAS DE EVALUACIÓN
# ---------------------------------------------------------------------------
METRICAS = ["MAE", "RMSE", "R2", "MAPE"]
UMBRAL_MEJORA_RMSE = 0.15  # 15% de mejora mínima esperada vs modelo referencia

# ---------------------------------------------------------------------------
# HIPERPARÁMETROS — GRID SEARCH
# ---------------------------------------------------------------------------
PARAM_GRIDS = {
    "XGBoost": {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.01, 0.05, 0.1],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
        "reg_alpha": [0, 0.1],
        "reg_lambda": [1, 1.5],
    },
    "Gradient Boosting": {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.01, 0.05, 0.1],
        "subsample": [0.8, 1.0],
    },
    "Random Forest": {
        "n_estimators": [100, 200, 300],
        "max_depth": [5, 10, None],
        "min_samples_split": [2, 5],
        "max_features": ["sqrt", "log2"],
    },
    "Ridge": {"alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
    "Lasso": {"alpha": [0.001, 0.01, 0.1, 1.0, 10.0]},
}

# Grids reducidos para ejecución rápida dentro de la interfaz (demo académica)
PARAM_GRIDS_FAST = {
    "XGBoost": {"n_estimators": [100, 200], "max_depth": [3, 5], "learning_rate": [0.05, 0.1]},
    "Gradient Boosting": {"n_estimators": [100, 200], "max_depth": [3, 5], "learning_rate": [0.05, 0.1]},
    "Random Forest": {"n_estimators": [100, 200], "max_depth": [5, 10], "min_samples_split": [2, 5]},
    "Ridge": {"alpha": [0.1, 1.0, 10.0, 100.0]},
    "Lasso": {"alpha": [0.01, 0.1, 1.0, 10.0]},
}

# ---------------------------------------------------------------------------
# HORIZONTE DE PREDICCIÓN
# ---------------------------------------------------------------------------
HORIZONTE_PREDICCION_MESES = 12

# ---------------------------------------------------------------------------
# CONTEXTO ACADÉMICO
# ---------------------------------------------------------------------------
ACADEMIC_INFO = {
    "universidad": "Universidad de Investigación y Desarrollo (UDI) — Barrancabermeja",
    "programa": "Ingeniería de Sistemas",
    "linea_investigacion": "Sistemas de Información (Grupo Gidsaw)",
    "director": "Marino Rodríguez Palacios",
    "autor": "Angello André Corredor Rangel",
    "periodo_analisis": "Enero 2015 — Diciembre 2024",
    "objetivo": "Reducir en al menos 15% el RMSE frente al modelo ARIMA de referencia",
    "hipotesis": "El modelo de Machine Learning supera al modelo estadístico tradicional (ARIMA) en precisión predictiva",
}
