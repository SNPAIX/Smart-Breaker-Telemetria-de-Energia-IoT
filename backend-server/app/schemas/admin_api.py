from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "user"


class UserUpdateIn(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class SiteCreateIn(BaseModel):
    name: str
    kind: str = "otro"


class SiteUpdateIn(BaseModel):
    name: str | None = None
    kind: str | None = None


class DeviceCreateIn(BaseModel):
    public_id: str
    name: str
    site_id: int | None = None
    profile_id: int | None = None


class DeviceCreateOut(BaseModel):
    id: int
    public_id: str
    name: str
    site_id: int | None
    profile_id: int | None
    secret: str = Field(..., description="Solo se muestra una vez; no se puede recuperar después.")


class DeviceUpdateIn(BaseModel):
    name: str | None = None
    profile_id: int | None = None


class DeviceReassignIn(BaseModel):
    site_id: int | None


class ProfileCreateIn(BaseModel):
    name: str
    site_id: int | None = None
    max_current_a: float = 15.0
    min_voltage_v: float | None = None
    max_voltage_v: float | None = None
    auto_cutoff_enabled: bool = True


class ProfileUpdateIn(BaseModel):
    max_current_a: float | None = None
    min_voltage_v: float | None = None
    max_voltage_v: float | None = None
    auto_cutoff_enabled: bool | None = None


class ProfileOut(BaseModel):
    id: int
    name: str
    site_id: int | None
    max_current_a: float
    min_voltage_v: float | None
    max_voltage_v: float | None
    auto_cutoff_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class AdminEventOut(BaseModel):
    id: int
    device_id: int
    type: str
    payload: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GlobalMetricsOut(BaseModel):
    total_sites: int
    total_users: int
    total_devices: int
    devices_online: int
    devices_offline: int
    critical_events_last_24h: int

    model_config = ConfigDict(from_attributes=True)


class SiteMetricsOut(BaseModel):
    site_id: int
    site_name: str
    device_count: int
    devices_online: int

    model_config = ConfigDict(from_attributes=True)


class ProfileMetricsOut(BaseModel):
    profile_id: int
    profile_name: str
    device_count: int

    model_config = ConfigDict(from_attributes=True)


class AdminOverviewOut(BaseModel):
    global_metrics: GlobalMetricsOut
    by_site: list[SiteMetricsOut]
    by_profile: list[ProfileMetricsOut]

    model_config = ConfigDict(from_attributes=True)
