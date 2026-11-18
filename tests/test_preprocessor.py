import numpy as np
import pandas as pd

from src.data.preprocessor import DataPreprocessor


def test_scaler_se_ajusta_solo_con_entrenamiento():
    df = pd.DataFrame({
        "fecha": pd.date_range("2018-01-01", periods=60, freq="MS"),
        "trm_peso_dolar": np.linspace(2800, 5000, 60),  # el test tiene valores más altos
        "volumen_importacion_kg": np.arange(60.0),
    })
    pre = DataPreprocessor()
    scaled, _ = pre.scale_features(df, ["trm_peso_dolar"], fit_before_date="2022-01-01")
    train = scaled[df["fecha"] < "2022-01-01"]["trm_peso_dolar"]
    test = scaled[df["fecha"] >= "2022-01-01"]["trm_peso_dolar"]
    assert np.isclose(train.max(), 1.0) and np.isclose(train.min(), 0.0)
    assert test.max() > 1.0  # prueba de que el test NO participó en el ajuste
