import numpy as np
import pandas as pd
import pytest


def _estado():
    df = pd.DataFrame({"fecha": pd.date_range("2020-01-01", periods=24, freq="MS"),
                       "volumen_importacion_kg": np.arange(24.0)})
    res = pd.DataFrame([
        {"Modelo": "Ridge", "MAE": 1, "RMSE": 2, "R2": .9, "MAPE": 3, "% Mejora vs ARIMA (RMSE)": 33.3},
        {"Modelo": "ARIMA", "MAE": 2, "RMSE": 3, "R2": .8, "MAPE": 4, "% Mejora vs ARIMA (RMSE)": 0.0},
    ])
    fut = pd.DataFrame({"fecha": pd.date_range("2022-01-01", periods=3, freq="MS"),
                        "prediccion": [1.0, 2, 3], "limite_inferior": [0.0, 1, 2],
                        "limite_superior": [2.0, 3, 4]})
    return {"dataset_processed": df, "selected_partidas": ["8414.30"], "comparison_results": res,
            "predictions_future": fut,
            "best_model_info": {"best_model_name": "Ridge", "metrics": res.iloc[0].to_dict(),
                                "hypothesis_confirmed": True}}


def test_primer_usuario_es_admin(db):
    assert db.crear_usuario("ana", "Ana", "Clave1234")["rol"] == "admin"
    assert db.crear_usuario("beto", "Beto", "Clave1234")["rol"] == "usuario"
    with pytest.raises(ValueError):
        db.crear_usuario("ANA", "Otra", "Clave1234")  # duplicado (sin distinguir mayúsculas)


def test_login_y_bloqueo(db):
    db.crear_usuario("ana", "Ana", "Clave1234")
    assert db.autenticar("ana", "Clave1234")[0]["username"] == "ana"
    assert db.autenticar("nadie", "x")[0] is None
    for _ in range(db.MAX_INTENTOS):
        db.autenticar("ana", "mala")
    user, msg = db.autenticar("ana", "Clave1234")
    assert user is None and "bloqueada" in msg


def test_corrida_guardar_y_cargar(db):
    u = db.crear_usuario("ana", "Ana", "Clave1234")
    cid = db.crear_corrida(u["id"], "Prueba")
    assert db.guardar_estado_corrida(u["id"], cid, _estado())
    corrida = db.listar_corridas(u["id"])[0]
    assert corrida["mejor_modelo"] == "Ridge" and corrida["tiene_pronosticos"]
    assert corrida["rango_fechas"] == "2020-01 a 2021-12"
    estado = db.cargar_estado_corrida(u["id"], cid)
    assert estado["dataset_processed"].shape == (24, 2)
    assert len(db.resultados_comparados(u["id"], [cid])) == 2
    assert len(db.pronosticos_comparados(u["id"], [cid])) == 3


def test_aislamiento_entre_usuarios(db):
    a = db.crear_usuario("ana", "Ana", "Clave1234")
    b = db.crear_usuario("beto", "Beto", "Clave1234")
    cid = db.crear_corrida(a["id"], "De Ana")
    db.guardar_estado_corrida(a["id"], cid, _estado())
    assert db.listar_corridas(b["id"]) == []
    assert db.cargar_estado_corrida(b["id"], cid) is None
    assert db.guardar_estado_corrida(b["id"], cid, _estado()) is False
    assert db.eliminar_corrida(b["id"], cid) is False
    assert db.resultados_comparados(b["id"], [cid]).empty


def test_artefacto_alterado_se_rechaza(db):
    from sqlalchemy import update
    from src.db.engine import session_scope
    from src.db.models import Artefacto

    u = db.crear_usuario("ana", "Ana", "Clave1234")
    cid = db.crear_corrida(u["id"])
    db.guardar_estado_corrida(u["id"], cid, {"dataset_processed": pd.DataFrame({"a": [1]}), "x": [1, 2]})
    with session_scope() as s:
        s.execute(update(Artefacto).where(Artefacto.clave == "x").values(contenido=b"malicioso"))
    estado = db.cargar_estado_corrida(u["id"], cid)
    assert "x" not in estado and estado["_artefactos_invalidos"] == ["x"]


def test_borrado_en_cascada(db):
    from sqlalchemy import func, select
    from src.db.engine import session_scope
    from src.db.models import Artefacto, Pronostico, ResultadoModelo

    u = db.crear_usuario("ana", "Ana", "Clave1234")
    cid = db.crear_corrida(u["id"])
    db.guardar_estado_corrida(u["id"], cid, _estado())
    assert db.eliminar_corrida(u["id"], cid)
    with session_scope() as s:
        for tabla in (Artefacto, Pronostico, ResultadoModelo):
            assert s.scalar(select(func.count()).select_from(tabla)) == 0


def test_historial_y_cuota_ia(db):
    u = db.crear_usuario("ana", "Ana", "Clave1234")
    db.guardar_mensaje_ia(u["id"], "carga", "user", "hola")
    db.guardar_mensaje_ia(u["id"], "carga", "assistant", "¡hola!")
    assert [m["role"] for m in db.historial_ia(u["id"], "carga")] == ["user", "assistant"]
    db.borrar_historial_ia(u["id"], "carga")
    assert db.historial_ia(u["id"], "carga") == []
    for _ in range(3):
        db.registrar_uso_ia(u["id"], "carga", "chat", "m", True)
    assert db.uso_ia_ultima_hora(u["id"]) == 3
