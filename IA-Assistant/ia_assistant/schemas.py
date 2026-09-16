"""Tipos de datos puros — sin dependencias de FastAPI, SQLAlchemy ni de
ningún motor de inferencia. `backend-server` traduce sus propios modelos
ORM a estos tipos antes de llamar a `resolve_voice_command`, y traduce el
resultado real de la ejecución a `ExecutionOutcome` antes de pedir el texto
hablado — así este paquete se puede probar y reemplazar sin tocar la base
de datos."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentType(str, Enum):
    SWITCH_ON = "switch_on"
    SWITCH_OFF = "switch_off"
    QUERY_STATE = "query_state"
    QUERY_COST = "query_cost"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DeviceRef:
    """Vista mínima de un dispositivo real, ya filtrada a los que el
    usuario autenticado puede ver — el matcher nunca decide autorización,
    solo elige entre los nombres que se le pasan."""

    id: int
    name: str


@dataclass(frozen=True)
class VoiceIntent:
    type: IntentType
    device: DeviceRef | None = None
    days: int | None = None
    confidence: float = 0.0
    source: str = "none"  # "matcher" | "llm" | "none"
    ambiguous_candidates: tuple[DeviceRef, ...] = ()


@dataclass(frozen=True)
class ExecutionOutcome:
    """Resultado real de ejecutar (o consultar) la intención — llenado por
    `backend-server` con datos reales, nunca inventado. `responder.py` solo
    puede citar lo que venga acá."""

    ok: bool
    error_code: str | None = None  # "locked_out" | "not_found" | "no_device_match" | "ambiguous" | "internal"
    device_name: str | None = None
    actual_state: str | None = None
    is_locked_out: bool | None = None
    days_analyzed: int | None = None
    total_kwh: float | None = None
    total_cost: float | None = None
    currency: str | None = None
