from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


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
    device_id: int
    days_analyzed: int
    projected_monthly_kwh: float
    tariff_mxn_per_kwh: float
    projected_monthly_cost_mxn: float
    note: str = "Proyeccion calculada al vuelo; la etapa 8 la persiste con Tariff real."


class DevicePredictionOut(BaseModel):
    device_id: int
    projected_monthly_kwh: float
    trend_wh_per_day: float
    is_trending_up: bool
    method: str = "linear_trend_v0"
    note: str = "La etapa 9 persiste esto en Prediction y agrega deteccion de anomalias."


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
