"""
src/data/preprocessor.py
Pipeline de preprocesamiento: agregación, imputación, ingeniería de
variables temporales (lags, rolling stats), escalado y partición temporal.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from config.settings import TARGET_VARIABLE, FEATURE_COLUMNS


class DataPreprocessor:
    def __init__(self, target_variable: str = TARGET_VARIABLE):
        self.target_variable = target_variable
        self.scaler = None

    # ------------------------------------------------------------------
    def filter_by_partida(self, df: pd.DataFrame, partidas: list) -> pd.DataFrame:
        if "partida_arancelaria" in df.columns and partidas:
            return df[df["partida_arancelaria"].isin(partidas)].copy()
        return df.copy()

    # ------------------------------------------------------------------
    def aggregate_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Agrega todas las partidas seleccionadas por mes (suma de kg y FOB,
        promedio de las variables macroeconómicas)."""
        df = df.copy()
        df["fecha"] = pd.to_datetime(df["fecha"])
        agg = df.groupby("fecha").agg({
            "volumen_importacion_kg": "sum",
            "valor_fob_usd": "sum",
            "trm_peso_dolar": "mean",
            "ipc_variacion_mensual": "mean",
            "tasa_interes_referencia": "mean",
            "ipi_manufacturero": "mean",
        }).reset_index().sort_values("fecha")
        return agg

    # ------------------------------------------------------------------
    def handle_missing_values(self, df: pd.DataFrame) -> tuple:
        df = df.copy().sort_values("fecha")
        na_before = df.isnull().sum().to_dict()

        # Interpolación lineal para huecos cortos
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit=2)
        # Forward/backward fill para lo que quede (variables macro)
        df[numeric_cols] = df[numeric_cols].ffill().bfill()

        na_after = df.isnull().sum().to_dict()
        report = {"na_before": na_before, "na_after": na_after}
        return df, report

    # ------------------------------------------------------------------
    def remove_outliers(self, df: pd.DataFrame, column: str = None, threshold: float = 3.0) -> tuple:
        """Winsoriza outliers de la variable objetivo al percentil 1-99 (no elimina filas)."""
        column = column or self.target_variable
        df = df.copy()
        low, high = df[column].quantile([0.01, 0.99])
        n_outliers = int(((df[column] < low) | (df[column] > high)).sum())
        df[column] = df[column].clip(lower=low, upper=high)
        return df, n_outliers

    # ------------------------------------------------------------------
    def create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy().sort_values("fecha").reset_index(drop=True)
        df["mes"] = df["fecha"].dt.month
        df["anio"] = df["fecha"].dt.year
        df["trimestre"] = df["fecha"].dt.quarter

        target = self.target_variable
        df["lag_1"] = df[target].shift(1)
        df["lag_3"] = df[target].shift(3)
        df["lag_6"] = df[target].shift(6)
        df["lag_12"] = df[target].shift(12)

        df["rolling_mean_3"] = df[target].shift(1).rolling(3).mean()
        df["rolling_mean_6"] = df[target].shift(1).rolling(6).mean()
        df["rolling_mean_12"] = df[target].shift(1).rolling(12).mean()
        df["rolling_std_6"] = df[target].shift(1).rolling(6).std()

        df["diff_1"] = df[target].diff(1)
        df["diff_12"] = df[target].diff(12)

        # Rellenar los primeros lags/rolling con backfill (para no perder filas en demo)
        lag_cols = ["lag_1", "lag_3", "lag_6", "lag_12", "rolling_mean_3",
                    "rolling_mean_6", "rolling_mean_12", "rolling_std_6", "diff_1", "diff_12"]
        df[lag_cols] = df[lag_cols].bfill().fillna(0)

        return df

    # ------------------------------------------------------------------
    def scale_features(self, df: pd.DataFrame, feature_cols: list = None, method: str = "minmax",
                       fit_before_date=None):
        """Escala las variables predictoras.

        FIX v2.0 (fuga de información): si se indica `fit_before_date`, el
        scaler se AJUSTA solo con las filas anteriores a esa fecha (el
        conjunto de entrenamiento) y luego se aplica a todo el dataset.
        Antes se ajustaba con el dataset completo, de modo que los mínimos
        y máximos del periodo de prueba "se filtraban" al entrenamiento y
        las métricas sobre test quedaban levemente optimistas.
        """
        feature_cols = feature_cols or FEATURE_COLUMNS
        feature_cols = [c for c in feature_cols if c in df.columns]
        self.scaler = MinMaxScaler() if method == "minmax" else StandardScaler()
        df_scaled = df.copy()
        if fit_before_date is not None:
            mask = pd.to_datetime(df["fecha"]) < pd.to_datetime(fit_before_date)
            if mask.sum() == 0:
                raise ValueError("No hay filas anteriores a la fecha de corte para ajustar el escalado.")
            self.scaler.fit(df.loc[mask, feature_cols])
        else:
            self.scaler.fit(df[feature_cols])
        df_scaled[feature_cols] = self.scaler.transform(df[feature_cols])
        return df_scaled, self.scaler

    # ------------------------------------------------------------------
    def split_temporal(self, df: pd.DataFrame, test_start_date: str, feature_cols: list = None):
        feature_cols = feature_cols or FEATURE_COLUMNS
        feature_cols = [c for c in feature_cols if c in df.columns]
        df = df.sort_values("fecha")
        test_start = pd.to_datetime(test_start_date)

        train = df[df["fecha"] < test_start]
        test = df[df["fecha"] >= test_start]

        X_train, y_train = train[feature_cols], train[self.target_variable]
        X_test, y_test = test[feature_cols], test[self.target_variable]

        return X_train, X_test, y_train, y_test, train["fecha"], test["fecha"]

    # ------------------------------------------------------------------
    def run_full_pipeline(self, df_raw: pd.DataFrame, partidas: list = None):
        """Ejecuta el pipeline completo y retorna el dataset final + reporte."""
        original_rows = len(df_raw)

        df = self.filter_by_partida(df_raw, partidas) if partidas else df_raw.copy()
        df = self.aggregate_monthly(df)
        df, na_report = self.handle_missing_values(df)
        df, n_outliers = self.remove_outliers(df)
        df = self.create_temporal_features(df)

        report = {
            "filas_originales": original_rows,
            "filas_procesadas": len(df),
            "outliers_detectados": n_outliers,
            "rango_fechas": (df["fecha"].min(), df["fecha"].max()),
            "na_report": na_report,
            "media_objetivo": float(df[self.target_variable].mean()),
            "std_objetivo": float(df[self.target_variable].std()),
        }
        return df, report
