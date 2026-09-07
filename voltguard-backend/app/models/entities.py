from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")  # "admin" o "user"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    devices: Mapped[list["Device"]] = relationship(back_populates="owner")


class DeviceGroup(Base):
    __tablename__ = "device_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    devices: Mapped[list["Device"]] = relationship(back_populates="group")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # ej: "DEV-ESP32-01"
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("device_groups.id"))
    max_current_threshold: Mapped[float] = mapped_column(Float, default=15.0)  # Amperios
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    relay_status: Mapped[bool] = mapped_column(Boolean, default=True)  # True = ON, False = OFF

    owner: Mapped[Optional[User]] = relationship(back_populates="devices")
    group: Mapped[Optional[DeviceGroup]] = relationship(back_populates="devices")
    readings: Mapped[list["Reading"]] = relationship(back_populates="device")


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    voltage: Mapped[float] = mapped_column(Float)
    current: Mapped[float] = mapped_column(Float)
    power: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    device: Mapped[Device] = relationship(back_populates="readings")