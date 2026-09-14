from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    site_memberships: Mapped[list["SiteMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notification_preferences: Mapped[list["NotificationPreference"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Site(Base):
    """Abstracción de sitio: casa, laboratorio, taller, negocio, sucursal.

    Reemplaza la relación directa User -> Device del repo base. Un usuario
    accede a un dispositivo únicamente a través de su membresía a un Site
    (ver SiteMember) — nunca por una FK directa Device.owner_id.
    """

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(50), default="otro")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    members: Mapped[list["SiteMember"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(back_populates="site")
    device_profiles: Mapped[list["DeviceProfile"]] = relationship(back_populates="site")
    tariffs: Mapped[list["Tariff"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )


class SiteMember(Base):
    """Membresía de un usuario a un sitio, con un rol dentro de ese sitio.

    MVP: solo se usan los roles "owner" y "member". El campo admite
    evolucionar a "viewer" sin cambio de esquema cuando haga falta.
    """

    __tablename__ = "site_members"
    __table_args__ = (UniqueConstraint("site_id", "user_id", name="uq_site_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    site: Mapped[Site] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="site_memberships")


class DeviceProfile(Base):
    """Umbrales y configuración de seguridad reutilizable entre dispositivos.

    `site_id` es opcional a propósito: un dispositivo recién fabricado (aún
    sin reclamar por ningún sitio) igual necesita un perfil de fábrica con
    umbrales seguros por defecto.
    """

    __tablename__ = "device_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), default="default")
    max_current_a: Mapped[float] = mapped_column(Float, default=15.0)
    # Nullable: un perfil sin límites de voltaje configurados no dispara la
    # regla de sobre/bajo voltaje (ver app/services/voltage_rules.py).
    min_voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_cutoff_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    site: Mapped[Site | None] = relationship(back_populates="device_profiles")
    devices: Mapped[list["Device"]] = relationship(back_populates="profile")


class Device(Base):
    """`public_id` es el identificador estable que ve el usuario/firmware
    (ej. "VG-001"); `id` es la clave interna, para no acoplar la PK a un
    valor que en algún momento podría necesitar reasignarse."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_profiles.id"), nullable=True, index=True
    )

    # Una orden enviada por el servidor (desired_state) no demuestra que el
    # relé haya cambiado físicamente (actual_state) — ver Command.
    desired_state: Mapped[str] = mapped_column(String(10), default="OFF")
    actual_state: Mapped[str] = mapped_column(String(10), default="UNKNOWN")

    # Tras un evento crítico (sobrecorriente o sobre/bajo voltaje) queda en
    # True y bloquea cualquier reactivación automática: solo un endpoint
    # explícito (etapa 6, /api/v1/app/devices/{id}/reactivate) puede
    # limpiarlo. Ningún flujo de telemetría/heartbeat lo modifica a False.
    is_locked_out: Mapped[bool] = mapped_column(Boolean, default=False)

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    site: Mapped[Site | None] = relationship(back_populates="devices")
    profile: Mapped[DeviceProfile | None] = relationship(back_populates="devices")
    credential: Mapped["DeviceCredential | None"] = relationship(
        back_populates="device", cascade="all, delete-orphan", uselist=False
    )
    telemetry_readings: Mapped[list["TelemetryReading"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    commands: Mapped[list["Command"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    anomaly_alerts: Mapped[list["AnomalyAlert"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class DeviceCredential(Base):
    """Credencial propia del dispositivo (relación 1:1 con Device), separada
    de la autenticación de usuario: ciclo de vida y revocación distintos."""

    __tablename__ = "device_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), unique=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[Device] = relationship(back_populates="credential")


class TelemetryReading(Base):
    """Lectura de telemetría (renombrada desde `Reading` del repo base).

    `sequence` es el contador incremental que arma el propio firmware; sirve
    para detectar secuencia duplicada o fuera de orden (ver etapa 4).
    """

    __tablename__ = "telemetry_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    voltage: Mapped[float] = mapped_column(Float)
    current: Mapped[float] = mapped_column(Float)
    power: Mapped[float] = mapped_column(Float)
    frequency: Mapped[float] = mapped_column(Float, default=60.0)
    power_factor: Mapped[float] = mapped_column(Float, default=1.0)
    energy: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    device: Mapped[Device] = relationship(back_populates="telemetry_readings")


class Command(Base):
    """Orden pendiente de entregar al dispositivo (cola simple, sin broker).

    `status` transiciona PENDING -> ACKED (o EXPIRED si nunca se confirma;
    la política de expiración se define cuando algún flujo la necesite,
    ver roadmap etapa 4)."""

    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[Device] = relationship(back_populates="commands")


class Event(Base):
    """Evento genérico de dispositivo (generaliza `SafetyEvent` del repo
    base — ver roadmap/01-gap-analysis.md). `type="CRITICAL_OVERLOAD"` cubre
    el caso que antes tenía tabla propia; el `payload` JSON guarda los datos
    específicos de cada tipo de evento sin necesitar una columna por caso."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    device: Mapped[Device] = relationship(back_populates="events")


class AnomalyAlert(Base):
    """Anomalía de consumo detectada (renombrada desde `Alert` del repo base
    para no confundirse con `Event`): compara una lectura contra el
    histórico del propio dispositivo y nunca corta la energía por sí sola."""

    __tablename__ = "anomaly_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    power: Mapped[float] = mapped_column(Float)
    expected_power: Mapped[float] = mapped_column(Float)
    detector: Mapped[str] = mapped_column(String(50))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    device: Mapped[Device] = relationship(back_populates="anomaly_alerts")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(1000))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_notification_preference"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="notification_preferences")


class Tariff(Base):
    """Precio por kWh vigente en un rango de fechas. Se conserva el
    histórico (no se sobrescribe) para poder prorratear el costo cuando la
    tarifa cambia a mitad de un período (ver etapa 8)."""

    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    currency: Mapped[str] = mapped_column(String(10), default="MXN")
    price_per_kwh: Mapped[float] = mapped_column(Float)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped[Site] = relationship(back_populates="tariffs")


class Prediction(Base):
    """Resultado persistido de una proyección de consumo/costo (etapa 9),
    para no tener que recalcularla en cada consulta."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    horizon: Mapped[str] = mapped_column(String(20), default="monthly")
    projected_kwh: Mapped[float] = mapped_column(Float)
    projected_cost: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(50))
