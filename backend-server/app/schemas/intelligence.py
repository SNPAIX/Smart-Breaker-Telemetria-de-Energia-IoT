from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Motor de reglas de corte (RF-4) ---
class SafetyThresholdUpdate(BaseModel):
    max_current_threshold: float = Field(..., gt=0.0, le=15.0)
    auto_cutoff_enabled: bool = True


class SafetyEventOut(BaseModel):
    id: int
    device_id: str
    event_type: str
    current: float
    max_current_threshold: float
    action_taken: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Detector de anomalías (informativo) ---
class AlertOut(BaseModel):
    id: int
    device_id: str
    power: float
    expected_power: float
    detector: str
    acknowledged: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Proyección de costo mensual ---
class CostProjectionFactor(BaseModel):
    factor: str
    value: float
    detail: str


class CostProjectionOut(BaseModel):
    device_id: str
    days_analyzed: int
    avg_daily_energy_wh: float
    trend_wh_per_day: float
    projected_monthly_kwh: float
    tariff_mxn_per_kwh: float
    projected_monthly_cost_mxn: float
    is_trending_up: bool
    percent_change_vs_previous_period: float | None = None
    factors: list[CostProjectionFactor] = []
