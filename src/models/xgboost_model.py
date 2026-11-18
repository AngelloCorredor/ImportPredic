"""src/models/xgboost_model.py — Wrapper de XGBoost con importancia de variables y SHAP."""
import pandas as pd
from xgboost import XGBRegressor

from src.models.base_model import BaseModel


class XGBoostModel(BaseModel):
    name = "XGBoost"

    def __init__(self):
        super().__init__()

    def train(self, X_train, y_train, params: dict = None):
        params = params or dict(n_estimators=200, max_depth=5, learning_rate=0.05,
                                 subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=2)
        self.model = XGBRegressor(**params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)

    def get_feature_importance(self, feature_names):
        importances = self.model.feature_importances_
        return pd.DataFrame({"variable": feature_names, "importancia": importances}) \
            .sort_values("importancia", ascending=False).reset_index(drop=True)
