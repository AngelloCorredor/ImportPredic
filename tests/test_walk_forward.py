import pytest

pytest.importorskip("xgboost")
pytest.importorskip("statsmodels")


def test_walk_forward_sobre_datos_de_demostracion():
    from config.settings import FEATURE_COLUMNS, TARGET_VARIABLE
    from src.data.preprocessor import DataPreprocessor
    from src.data.sample_generator import generate_sample_dataset
    from src.models.model_selector import walk_forward_validation

    df, _ = DataPreprocessor().run_full_pipeline(generate_sample_dataset(), ["8414.30"])
    feats = [c for c in FEATURE_COLUMNS if c in df.columns]
    wf = walk_forward_validation(df, feats, TARGET_VARIABLE, ["Ridge", "Lasso"], n_splits=3)
    assert set(wf["resumen"]["Modelo"]) == {"ARIMA", "Ridge", "Lasso"}
    assert len(wf["detalle"]) == 3 * 3
    assert wf["resumen"]["Pliegues ganados"].sum() == 3
