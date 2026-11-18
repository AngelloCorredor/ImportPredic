"""
src/interpretability/feature_importance.py
Análisis de interpretabilidad con SHAP: importancia global, individual
(waterfall) y generación de interpretación narrativa automática.
"""
import numpy as np
import pandas as pd
import shap


TREE_MODELS = {"XGBoost", "Gradient Boosting", "Random Forest"}
LINEAR_MODELS = {"Ridge", "Lasso"}


class FeatureImportanceAnalyzer:
    def __init__(self, model_wrapper, model_name: str, X_background: pd.DataFrame):
        self.model_wrapper = model_wrapper
        self.model_name = model_name
        self.X_background = X_background
        self.explainer = None
        self.shap_values = None

    def compute_shap_values(self, X_sample: pd.DataFrame):
        model = self.model_wrapper.model
        if self.model_name in TREE_MODELS:
            self.explainer = shap.TreeExplainer(model)
            self.shap_values = self.explainer.shap_values(X_sample)
        elif self.model_name in LINEAR_MODELS:
            self.explainer = shap.LinearExplainer(model, self.X_background)
            self.shap_values = self.explainer.shap_values(X_sample)
        else:
            raise ValueError(f"Modelo no soportado para SHAP: {self.model_name}")
        self.X_sample = X_sample
        return self.shap_values

    def get_global_importance(self) -> pd.DataFrame:
        mean_abs = np.abs(self.shap_values).mean(axis=0)
        df = pd.DataFrame({"variable": self.X_sample.columns, "mean_abs_shap": mean_abs})
        return df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    def get_temporal_importance(self, dates) -> pd.DataFrame:
        df = pd.DataFrame(self.shap_values, columns=self.X_sample.columns)
        df["fecha"] = pd.to_datetime(np.asarray(dates))
        return df

    def get_waterfall_data(self, index: int) -> dict:
        base_value = self.explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = base_value[0]
        contributions = self.shap_values[index]
        variables = self.X_sample.columns.tolist()
        order = np.argsort(-np.abs(contributions))
        return {
            "base_value": float(base_value),
            "variables": [variables[i] for i in order],
            "contributions": [float(contributions[i]) for i in order],
            "feature_values": [self.X_sample.iloc[index, i] for i in order],
        }

    def interpret_results(self, importance_df: pd.DataFrame, target_label: str = "kg/mes") -> str:
        top3 = importance_df.head(3)
        top_var = top3.iloc[0]["variable"]
        top_val = top3.iloc[0]["mean_abs_shap"]

        text = (
            f"El análisis de importancia de características revela que la variable con mayor "
            f"influencia sobre el volumen de importación fue **{top_var}**, con un impacto "
            f"promedio de {top_val:,.0f} {target_label}. "
        )
        if len(top3) > 1:
            others = ", ".join(f"**{v}**" for v in top3["variable"].iloc[1:])
            text += f"Le siguieron en importancia {others}."
        return text


def get_linear_coefficients_interpretation(coef_df: pd.DataFrame) -> str:
    top = coef_df.iloc[0]
    direction = "positiva" if top["coeficiente"] > 0 else "negativa"
    zero_coef = (coef_df["coeficiente"].abs() < 1e-6).sum()
    text = (
        f"La variable **{top['variable']}** tiene la relación más fuerte con el volumen "
        f"importado, con una asociación {direction}. "
    )
    if zero_coef > 0:
        text += f"El modelo descartó automáticamente {zero_coef} variable(s) por selección de características (coeficiente = 0)."
    return text
