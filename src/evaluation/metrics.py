"""
src/evaluation/metrics.py
Cálculo de métricas de evaluación de modelos de predicción.
"""
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def calculate_mae(y_true, y_pred) -> float:
    return float(mean_absolute_error(y_true, y_pred))


def calculate_rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def calculate_r2(y_true, y_pred) -> float:
    return float(r2_score(y_true, y_pred))


def calculate_mape(y_true, y_pred) -> float:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def calculate_all_metrics(y_true, y_pred, model_name: str = "") -> dict:
    mae = calculate_mae(y_true, y_pred)
    rmse = calculate_rmse(y_true, y_pred)
    r2 = calculate_r2(y_true, y_pred)
    mape = calculate_mape(y_true, y_pred)

    interpretations = {
        "MAE": f"El modelo {model_name} se equivoca en promedio {mae:,.0f} kg/mes.",
        "RMSE": f"El error cuadrático medio del modelo {model_name} es {rmse:,.0f} kg/mes.",
        "R2": f"El modelo {model_name} explica el {r2*100:.1f}% de la variabilidad del volumen importado."
              + (" (Advertencia: posible sobreajuste)" if r2 > 0.99 else ""),
        "MAPE": f"El error porcentual promedio del modelo {model_name} es {mape:.2f}%.",
    }

    return {
        "values": {"MAE": round(mae, 2), "RMSE": round(rmse, 2), "R2": round(r2, 4), "MAPE": round(mape, 2)},
        "interpretations": interpretations,
    }


def calculate_improvement_vs_baseline(baseline_metrics: dict, model_metrics: dict) -> dict:
    improvement = {}
    for key in ["MAE", "RMSE", "MAPE"]:
        base_val = baseline_metrics.get(key, np.nan)
        model_val = model_metrics.get(key, np.nan)
        if base_val:
            improvement[key] = round((base_val - model_val) / base_val * 100, 2)
    r2_base = baseline_metrics.get("R2", np.nan)
    r2_model = model_metrics.get("R2", np.nan)
    improvement["R2"] = round(r2_model - r2_base, 4)
    return improvement


def calculate_residuals_analysis(y_true, y_pred) -> dict:
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    residuals = y_true - y_pred

    from scipy.stats import skew, kurtosis
    dw_stat = float(np.sum(np.diff(residuals) ** 2) / np.sum(residuals ** 2)) if np.sum(residuals ** 2) > 0 else np.nan

    return {
        "residuals": residuals,
        "media": float(np.mean(residuals)),
        "std": float(np.std(residuals)),
        "skewness": float(skew(residuals)),
        "kurtosis": float(kurtosis(residuals)),
        "durbin_watson": dw_stat,
    }
