
from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "DEV-ESP32-C3-01"})
    name: str = Field(..., json_schema_extra={"example": "Refrigerador Taller"})
    max_current_threshold: float = Field(default=15.0, le=15.0, description="Máximo 15A por fusible T15A")


class DeviceToggle(BaseModel):
    relay_status: bool


class DeviceOut(DeviceCreate):
    owner_id: int | None = None
    group_id: int | None = None
    auto_cutoff_enabled: bool = True
    is_active: bool
    relay_status: bool

    model_config = ConfigDict(from_attributes=True)