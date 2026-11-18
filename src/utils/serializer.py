"""src/utils/serializer.py — Empaquetado del modelo entrenado para descarga.

v2.0: el modelo ya no se escribe en una carpeta global `models_saved/`
(que se sobrescribía con el último entrenamiento de CUALQUIER usuario).
Cada modelo vive dentro de la corrida de su dueño en la base de datos, y
desde la página de Entrenamiento se puede descargar como un único
archivo .joblib con el modelo, el escalador y sus metadatos.
"""
import io
from datetime import datetime

import joblib


def build_model_bundle_bytes(model_wrapper, scaler, feature_cols, metrics, model_name) -> bytes:
    bundle = {
        "model": getattr(model_wrapper, "model", model_wrapper),
        "scaler": scaler,
        "metadata": {
            "model_name": model_name,
            "feature_columns": list(feature_cols),
            "metrics": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in dict(metrics).items()},
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "uso": "bundle = joblib.load(ruta); X = bundle['scaler'].transform(df[cols]); "
                   "bundle['model'].predict(X)",
        },
    }
    buf = io.BytesIO()
    joblib.dump(bundle, buf, compress=3)
    return buf.getvalue()


def load_model_bundle_bytes(data: bytes):
    """Solo para archivos generados por esta misma app (joblib usa pickle:
    nunca cargues un .joblib de origen desconocido)."""
    bundle = joblib.load(io.BytesIO(data))
    return bundle["model"], bundle["scaler"], bundle["metadata"]
