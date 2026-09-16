from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SiteOut(BaseModel):
    id: int
    name: str
    kind: str

    model_config = ConfigDict(from_attributes=True)


class MySiteOut(SiteOut):
    """`SiteOut` normal más el rol propio del usuario en ese sitio y el
    correo del dueño real — "Mis sitios" necesita distinguir a primera
    vista si el usuario es dueño, invitado, o (si es admin) está ahí de
    soporte temporal, sin tener que adivinarlo ni abrir nada."""

    my_role: Literal["owner", "member"]
    owner_email: str | None = None


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


class SiteCreateIn(BaseModel):
    """Alta de sitio por el propio usuario final (a diferencia de
    `admin_api.SiteCreateIn`, acá quien crea el sitio queda automáticamente
    como su primer miembro con rol "owner" — ver `create_my_site`)."""

    name: str
    kind: str = "otro"


class DeviceSelfCreateIn(BaseModel):
    """Alta de dispositivo por un usuario final dentro de un sitio propio.

    A diferencia de `admin_api.DeviceCreateIn`, acá no se pide `profile_id`
    — el usuario final no debería tener que entender qué es un
    `DeviceProfile` primero; el endpoint crea uno propio para el
    dispositivo con el umbral que el usuario indique (o el default)."""

    public_id: str
    name: str
    max_current_a: float = 15.0


class DeviceStateOut(BaseModel):
    device_id: int
    desired_state: str
    actual_state: str
    is_locked_out: bool


class ConsumptionPointOut(BaseModel):
    period: str = Field(
        description='"YYYY-MM-DD" si granularity="day", "YYYY-MM" si "month", '
        '"YYYY-MM-DDTHH" si "hour", "YYYY-MM-DDTHH:MM" si "minute".'
    )
    kwh: float


class DeviceConsumptionOut(BaseModel):
    device_id: int
    granularity: Literal["minute", "hour", "day", "month"]
    points: list[ConsumptionPointOut]
    earliest_date: str | None = Field(
        default=None,
        description='"YYYY-MM-DD" de la lectura más antigua del dispositivo — límite '
        "inferior real para un rango personalizado, null si nunca reportó telemetría.",
    )


class VoiceQueryIn(BaseModel):
    """Texto ya transcrito por STT en el celular — este endpoint nunca
    recibe audio, solo texto (etapa 14)."""

    text: str = Field(min_length=1, max_length=500)


class VoiceQueryOut(BaseModel):
    """`spoken_text` es lo único que el celular necesita pasarle a su TTS
    nativo — siempre construido a partir del resultado real de la acción o
    consulta, nunca un texto genérico (ver IA-Assistant/ia_assistant/responder.py)."""

    spoken_text: str
    action_taken: bool
    intent_type: str
    device_id: int | None = None
