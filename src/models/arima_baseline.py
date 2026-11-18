"""src/models/arima_baseline.py — Modelo ARIMA de referencia para comparación."""
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")


class ARIMABaseline:
    name = "ARIMA"

    def __init__(self, order=(2, 1, 2)):
        self.order = order
        self.model_fit = None
        self.history = None

    def train(self, y_train: pd.Series):
        self.history = list(y_train.values)
        try:
            model = ARIMA(self.history, order=self.order)
            self.model_fit = model.fit()
        except Exception:
            # Fallback a orden más simple si no converge
            self.order = (1, 1, 1)
            model = ARIMA(self.history, order=self.order)
            self.model_fit = model.fit()
        return self

    def predict(self, n_periods: int):
        """Pronóstico walk-forward de n_periods pasos usando el historial de entrenamiento."""
        forecast = self.model_fit.forecast(steps=n_periods)
        return np.array(forecast)

    def predict_test(self, y_test: pd.Series):
        """Genera predicciones one-step-ahead sobre el set de prueba usando
        actualización walk-forward (re-fit incremental simplificado)."""
        history = list(self.history)
        preds = []
        for val in y_test.values:
            model = ARIMA(history, order=self.order)
            fit = model.fit()
            yhat = fit.forecast(steps=1)[0]
            preds.append(yhat)
            history.append(val)
        return np.array(preds)
