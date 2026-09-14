"""Servicios de dispositivo compartidos entre `/api/v1/app` (etapa 6) y
`/api/v1/admin` (etapa 7) — ninguna de las dos superficies debe reimplementar
esta lógica, solo exponerla vía rutas delgadas con su propia autorización.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Command, Device, Event, TelemetryReading, User


def list_recent_telemetry(
    db: Session, device_id: int, limit: int = 100
) -> list[TelemetryReading]:
    return (
        db.query(TelemetryReading)
        .filter(TelemetryReading.device_id == device_id)
        .order_by(TelemetryReading.recorded_at.desc())
        .limit(limit)
        .all()
    )


def list_device_events(db: Session, device_id: int, limit: int = 100) -> list[Event]:
    return (
        db.query(Event)
        .filter(Event.device_id == device_id)
        .order_by(Event.created_at.desc())
        .limit(limit)
        .all()
    )


def compute_daily_consumption_wh(
    db: Session, device_id: int, days: int = 14
) -> tuple[int, list[float]]:
    """Devuelve (lecturas_analizadas, consumo_diario_en_Wh).

    `energy` es la lectura acumulada del medidor en kWh (nunca se resetea
    sola), no el consumo del día — el consumo real es la diferencia entre
    el máximo acumulado de un día y el del día anterior. El primer día del
    rango se descarta por no tener línea base previa. Misma lógica que
    usaba `app/api/admin/devices_intelligence.py` en el repo base (ver
    ADR 0009) — se reutiliza tal cual, solo cambia de dónde se llama.
    """
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    readings = (
        db.query(TelemetryReading)
        .filter(TelemetryReading.device_id == device_id, TelemetryReading.recorded_at >= start)
        .order_by(TelemetryReading.recorded_at.asc())
        .all()
    )

    buckets: dict[str, list[TelemetryReading]] = defaultdict(list)
    for reading in readings:
        buckets[reading.recorded_at.strftime("%Y-%m-%d")].append(reading)

    daily_energy_kwh = [max(r.energy for r in buckets[day]) for day in sorted(buckets)]
    daily_wh = [
        max(0.0, (current - previous) * 1000.0) for previous, current in pairwise(daily_energy_kwh)
    ]
    return len(readings), daily_wh


def switch_device(db: Session, device: Device, desired_state: str) -> Command:
    """Enciende/apaga un dispositivo a petición explícita del usuario/admin.

    Rechaza encender (`ON`) un dispositivo bloqueado por un evento crítico
    (etapa 5, `Device.is_locked_out`) — solo `reactivate_device` puede
    limpiar ese bloqueo, nunca un `switch` normal.
    """
    if desired_state == "ON" and device.is_locked_out:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El dispositivo está bloqueado por un evento crítico. "
                "Debe reactivarse explícitamente antes de encenderlo."
            ),
        )

    command_type = "SET_RELAY_ON" if desired_state == "ON" else "SET_RELAY_OFF"
    command = Command(device_id=device.id, type=command_type, status="PENDING")
    db.add(command)
    device.desired_state = desired_state
    db.commit()
    db.refresh(command)
    return command


def reactivate_device(db: Session, device: Device, actor: User) -> Command:
    """Reactivación explícita tras un evento crítico: limpia el bloqueo,
    deja trazabilidad de quién reactivó y emite la orden de encendido."""
    device.is_locked_out = False
    device.desired_state = "ON"
    db.add(
        Event(
            device_id=device.id,
            type="MANUAL_REACTIVATION",
            payload={"reactivated_by_user_id": actor.id},
        )
    )
    command = Command(device_id=device.id, type="SET_RELAY_ON", status="PENDING")
    db.add(command)
    db.commit()
    db.refresh(command)
    return command


def claim_device(db: Session, device: Device, site_id: int) -> Device:
    """Vincula un dispositivo sin sitio a un sitio destino. Un dispositivo
    ya vinculado no puede reclamarse de nuevo por esta vía (ver etapa 7
    para reasignación administrativa, que sí puede mover un dispositivo
    entre sitios)."""
    if device.site_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El dispositivo ya está vinculado a un sitio.",
        )
    device.site_id = site_id
    db.commit()
    db.refresh(device)
    return device
