"""
src/evaluation/statistical_tests.py
Pruebas estadísticas para verificar la hipótesis del proyecto: que el
modelo de Machine Learning supera significativamente al modelo ARIMA.
"""
import numpy as np
from scipy import stats


def diebold_mariano_test(e1, e2, h: int = 1, power: int = 2) -> dict:
    """
    e1: errores del modelo de referencia (ARIMA)
    e2: errores del modelo ML propuesto
    H0: los dos modelos tienen el mismo poder predictivo.
    H1: el modelo ML es superior.
    """
    e1 = np.asarray(e1, dtype=float)
    e2 = np.asarray(e2, dtype=float)
    n = len(e1)
    if n < 3:
        return {"dm_stat": np.nan, "p_value": np.nan, "conclusion": "Muestra insuficiente para la prueba."}

    d = np.abs(e1) ** power - np.abs(e2) ** power
    d_mean = np.mean(d)
    gamma0 = np.var(d, ddof=0)

    # Corrección Newey-West simplificada para h>1
    gamma_sum = 0.0
    for k in range(1, h):
        if k < n:
            cov = np.cov(d[:-k], d[k:])[0, 1] if n - k > 1 else 0
            gamma_sum += 2 * cov
    var_d = (gamma0 + gamma_sum) / n
    if var_d <= 0:
        var_d = gamma0 / n if gamma0 > 0 else 1e-10

    dm_stat = d_mean / np.sqrt(var_d)
    p_value = 2 * (1 - stats.norm.cdf(np.abs(dm_stat)))

    if p_value < 0.05 and dm_stat > 0:
        conclusion = "El modelo ML es significativamente superior al ARIMA (p < 0.05)."
    elif p_value < 0.05 and dm_stat < 0:
        conclusion = "El modelo ARIMA es significativamente superior al modelo ML (p < 0.05)."
    else:
        conclusion = "No hay diferencia estadísticamente significativa entre los modelos (p ≥ 0.05)."

    return {"dm_stat": round(float(dm_stat), 4), "p_value": round(float(p_value), 4), "conclusion": conclusion}


def shapiro_wilk_test(residuals) -> dict:
    residuals = np.asarray(residuals, dtype=float)
    if len(residuals) < 3:
        return {"statistic": np.nan, "p_value": np.nan, "conclusion": "Muestra insuficiente."}
    stat, p_value = stats.shapiro(residuals)
    conclusion = ("Los residuos siguen una distribución normal (p > 0.05)."
                  if p_value > 0.05 else
                  "Los residuos NO siguen una distribución normal (p ≤ 0.05); usar prueba no paramétrica.")
    return {"statistic": round(float(stat), 4), "p_value": round(float(p_value), 4), "conclusion": conclusion}


def wilcoxon_signed_rank_test(errors_baseline, errors_model) -> dict:
    errors_baseline = np.abs(np.asarray(errors_baseline, dtype=float))
    errors_model = np.abs(np.asarray(errors_model, dtype=float))
    try:
        stat, p_value = stats.wilcoxon(errors_baseline, errors_model)
    except ValueError:
        return {"statistic": np.nan, "p_value": np.nan, "conclusion": "No fue posible calcular (diferencias nulas)."}
    conclusion = ("El modelo ML tiene errores sistemáticamente menores que ARIMA (p < 0.05)."
                  if p_value < 0.05 else
                  "No hay diferencia significativa entre los errores de ambos modelos (p ≥ 0.05).")
    return {"statistic": round(float(stat), 4), "p_value": round(float(p_value), 4), "conclusion": conclusion}


def student_t_test_paired(errors_baseline, errors_model) -> dict:
    errors_baseline = np.abs(np.asarray(errors_baseline, dtype=float))
    errors_model = np.abs(np.asarray(errors_model, dtype=float))
    stat, p_value = stats.ttest_rel(errors_baseline, errors_model)
    diff = errors_baseline - errors_model
    ci = stats.t.interval(0.95, len(diff) - 1, loc=np.mean(diff), scale=stats.sem(diff)) if len(diff) > 1 else (np.nan, np.nan)
    conclusion = ("El modelo ML tiene error medio significativamente menor que ARIMA (p < 0.05)."
                  if p_value < 0.05 and stat > 0 else
                  "No hay diferencia significativa entre los errores medios (p ≥ 0.05).")
    return {
        "t_statistic": round(float(stat), 4), "p_value": round(float(p_value), 4),
        "ci_95": (round(float(ci[0]), 2), round(float(ci[1]), 2)), "conclusion": conclusion,
    }


def run_complete_hypothesis_test(y_true, y_pred_baseline, y_pred_model) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    e_baseline = y_true - np.asarray(y_pred_baseline, dtype=float)
    e_model = y_true - np.asarray(y_pred_model, dtype=float)

    shapiro = shapiro_wilk_test(e_model)
    normal = shapiro["p_value"] > 0.05 if not np.isnan(shapiro["p_value"]) else False

    if normal:
        parametric_test = student_t_test_paired(e_baseline, e_model)
        test_used = "t-test pareado"
    else:
        parametric_test = wilcoxon_signed_rank_test(e_baseline, e_model)
        test_used = "Wilcoxon (rangos con signo)"

    dm = diebold_mariano_test(e_baseline, e_model)

    hypothesis_confirmed = (dm["p_value"] < 0.05 and dm["dm_stat"] > 0) and (parametric_test["p_value"] < 0.05)

    final_conclusion = (
        "✓ La hipótesis se CONFIRMA: el modelo de Machine Learning ofrece una precisión "
        "predictiva significativamente superior al modelo estadístico de referencia (ARIMA), (p < 0.05)."
        if hypothesis_confirmed else
        "✗ La hipótesis NO se confirma con evidencia estadística suficiente al nivel α = 0.05."
    )

    return {
        "shapiro_wilk": shapiro,
        "test_used": test_used,
        "parametric_test": parametric_test,
        "diebold_mariano": dm,
        "hypothesis_confirmed": hypothesis_confirmed,
        "final_conclusion": final_conclusion,
    }
