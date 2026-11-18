"""src/models/random_forest_model.py — Wrapper de Random Forest."""
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from src.models.base_model import BaseModel


class RandomForestModel(BaseModel):
    name = "Random Forest"

    def train(self, X_train, y_train, params: dict = None):
        params = params or dict(n_estimators=200, max_depth=10, min_samples_split=2,
                                 max_features="sqrt", random_state=42, n_jobs=2)
        self.model = RandomForestRegressor(**params)
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)

    def get_feature_importance(self, feature_names):
        importances = self.model.feature_importances_
        return pd.DataFrame({"variable": feature_names, "importancia": importances}) \
            .sort_values("importancia", ascending=False).reset_index(drop=True)
