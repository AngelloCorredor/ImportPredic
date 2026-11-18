"""
src/db/repository.py
Capa de acceso a datos. Todas las funciones reciben y devuelven tipos
simples (int, str, dict, DataFrame) para que las páginas de Streamlit
nunca manipulen objetos ORM directamente.

Regla de seguridad: TODA consulta sobre corridas filtra por `usuario_id`,
de modo que un usuario jamás puede leer, cargar o borrar la corrida de
otro aunque adivine su id.
"""
from __future__ import annotations

import io
import logging
import math
from datetime import datetime, timedelta

import joblib
import pandas as pd
from sqlalchemy import delete, func, select

from config.secrets import app_secret_key
from src.auth import security
from src.db.engine import session_scope
from src.db.models import (
    Artefacto, Auditoria, Corrida, MensajeIA, Pronostico, ResultadoModelo,
    UsoIA, Usuario, utcnow,
)

log = logging.getLogger(__name__)

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


class ArtefactoInvalido(Exception):
    """La firma HMAC de un artefacto no coincide: fue modificado fuera de la app."""


# ===========================================================================
# Utilidades
# ===========================================================================
def _clean_float(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _to_date(value):
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
        return None if pd.isna(ts) else ts.date()
    except (TypeError, ValueError):
        return None


def _usuario_dict(u: Usuario) -> dict:
    return {
        "id": u.id, "username": u.username, "nombre": u.nombre, "email": u.email,
        "rol": u.rol, "activo": u.activo, "creado_en": u.creado_en,
        "ultimo_acceso": u.ultimo_acceso,
    }


def serializar(obj) -> bytes:
    buf = io.BytesIO()
    joblib.dump(obj, buf, compress=3)
    return buf.getvalue()


def deserializar(data: bytes, firma: str):
    if not security.verify_signature(data, firma, app_secret_key()):
        raise ArtefactoInvalido("Firma inválida: el artefacto fue alterado o la APP_SECRET_KEY cambió.")
    return joblib.load(io.BytesIO(data))


# ===========================================================================
# Auditoría
# ===========================================================================
def auditar(accion: str, usuario_id: int | None = None, username: str | None = None,
            detalle: str | None = None) -> None:
    try:
        with session_scope() as s:
            s.add(Auditoria(usuario_id=usuario_id, username=username, accion=accion,
                            detalle=(detalle or "")[:500]))
    except Exception:  # la auditoría nunca debe tumbar la app
        log.exception("No se pudo registrar auditoría")


def listar_auditoria(limite: int = 200) -> pd.DataFrame:
    with session_scope() as s:
        rows = s.execute(
            select(Auditoria.creado_en, func.coalesce(Auditoria.username, Usuario.username),
                   Auditoria.accion, Auditoria.detalle)
            .outerjoin(Usuario, Usuario.id == Auditoria.usuario_id)
            .order_by(Auditoria.creado_en.desc()).limit(limite)
        ).all()
    return pd.DataFrame(rows, columns=["Fecha (UTC)", "Usuario", "Acción", "Detalle"])


# ===========================================================================
# Usuarios
# ===========================================================================
def contar_usuarios() -> int:
    with session_scope() as s:
        return s.scalar(select(func.count(Usuario.id))) or 0


def crear_usuario(username: str, nombre: str, password: str, email: str | None = None,
                  rol: str | None = None) -> dict:
    """Crea un usuario. El PRIMER usuario del sistema queda como administrador.
    Lanza ValueError con un mensaje legible si algo no es válido."""
    username = (username or "").strip().lower()
    nombre = (nombre or "").strip()
    err = security.validate_username(username)
    if err:
        raise ValueError(err)
    if not nombre or len(nombre) > 120:
        raise ValueError("Escribe tu nombre (máximo 120 caracteres).")
    problemas = security.validate_password_policy(password, username)
    if problemas:
        raise ValueError(" ".join(problemas))

    with session_scope() as s:
        if s.scalar(select(Usuario.id).where(Usuario.username == username)):
            raise ValueError("Ese nombre de usuario ya está en uso.")
        es_primero = (s.scalar(select(func.count(Usuario.id))) or 0) == 0
        u = Usuario(
            username=username, nombre=nombre, email=(email or "").strip() or None,
            password_hash=security.hash_password(password),
            rol=rol or ("admin" if es_primero else "usuario"),
        )
        s.add(u)
        s.flush()
        data = _usuario_dict(u)
    auditar("registro", data["id"], username, f"rol={data['rol']}")
    return data


def autenticar(username: str, password: str) -> tuple[dict | None, str]:
    """Verifica credenciales. Devuelve (usuario, "") o (None, mensaje_error).
    El mensaje es deliberadamente genérico para no revelar si el usuario existe."""
    username = (username or "").strip().lower()
    generico = "Usuario o contraseña incorrectos."
    with session_scope() as s:
        u = s.scalar(select(Usuario).where(Usuario.username == username))
        if u is None:
            security.burn_time(password)
            auditar("login_fallido", None, username[:50], "usuario inexistente")
            return None, generico
        ahora = utcnow()
        if u.bloqueado_hasta and u.bloqueado_hasta > ahora:
            minutos = max(1, int((u.bloqueado_hasta - ahora).total_seconds() // 60) + 1)
            return None, f"Cuenta bloqueada temporalmente por intentos fallidos. Intenta en {minutos} min."
        if not security.verify_password(password, u.password_hash):
            u.intentos_fallidos = (u.intentos_fallidos or 0) + 1
            detalle = f"intento {u.intentos_fallidos}"
            if u.intentos_fallidos >= MAX_INTENTOS:
                u.bloqueado_hasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
                u.intentos_fallidos = 0
                detalle += " -> bloqueo"
            uid = u.id
            s.commit()
            auditar("login_fallido", uid, username, detalle)
            return None, generico
        if not u.activo:
            return None, "Esta cuenta está desactivada. Contacta al administrador."
        u.intentos_fallidos = 0
        u.bloqueado_hasta = None
        u.ultimo_acceso = ahora
        data = _usuario_dict(u)
    auditar("login", data["id"], username)
    return data, ""


def obtener_usuario(usuario_id: int) -> dict | None:
    with session_scope() as s:
        u = s.get(Usuario, usuario_id)
        return _usuario_dict(u) if u else None


def cambiar_password(usuario_id: int, actual: str, nueva: str) -> None:
    with session_scope() as s:
        u = s.get(Usuario, usuario_id)
        if u is None or not security.verify_password(actual, u.password_hash):
            raise ValueError("La contraseña actual no es correcta.")
        problemas = security.validate_password_policy(nueva, u.username)
        if problemas:
            raise ValueError(" ".join(problemas))
        u.password_hash = security.hash_password(nueva)
        username = u.username
    auditar("cambio_password", usuario_id, username)


def listar_usuarios() -> pd.DataFrame:
    with session_scope() as s:
        n_corridas = (
            select(Corrida.usuario_id, func.count(Corrida.id).label("n"))
            .group_by(Corrida.usuario_id).subquery()
        )
        rows = s.execute(
            select(Usuario.id, Usuario.username, Usuario.nombre, Usuario.rol, Usuario.activo,
                   Usuario.creado_en, Usuario.ultimo_acceso, func.coalesce(n_corridas.c.n, 0))
            .outerjoin(n_corridas, n_corridas.c.usuario_id == Usuario.id)
            .order_by(Usuario.creado_en)
        ).all()
    return pd.DataFrame(rows, columns=["id", "Usuario", "Nombre", "Rol", "Activo",
                                       "Creado (UTC)", "Último acceso (UTC)", "Corridas"])


def actualizar_usuario(admin_id: int, usuario_id: int, *, rol: str | None = None,
                       activo: bool | None = None) -> None:
    if usuario_id == admin_id:
        raise ValueError("No puedes cambiar tu propio rol o estado.")
    with session_scope() as s:
        u = s.get(Usuario, usuario_id)
        if u is None:
            raise ValueError("Usuario no encontrado.")
        if rol in {"admin", "usuario"}:
            u.rol = rol
        if activo is not None:
            u.activo = bool(activo)
        username = u.username
    auditar("admin_actualiza_usuario", admin_id, None, f"{username}: rol={rol} activo={activo}")


# ===========================================================================
# Corridas
# ===========================================================================
def crear_corrida(usuario_id: int, nombre: str | None = None, origen: str | None = None) -> int:
    with session_scope() as s:
        c = Corrida(
            usuario_id=usuario_id,
            nombre=(nombre or f"Corrida {datetime.now():%Y-%m-%d %H:%M}")[:120],
            origen_datos=(origen or None) and origen[:255],
        )
        s.add(c)
        s.flush()
        cid = c.id
    auditar("crear_corrida", usuario_id, None, f"corrida={cid}")
    return cid


def _get_corrida(s, usuario_id: int, corrida_id: int) -> Corrida | None:
    return s.scalar(select(Corrida).where(Corrida.id == corrida_id, Corrida.usuario_id == usuario_id))


def guardar_estado_corrida(usuario_id: int, corrida_id: int, estado: dict) -> bool:
    """Persiste el estado de trabajo de una corrida:
    - metadatos y métricas -> columnas de `corridas`
    - tabla comparativa    -> `resultados_modelos`
    - pronósticos          -> `pronosticos`
    - todo lo demás        -> `artefactos` (solo si cambió desde la última vez)
    Devuelve False si la corrida no existe o no pertenece al usuario."""
    key = app_secret_key()
    with session_scope() as s:
        c = _get_corrida(s, usuario_id, corrida_id)
        if c is None:
            return False

        df = estado.get("dataset_processed")
        if df is not None:
            c.n_filas = int(len(df))
            if "fecha" in df.columns and len(df):
                c.fecha_inicio = _to_date(df["fecha"].min())
                c.fecha_fin = _to_date(df["fecha"].max())
        c.partidas = [str(p) for p in (estado.get("selected_partidas") or [])]
        c.metodo_validacion = estado.get("validation_method") or c.metodo_validacion

        best = estado.get("best_model_info")
        if best:
            m = best.get("metrics") or {}
            c.mejor_modelo = best.get("best_model_name")
            c.rmse = _clean_float(m.get("RMSE"))
            c.mae = _clean_float(m.get("MAE"))
            c.r2 = _clean_float(m.get("R2"))
            c.mape = _clean_float(m.get("MAPE"))
            c.mejora_vs_arima = _clean_float(m.get("% Mejora vs ARIMA (RMSE)"))
            c.hipotesis_confirmada = bool(best.get("hypothesis_confirmed"))
        else:
            c.mejor_modelo = c.rmse = c.mae = c.r2 = c.mape = c.mejora_vs_arima = None
            c.hipotesis_confirmada = None

        # --- Resultados por modelo (relacional) ---
        s.execute(delete(ResultadoModelo).where(ResultadoModelo.corrida_id == c.id))
        res = estado.get("comparison_results")
        if res is not None and len(res):
            best_name = best.get("best_model_name") if best else None
            for _, row in res.iterrows():
                s.add(ResultadoModelo(
                    corrida_id=c.id, modelo=str(row["Modelo"]),
                    mae=_clean_float(row.get("MAE")), rmse=_clean_float(row.get("RMSE")),
                    r2=_clean_float(row.get("R2")), mape=_clean_float(row.get("MAPE")),
                    mejora_vs_arima=_clean_float(row.get("% Mejora vs ARIMA (RMSE)")),
                    es_mejor=(row["Modelo"] == best_name),
                ))

        # --- Pronósticos (relacional) ---
        s.execute(delete(Pronostico).where(Pronostico.corrida_id == c.id))
        fut = estado.get("predictions_future")
        c.tiene_pronosticos = fut is not None and len(fut) > 0
        if c.tiene_pronosticos:
            for _, row in fut.iterrows():
                s.add(Pronostico(
                    corrida_id=c.id, fecha=_to_date(row["fecha"]),
                    prediccion=_clean_float(row["prediccion"]) or 0.0,
                    limite_inferior=_clean_float(row.get("limite_inferior")),
                    limite_superior=_clean_float(row.get("limite_superior")),
                ))

        # --- Artefactos binarios firmados (solo los que cambiaron) ---
        existentes = {a.clave: a for a in c.artefactos}
        for clave, valor in estado.items():
            if valor is None:
                if clave in existentes:
                    s.delete(existentes[clave])
                continue
            datos = serializar(valor)
            huella = security.sha256_hex(datos)
            art = existentes.get(clave)
            if art is not None and art.huella == huella:
                continue
            if art is None:
                art = Artefacto(corrida_id=c.id, clave=clave)
                s.add(art)
            art.contenido = datos
            art.huella = huella
            art.firma = security.sign_bytes(datos, key)
            art.tamano_bytes = len(datos)
            art.actualizado_en = utcnow()
        c.actualizado_en = utcnow()
    return True


def cargar_estado_corrida(usuario_id: int, corrida_id: int) -> dict | None:
    """Devuelve {clave: objeto} con todos los artefactos verificados, o None
    si la corrida no existe / no es del usuario. Artefactos con firma
    inválida se omiten y se registran en auditoría."""
    with session_scope() as s:
        c = _get_corrida(s, usuario_id, corrida_id)
        if c is None:
            return None
        crudos = [(a.clave, a.contenido, a.firma) for a in c.artefactos]
    estado, invalidos = {}, []
    for clave, contenido, firma in crudos:
        try:
            estado[clave] = deserializar(contenido, firma)
        except ArtefactoInvalido:
            invalidos.append(clave)
        except Exception:
            log.exception("No se pudo deserializar el artefacto %s", clave)
            invalidos.append(clave)
    if invalidos:
        auditar("artefacto_invalido", usuario_id, None,
                f"corrida={corrida_id} claves={','.join(invalidos)}")
    estado["_artefactos_invalidos"] = invalidos
    return estado


def listar_corridas(usuario_id: int) -> list[dict]:
    with session_scope() as s:
        tam = (
            select(Artefacto.corrida_id, func.sum(Artefacto.tamano_bytes).label("bytes"))
            .group_by(Artefacto.corrida_id).subquery()
        )
        rows = s.execute(
            select(Corrida, func.coalesce(tam.c.bytes, 0))
            .outerjoin(tam, tam.c.corrida_id == Corrida.id)
            .where(Corrida.usuario_id == usuario_id)
            .order_by(Corrida.actualizado_en.desc())
        ).all()
        out = []
        for c, size in rows:
            rango = None
            if c.fecha_inicio and c.fecha_fin:
                rango = f"{c.fecha_inicio:%Y-%m} a {c.fecha_fin:%Y-%m}"
            out.append({
                "id": c.id, "nombre": c.nombre, "creado_en": c.creado_en,
                "actualizado_en": c.actualizado_en, "n_filas": c.n_filas,
                "rango_fechas": rango, "partidas": list(c.partidas or []),
                "mejor_modelo": c.mejor_modelo, "rmse": c.rmse, "mae": c.mae, "r2": c.r2,
                "mape": c.mape, "mejora_vs_arima": c.mejora_vs_arima,
                "hipotesis_confirmada": c.hipotesis_confirmada,
                "tiene_pronosticos": c.tiene_pronosticos,
                "metodo_validacion": c.metodo_validacion,
                "tamano_bytes": int(size or 0), "origen_datos": c.origen_datos,
            })
        return out


def renombrar_corrida(usuario_id: int, corrida_id: int, nombre: str) -> bool:
    nombre = (nombre or "").strip()[:120]
    if not nombre:
        return False
    with session_scope() as s:
        c = _get_corrida(s, usuario_id, corrida_id)
        if c is None:
            return False
        c.nombre = nombre
    return True


def eliminar_corrida(usuario_id: int, corrida_id: int) -> bool:
    with session_scope() as s:
        c = _get_corrida(s, usuario_id, corrida_id)
        if c is None:
            return False
        s.delete(c)
    auditar("eliminar_corrida", usuario_id, None, f"corrida={corrida_id}")
    return True


def resultados_comparados(usuario_id: int, corrida_ids: list[int]) -> pd.DataFrame:
    """Tabla larga con las métricas de cada modelo en cada corrida seleccionada."""
    if not corrida_ids:
        return pd.DataFrame()
    with session_scope() as s:
        rows = s.execute(
            select(Corrida.id, Corrida.nombre, ResultadoModelo.modelo, ResultadoModelo.mae,
                   ResultadoModelo.rmse, ResultadoModelo.r2, ResultadoModelo.mape,
                   ResultadoModelo.mejora_vs_arima, ResultadoModelo.es_mejor)
            .join(ResultadoModelo, ResultadoModelo.corrida_id == Corrida.id)
            .where(Corrida.usuario_id == usuario_id, Corrida.id.in_(corrida_ids))
            .order_by(Corrida.id, ResultadoModelo.rmse)
        ).all()
    return pd.DataFrame(rows, columns=["corrida_id", "Corrida", "Modelo", "MAE", "RMSE", "R2",
                                       "MAPE", "% Mejora vs ARIMA", "Es el mejor"])


def pronosticos_comparados(usuario_id: int, corrida_ids: list[int]) -> pd.DataFrame:
    if not corrida_ids:
        return pd.DataFrame()
    with session_scope() as s:
        rows = s.execute(
            select(Corrida.id, Corrida.nombre, Pronostico.fecha, Pronostico.prediccion,
                   Pronostico.limite_inferior, Pronostico.limite_superior)
            .join(Pronostico, Pronostico.corrida_id == Corrida.id)
            .where(Corrida.usuario_id == usuario_id, Corrida.id.in_(corrida_ids))
            .order_by(Corrida.id, Pronostico.fecha)
        ).all()
    return pd.DataFrame(rows, columns=["corrida_id", "Corrida", "fecha", "prediccion",
                                       "limite_inferior", "limite_superior"])


# ===========================================================================
# Asistente de IA: historial de chat y límite de uso
# ===========================================================================
def registrar_uso_ia(usuario_id: int, pagina: str, tipo: str, modelo: str | None, exito: bool) -> None:
    try:
        with session_scope() as s:
            s.add(UsoIA(usuario_id=usuario_id, pagina=pagina[:40], tipo=tipo[:20],
                        modelo=(modelo or "")[:80] or None, exito=bool(exito)))
    except Exception:
        log.exception("No se pudo registrar uso de IA")


def uso_ia_ultima_hora(usuario_id: int) -> int:
    desde = utcnow() - timedelta(hours=1)
    with session_scope() as s:
        return s.scalar(
            select(func.count(UsoIA.id)).where(UsoIA.usuario_id == usuario_id, UsoIA.creado_en >= desde)
        ) or 0


def guardar_mensaje_ia(usuario_id: int, pagina: str, rol: str, contenido: str,
                       corrida_id: int | None = None) -> None:
    with session_scope() as s:
        if corrida_id is not None and _get_corrida(s, usuario_id, corrida_id) is None:
            corrida_id = None
        s.add(MensajeIA(usuario_id=usuario_id, corrida_id=corrida_id, pagina=pagina[:40],
                        rol=rol, contenido=contenido[:20000]))


def historial_ia(usuario_id: int, pagina: str, corrida_id: int | None = None,
                 limite: int = 40) -> list[dict]:
    with session_scope() as s:
        q = select(MensajeIA.rol, MensajeIA.contenido).where(
            MensajeIA.usuario_id == usuario_id, MensajeIA.pagina == pagina
        )
        q = q.where(MensajeIA.corrida_id.is_(None) if corrida_id is None
                    else MensajeIA.corrida_id == corrida_id)
        rows = s.execute(q.order_by(MensajeIA.id.desc()).limit(limite)).all()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def borrar_historial_ia(usuario_id: int, pagina: str, corrida_id: int | None = None) -> None:
    with session_scope() as s:
        q = delete(MensajeIA).where(MensajeIA.usuario_id == usuario_id, MensajeIA.pagina == pagina)
        q = q.where(MensajeIA.corrida_id.is_(None) if corrida_id is None
                    else MensajeIA.corrida_id == corrida_id)
        s.execute(q)


# ===========================================================================
# Panel de administración
# ===========================================================================
def estadisticas_generales() -> dict:
    desde = utcnow() - timedelta(days=1)
    with session_scope() as s:
        return {
            "usuarios": s.scalar(select(func.count(Usuario.id))) or 0,
            "corridas": s.scalar(select(func.count(Corrida.id))) or 0,
            "pronosticos": s.scalar(select(func.count(Pronostico.id))) or 0,
            "ia_24h": s.scalar(select(func.count(UsoIA.id)).where(UsoIA.creado_en >= desde)) or 0,
            "ia_fallos_24h": s.scalar(
                select(func.count(UsoIA.id)).where(UsoIA.creado_en >= desde, UsoIA.exito.is_(False))
            ) or 0,
            "almacenamiento_bytes": s.scalar(select(func.coalesce(func.sum(Artefacto.tamano_bytes), 0))) or 0,
        }


def uso_ia_por_dia(dias: int = 14) -> pd.DataFrame:
    desde = utcnow() - timedelta(days=dias)
    with session_scope() as s:
        rows = s.execute(
            select(UsoIA.creado_en, UsoIA.exito).where(UsoIA.creado_en >= desde)
        ).all()
    df = pd.DataFrame(rows, columns=["creado_en", "exito"])
    if df.empty:
        return df
    df["dia"] = pd.to_datetime(df["creado_en"]).dt.date
    return df.groupby("dia").agg(llamadas=("exito", "size"), exitosas=("exito", "sum")).reset_index()
