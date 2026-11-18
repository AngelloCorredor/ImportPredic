"""src/models/lasso_model.py — Wrapper de regresión Lasso (L1)."""
import pandas as pd
from sklearn.linear_model import Lasso

from src.models.base_model import BaseModel


class LassoModel(BaseModel):
    name = "Lasso"

    def train(self, X_train, y_train, params: dict = None):
        params = params or dict(alpha=0.1)
        self.model = Lasso(alpha=params.get("alpha", 0.1), max_iter=10000)
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
