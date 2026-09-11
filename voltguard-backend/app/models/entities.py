from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    devices: Mapped[list["Device"]] = relationship(back_populates="owner")


class DeviceGroup(Base):
    __tablename__ = "device_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))

    devices: Mapped[list["Device"]] = relationship(back_populates="group")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("device_groups.id"))
    max_current_threshold: Mapped[float] = mapped_column(Float, default=15.0)
    auto_cutoff_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    relay_status: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped[User | None] = relationship(back_populates="devices")
    group: Mapped[DeviceGroup | None] = relationship(back_populates="devices")
    readings: Mapped[list["Reading"]] = relationship(back_populates="device")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    safety_events: Mapped[list["SafetyEvent"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    voltage: Mapped[float] = mapped_column(Float)
    current: Mapped[float] = mapped_column(Float)
    power: Mapped[float] = mapped_column(Float)
    frequency: Mapped[float] = mapped_column(Float, default=60.0)
    power_factor: Mapped[float] = mapped_column(Float, default=1.0)
    energy: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    device: Mapped[Device] = relationship(back_populates="readings")


class Alert(Base):
    """Anomalía de consumo detectada para un dispositivo (informativa).

    Distinta de SafetyEvent: Alert compara una lectura de potencia contra
    el historial reciente del propio dispositivo (¿esto es raro?) y nunca
    corta la corriente por sí sola. La genera el detector intercambiable
    de app/services/anomaly_detector.py (rule_based o isolation_forest).
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    power: Mapped[float] = mapped_column(Float)
    expected_power: Mapped[float] = mapped_column(Float)
    detector: Mapped[str] = mapped_column(String(50))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    device: Mapped[Device] = relationship(back_populates="alerts")


class SafetyEvent(Base):
    """Evento de corte automático por sobrecarga crítica (RF-4).

    Distinta de Alert: SafetyEvent es la violación de un umbral de
    seguridad duro (max_current_threshold), evaluada de forma síncrona en
    el router de telemetría, y siempre dispara una orden de apagado
    inmediata (relay_status = False). No aprende nada ni necesita
    historial, a diferencia del detector de anomalías.
    """

    __tablename__ = "safety_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), default="CRITICAL_OVERLOAD")
    current: Mapped[float] = mapped_column(Float)
    max_current_threshold: Mapped[float] = mapped_column(Float)
    action_taken: Mapped[str] = mapped_column(
        String(50), default="SHUTDOWN_ORDER_ISSUED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    device: Mapped[Device] = relationship(back_populates="safety_events")