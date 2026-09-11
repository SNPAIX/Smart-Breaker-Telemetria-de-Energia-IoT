from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Ingesta desde el ESP32-C3 ---
class TelemetryReadingCreate(BaseModel):
    device_id: str = Field(..., json_schema_extra={"example": "DEV-ESP32-C3-01"})
    voltage: float = Field(..., ge=0.0, le=300.0, description="Voltaje en VCA")
    current: float = Field(..., ge=0.0, le=100.0, description="Corriente RMS en A")
    power: float = Field(..., ge=0.0, description="Potencia activa en W")
    frequency: float = Field(default=60.0, ge=45.0, le=65.0, description="Frecuencia en Hz")
    power_factor: float = Field(default=1.0, ge=0.0, le=1.0, description="Factor de potencia (0.0 a 1.0)")
    energy: float = Field(default=0.0, ge=0.0, description="Energía acumulada en kWh")


# --- Respuesta de la API hacia el ESP32 ---
class TelemetryResponse(BaseModel):
    status: str
    relay_status: bool  # True = Mantener energizado, False = Cortar (GPIO6 LOW)
    alert: str | None = None


# --- Lectura para Consultas HTTP / Dashboard ---
class ReadingOut(TelemetryReadingCreate):
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)