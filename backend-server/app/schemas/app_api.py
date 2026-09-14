from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SiteOut(BaseModel):
    id: int
    name: str
    kind: str

    model_config = ConfigDict(from_attributes=True)


class DeviceOut(BaseModel):
    id: int
    public_id: str
    name: str
    site_id: int | None
    desired_state: str
    actual_state: str
    is_locked_out: bool
    last_seen_at: datetime | None
    firmware_version: str | None

    model_config = ConfigDict(from_attributes=True)


class TelemetryOut(BaseModel):
    id: int
    sequence: int
    voltage: float
    current: float
    power: float
    frequency: float
    power_factor: float
    energy: float
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventOut(BaseModel):
    id: int
    type: str
    payload: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceMetricsOut(BaseModel):
    """Vista mínima viable — la etapa 8 la reemplaza por agregaciones
    día/mes reales."""

    device_id: int
    readings_count: int
    latest_voltage: float | None = None
    latest_current: float | None = None
    latest_power: float | None = None
    last_seen_at: datetime | None = None


class DeviceCostOut(BaseModel):
    """Costo real del período analizado (no una proyección) — cada día se
    valora con la tarifa que estaba vigente ese día. Ver `DevicePredictionOut`
    para la proyección a futuro."""

    device_id: int
    days_analyzed: int
    total_kwh: float
    total_cost: float
    currency: str
    used_default_tariff: bool = Field(
        description="True si el sitio no tiene ninguna Tariff configurada para algún día del período."
    )


class DevicePredictionOut(BaseModel):
    """Refleja directamente una fila persistida de `Prediction` — generada
    de forma perezosa y cacheada (ver `app/services/predictions.py`)."""

    device_id: int
    horizon: str
    projected_kwh: float
    projected_cost: float
    method: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: int
    channel: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceIn(BaseModel):
    channel: str
    enabled: bool


class NotificationPreferenceOut(BaseModel):
    channel: str
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class SwitchIn(BaseModel):
    desired_state: Literal["ON", "OFF"]


class ClaimIn(BaseModel):
    public_id: str
    site_id: int


class DeviceStateOut(BaseModel):
    device_id: int
    desired_state: str
    actual_state: str
    is_locked_out: bool
