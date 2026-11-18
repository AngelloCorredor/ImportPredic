"""
src/models/base_model.py
Clase abstracta base para todos los modelos de regresión del sistema.
"""
from abc import ABC, abstractmethod
import joblib


class BaseModel(ABC):
    name = "BaseModel"

    def __init__(self):
        self.model = None
        self.is_fitted = False

    @abstractmethod
    def train(self, X_train, y_train, params: dict = None):
        ...

    @abstractmethod
    def predict(self, X):
        ...

    def get_params(self) -> dict:
        return getattr(self.model, "get_params", lambda: {})()

    def save(self, filepath: str):
        joblib.dump(self.model, filepath)

    def load(self, filepath: str):
        self.model = joblib.load(filepath)
        self.is_fitted = True
        return self
