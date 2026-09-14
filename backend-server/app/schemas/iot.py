from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TelemetryIn(BaseModel):
    """Contrato de telemetría versionado (ver roadmap/ORIGINAL-SPEC-README.md).

    Los nombres de campo usan unidades explícitas (`_v`, `_a`, `_w`, `_kwh`,
    `_hz`) para que no haya ambigüedad de unidades entre firmware y backend.
    """

    sequence: int = Field(..., ge=0)
    timestamp: datetime
    voltage_v: float = Field(..., ge=0.0, le=300.0)
    current_a: float = Field(..., ge=0.0, le=100.0)
    power_w: float = Field(..., ge=0.0)
    energy_kwh: float = Field(..., ge=0.0)
    frequency_hz: float = Field(default=60.0, ge=45.0, le=65.0)
    power_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    relay_state: Literal["ON", "OFF"]


class CommandOut(BaseModel):
    id: int
    type: str
    payload: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class TelemetryAck(BaseModel):
    status: Literal["success", "duplicate"] = "success"
    is_out_of_order: bool = False
    command: CommandOut | None = None


class HeartbeatAck(BaseModel):
    status: str = "ok"


class CommandAckIn(BaseModel):
    actual_state: Literal["ON", "OFF"]


class DeviceStateOut(BaseModel):
    device_id: int
    desired_state: str
    actual_state: str
