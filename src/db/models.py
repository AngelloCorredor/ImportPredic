"""
src/db/models.py
Modelo relacional de ImportPredic (SQLAlchemy 2.0, estilo declarativo).

Diagrama entidad-relación (resumen):

    usuarios 1───* corridas 1───* resultados_modelos
        │              │ 1───* pronosticos
        │              │ 1───* artefactos
        │              └─0..*  mensajes_ia
        │ 1───* mensajes_ia
        │ 1───* uso_ia
        └ 1───* auditoria

- Las métricas, resultados por modelo y pronósticos se guardan en
  tablas normales (consultables con SQL, comparables entre corridas).
- Los objetos de Python que no tienen representación tabular (modelos
  entrenados, scaler, DataFrames intermedios) se guardan en
  `artefactos` como binario serializado + firma HMAC-SHA256, que se
  verifica antes de deserializar (evita ejecutar código inyectado si
  alguien manipula la base de datos).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer,
    LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="usuario")  # usuario | admin
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    corridas: Mapped[list["Corrida"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )


class Corrida(Base):
    """Una 'corrida' = un dataset procesado y todo lo que se derive de él
    (entrenamiento, pronósticos, evaluación, interpretabilidad)."""

    __tablename__ = "corridas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Datos
    n_filas: Mapped[int] = mapped_column(Integer, default=0)
    fecha_inicio: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    partidas: Mapped[list] = mapped_column(JSON, default=list)
    origen_datos: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Resultado del entrenamiento
    mejor_modelo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    mejora_vs_arima: Mapped[float | None] = mapped_column(Float, nullable=True)
    hipotesis_confirmada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    metodo_validacion: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tiene_pronosticos: Mapped[bool] = mapped_column(Boolean, default=False)

    usuario: Mapped[Usuario] = relationship(back_populates="corridas")
    resultados: Mapped[list["ResultadoModelo"]] = relationship(
        back_populates="corrida", cascade="all, delete-orphan", passive_deletes=True
    )
    pronosticos: Mapped[list["Pronostico"]] = relationship(
        back_populates="corrida", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Pronostico.fecha",
    )
    artefactos: Mapped[list["Artefacto"]] = relationship(
        back_populates="corrida", cascade="all, delete-orphan", passive_deletes=True
    )


class ResultadoModelo(Base):
    __tablename__ = "resultados_modelos"
    __table_args__ = (UniqueConstraint("corrida_id", "modelo", name="uq_resultado_corrida_modelo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corrida_id: Mapped[int] = mapped_column(ForeignKey("corridas.id", ondelete="CASCADE"), index=True)
    modelo: Mapped[str] = mapped_column(String(40))
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    mejora_vs_arima: Mapped[float | None] = mapped_column(Float, nullable=True)
    es_mejor: Mapped[bool] = mapped_column(Boolean, default=False)

    corrida: Mapped[Corrida] = relationship(back_populates="resultados")


class Pronostico(Base):
    __tablename__ = "pronosticos"
    __table_args__ = (UniqueConstraint("corrida_id", "fecha", name="uq_pronostico_corrida_fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corrida_id: Mapped[int] = mapped_column(ForeignKey("corridas.id", ondelete="CASCADE"), index=True)
    fecha: Mapped[datetime] = mapped_column(Date)
    prediccion: Mapped[float] = mapped_column(Float)
    limite_inferior: Mapped[float | None] = mapped_column(Float, nullable=True)
    limite_superior: Mapped[float | None] = mapped_column(Float, nullable=True)

    corrida: Mapped[Corrida] = relationship(back_populates="pronosticos")


class Artefacto(Base):
    """Objeto de sesión serializado (joblib) y firmado con HMAC-SHA256."""

    __tablename__ = "artefactos"
    __table_args__ = (UniqueConstraint("corrida_id", "clave", name="uq_artefacto_corrida_clave"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    corrida_id: Mapped[int] = mapped_column(ForeignKey("corridas.id", ondelete="CASCADE"), index=True)
    clave: Mapped[str] = mapped_column(String(60))
    contenido: Mapped[bytes] = mapped_column(LargeBinary)
    firma: Mapped[str] = mapped_column(String(64))
    huella: Mapped[str] = mapped_column(String(64))  # sha256 del contenido, para no re-escribir si no cambió
    tamano_bytes: Mapped[int] = mapped_column(Integer)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    corrida: Mapped[Corrida] = relationship(back_populates="artefactos")


class MensajeIA(Base):
    __tablename__ = "mensajes_ia"
    __table_args__ = (Index("ix_mensajes_usuario_pagina", "usuario_id", "pagina"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    corrida_id: Mapped[int | None] = mapped_column(
        ForeignKey("corridas.id", ondelete="SET NULL"), nullable=True
    )
    pagina: Mapped[str] = mapped_column(String(40))
    rol: Mapped[str] = mapped_column(String(12))  # user | assistant
    contenido: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UsoIA(Base):
    """Registro de cada llamada a la API de IA (para límite de uso y auditoría de costos)."""

    __tablename__ = "uso_ia"
    __table_args__ = (Index("ix_uso_usuario_fecha", "usuario_id", "creado_en"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    pagina: Mapped[str] = mapped_column(String(40))
    tipo: Mapped[str] = mapped_column(String(20))  # chat | analisis
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    exito: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    accion: Mapped[str] = mapped_column(String(40))
    detalle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
