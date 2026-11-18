"""
src/db/engine.py
Conexión a la base de datos.

- Desarrollo local: SQLite en data/importpredic.db (no requiere instalar nada).
- Producción: PostgreSQL (Supabase, Neon, Railway, etc.) definiendo
  DATABASE_URL en los secrets, p. ej.:
      postgresql+psycopg2://usuario:clave@host:5432/importpredic?sslmode=require
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.secrets import database_url
from src.db.models import Base

log = logging.getLogger(__name__)

_lock = threading.Lock()
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def _configure_sqlite(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")      # respeta ON DELETE CASCADE
        cur.execute("PRAGMA journal_mode=WAL")     # lecturas concurrentes
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


def get_engine(url: str | None = None) -> Engine:
    """Devuelve el engine global (lo crea y crea las tablas la primera vez)."""
    global _engine, _SessionFactory
    if _engine is not None and url is None:
        return _engine
    with _lock:
        if _engine is not None and url is None:
            return _engine
        url = url or database_url()
        is_sqlite = url.startswith("sqlite")
        kwargs = {"future": True, "pool_pre_ping": True}
        if is_sqlite:
            kwargs["connect_args"] = {"check_same_thread": False}
        engine = create_engine(url, **kwargs)
        if is_sqlite:
            _configure_sqlite(engine)
        Base.metadata.create_all(engine)
        _engine = engine
        _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        log.info("Base de datos lista (%s)", engine.dialect.name)
        return engine


def reset_engine(url: str) -> Engine:
    """Solo para pruebas: apunta el engine global a otra URL."""
    global _engine, _SessionFactory
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _SessionFactory = None
    return get_engine(url)


@contextmanager
def session_scope() -> Session:
    """Unidad de trabajo transaccional: commit al salir, rollback si hay error."""
    get_engine()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
