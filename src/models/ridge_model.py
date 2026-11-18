"""src/models/ridge_model.py — Wrapper de regresión Ridge (L2)."""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from src.models.base_model import BaseModel


class RidgeModel(BaseModel):
    name = "Ridge"

    def train(self, X_train, y_train, params: dict = None):
        params = params or dict(alpha=1.0, random_state=42)
        params.pop("random_state", None) if False else None
        self.model = Ridge(alpha=params.get("alpha", 1.0))
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)

    def get_coefficients(self, feature_names):
        coefs = self.model.coef_
        return pd.DataFrame({"variable": feature_names, "coeficiente": coefs}) \
            .assign(importancia=lambda d: d["coeficiente"].abs()) \
            .sort_values("importancia", ascending=False).reset_index(drop=True)
