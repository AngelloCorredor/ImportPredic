"""
src/models/model_selector.py
Coordina el entrenamiento y comparación automática de los 5 algoritmos
candidatos frente al modelo ARIMA de referencia.
"""
import pandas as pd

from src.models.xgboost_model import XGBoostModel
from src.models.gradient_boosting_model import GradientBoostingModel
from src.models.random_forest_model import RandomForestModel
from src.models.ridge_model import RidgeModel
from src.models.lasso_model import LassoModel
from src.models.arima_baseline import ARIMABaseline
from src.evaluation.metrics import calculate_all_metrics
from config.settings import UMBRAL_MEJORA_RMSE

MODEL_REGISTRY = {
    "XGBoost": XGBoostModel,
    "Gradient Boosting": GradientBoostingModel,
    "Random Forest": RandomForestModel,
    "Ridge": RidgeModel,
    "Lasso": LassoModel,
}


class ModelSelector:
    def __init__(self):
        self.trained_models = {}
        self.results = None
        self.predictions = {}
        self.arima_model = None

    def compare_all_models(self, X_train, X_test, y_train, y_test, selected_models=None,
                            params_by_model=None, progress_callback=None):
        selected_models = selected_models or list(MODEL_REGISTRY.keys())
        params_by_model = params_by_model or {}
        rows = []

        total_steps = len(selected_models) + 1
        step = 0

        # --- ARIMA baseline ---
        arima = ARIMABaseline()
        arima.train(y_train)
        y_pred_arima = arima.predict_test(y_test)
        self.arima_model = arima
        self.predictions["ARIMA"] = y_pred_arima
        metrics_arima = calculate_all_metrics(y_test.values, y_pred_arima, "ARIMA")
        rows.append({"Modelo": "ARIMA", **metrics_arima["values"]})
        step += 1
        if progress_callback:
            progress_callback(step, total_steps, "ARIMA")

        # --- ML candidates ---
        for name in selected_models:
            cls = MODEL_REGISTRY[name]
            model = cls()
            model.train(X_train, y_train, params_by_model.get(name))
            y_pred = model.predict(X_test)
            self.trained_models[name] = model
            self.predictions[name] = y_pred
            metrics = calculate_all_metrics(y_test.values, y_pred, name)
            rows.append({"Modelo": name, **metrics["values"]})
            step += 1
            if progress_callback:
                progress_callback(step, total_steps, name)

        df = pd.DataFrame(rows)
        rmse_arima = df.loc[df["Modelo"] == "ARIMA", "RMSE"].values[0]
        df["% Mejora vs ARIMA (RMSE)"] = ((rmse_arima - df["RMSE"]) / rmse_arima * 100).round(2)
        df.loc[df["Modelo"] == "ARIMA", "% Mejora vs ARIMA (RMSE)"] = 0.0
        df = df.sort_values("RMSE").reset_index(drop=True)

        self.results = df
        return df

    def select_best_model(self):
        if self.results is None:
            raise ValueError("Ejecute compare_all_models() primero.")
        ml_only = self.results[self.results["Modelo"] != "ARIMA"]
        best_row = ml_only.sort_values("RMSE").iloc[0]
        best_name = best_row["Modelo"]
        hypothesis_confirmed = best_row["% Mejora vs ARIMA (RMSE)"] >= UMBRAL_MEJORA_RMSE * 100
        return {
            "best_model_name": best_name,
            "best_model": self.trained_models[best_name],
            "metrics": best_row.to_dict(),
            "hypothesis_confirmed": bool(hypothesis_confirmed),
        }


# ---------------------------------------------------------------------------
# VALIDACIÓN WALK-FORWARD (origen móvil)
# ---------------------------------------------------------------------------
def walk_forward_validation(df, feature_cols, target, selected_models=None, n_splits=5,
                            test_size=None, progress_callback=None):
    """Validación walk-forward con ventana expansiva.

    Antes, la opción "Walk-forward (5 splits)" de la interfaz se mostraba
    pero el código la ignoraba y siempre hacía hold-out. Ahora:

      Pliegue k:  entrena con [inicio, t_k)  ->  evalúa en [t_k, t_k + h)

    En cada pliegue se re-ajusta el escalado SOLO con su tramo de
    entrenamiento (sin fuga de información) y se re-entrenan ARIMA y los
    modelos de ML. Devuelve:
      - detalle: DataFrame (pliegue, modelo, MAE, RMSE, R2, MAPE)
      - resumen: DataFrame por modelo con RMSE medio, desviación,
                 % de mejora media vs ARIMA y nº de pliegues ganados.
    """
    import numpy as np
    from sklearn.preprocessing import MinMaxScaler

    selected_models = selected_models or list(MODEL_REGISTRY.keys())
    data = df.sort_values("fecha").reset_index(drop=True)
    n = len(data)
    h = test_size or max(3, min(12, n // (n_splits + 1)))
    first_test = n - n_splits * h
    if first_test < 24:
        raise ValueError(
            f"Muy pocos datos para {n_splits} pliegues de {h} meses (se necesitan al menos "
            f"24 meses de entrenamiento en el primer pliegue)."
        )

    rows = []
    total = n_splits * (len(selected_models) + 1)
    step = 0
    for k in range(n_splits):
        start = first_test + k * h
        train, test = data.iloc[:start], data.iloc[start:start + h]
        scaler = MinMaxScaler().fit(train[feature_cols])
        X_tr = pd.DataFrame(scaler.transform(train[feature_cols]), columns=feature_cols)
        X_te = pd.DataFrame(scaler.transform(test[feature_cols]), columns=feature_cols)
        y_tr, y_te = train[target].reset_index(drop=True), test[target].reset_index(drop=True)
        periodo = f"{test['fecha'].min():%Y-%m} a {test['fecha'].max():%Y-%m}"

        arima = ARIMABaseline().train(y_tr)
        m = calculate_all_metrics(y_te.values, arima.predict_test(y_te), "ARIMA")["values"]
        rows.append({"Pliegue": k + 1, "Periodo de prueba": periodo, "Modelo": "ARIMA", **m})
        step += 1
        if progress_callback:
            progress_callback(step, total, f"ARIMA (pliegue {k + 1})")

        for name in selected_models:
            model = MODEL_REGISTRY[name]()
            model.train(X_tr, y_tr)
            m = calculate_all_metrics(y_te.values, model.predict(X_te), name)["values"]
            rows.append({"Pliegue": k + 1, "Periodo de prueba": periodo, "Modelo": name, **m})
            step += 1
            if progress_callback:
                progress_callback(step, total, f"{name} (pliegue {k + 1})")

    detalle = pd.DataFrame(rows)
    arima_rmse = detalle[detalle["Modelo"] == "ARIMA"].set_index("Pliegue")["RMSE"]
    detalle["% Mejora vs ARIMA (RMSE)"] = detalle.apply(
        lambda r: round((arima_rmse[r["Pliegue"]] - r["RMSE"]) / arima_rmse[r["Pliegue"]] * 100, 2)
        if arima_rmse[r["Pliegue"]] else np.nan, axis=1,
    )
    ganador = detalle[detalle["Modelo"] != "ARIMA"].loc[
        lambda d: d.groupby("Pliegue")["RMSE"].idxmin()
    ]["Modelo"].value_counts()

    resumen = detalle.groupby("Modelo").agg(
        RMSE_medio=("RMSE", "mean"), RMSE_desv=("RMSE", "std"),
        MAE_medio=("MAE", "mean"), MAPE_medio=("MAPE", "mean"),
        Mejora_media_pct=("% Mejora vs ARIMA (RMSE)", "mean"),
    ).reset_index()
    resumen["Pliegues ganados"] = resumen["Modelo"].map(ganador).fillna(0).astype(int)
    resumen.loc[resumen["Modelo"] == "ARIMA", "Pliegues ganados"] = 0
    resumen = resumen.sort_values("RMSE_medio").reset_index(drop=True).round(2)
    return {"detalle": detalle, "resumen": resumen, "n_splits": n_splits, "horizonte": h}
