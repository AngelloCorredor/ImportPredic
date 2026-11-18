"""src/models/gradient_boosting_model.py — Wrapper de Gradient Boosting."""
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from src.models.base_model import BaseModel


class GradientBoostingModel(BaseModel):
    name = "Gradient Boosting"

    def train(self, X_train, y_train, params: dict = None):
        params = params or dict(n_estimators=200, max_depth=3, learning_rate=0.05,
                                 subsample=0.9, random_state=42)
        self.model = GradientBoostingRegressor(**params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)

    def get_feature_importance(self, feature_names):
        importances = self.model.feature_importances_
        return pd.DataFrame({"variable": feature_names, "importancia": importances}) \
            .sort_values("importancia", ascending=False).reset_index(drop=True)
