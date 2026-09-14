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

from app.config import settings
from app.models.entities import (
    Command,
    Device,
    DeviceProfile,
    Event,
    TelemetryReading,
    User,
)
from app.services.device_auth import issue_device_credential


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


def list_events(
    db: Session, *, device_id: int | None = None, event_type: str | None = None, limit: int = 100
) -> list[Event]:
    query = db.query(Event)
    if device_id is not None:
        query = query.filter(Event.device_id == device_id)
    if event_type is not None:
        query = query.filter(Event.type == event_type)
    return query.order_by(Event.created_at.desc()).limit(limit).all()


def list_device_events(db: Session, device_id: int, limit: int = 100) -> list[Event]:
    return list_events(db, device_id=device_id, limit=limit)


def compute_daily_consumption(
    db: Session, device_id: int, days: int = 14
) -> tuple[int, list[tuple[str, float]]]:
    """Devuelve (lecturas_analizadas, [(fecha_iso, consumo_Wh), ...]).

    `energy` es la lectura acumulada del medidor en kWh (nunca se resetea
    sola), no el consumo del día — el consumo real es la diferencia entre
    el máximo acumulado de un día y el del día anterior. El primer día del
    rango se descarta por no tener línea base previa. Misma lógica que
    usaba `app/api/admin/devices_intelligence.py` en el repo base (ver
    ADR 0009) — se reutiliza tal cual, solo cambia de dónde se llama.

    Se conserva la fecha de cada bucket (no solo el valor en Wh) porque la
    etapa 8 necesita saber qué tarifa estaba vigente cada día para
    prorratear el costo cuando el precio cambió a mitad del período.
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

    sorted_days = sorted(buckets)
    daily_energy_kwh = [max(r.energy for r in buckets[day]) for day in sorted_days]
    daily_wh = [
        max(0.0, (current - previous) * 1000.0) for previous, current in pairwise(daily_energy_kwh)
    ]
    # El primer día se descarta (sin línea base previa), así que las fechas
    # se alinean a partir del segundo día de `sorted_days`.
    dated_daily_wh = list(zip(sorted_days[1:], daily_wh, strict=True))
    return len(readings), dated_daily_wh


def compute_daily_consumption_wh(
    db: Session, device_id: int, days: int = 14
) -> tuple[int, list[float]]:
    """Igual que `compute_daily_consumption`, pero sin las fechas — lo que
    necesita la etapa 9 (tendencia) para no acoplarse a Tariff."""
    count, dated = compute_daily_consumption(db, device_id, days=days)
    return count, [wh for _, wh in dated]


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


def reactivate_device(db: Session, device: Device, actor: User) -> tuple[Command, Event]:
    """Reactivación explícita tras un evento crítico: limpia el bloqueo,
    deja trazabilidad de quién reactivó y emite la orden de encendido."""
    device.is_locked_out = False
    device.desired_state = "ON"
    event = Event(
        device_id=device.id,
        type="MANUAL_REACTIVATION",
        payload={"reactivated_by_user_id": actor.id},
    )
    db.add(event)
    command = Command(device_id=device.id, type="SET_RELAY_ON", status="PENDING")
    db.add(command)
    db.commit()
    db.refresh(command)
    db.refresh(event)
    return command, event


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


def is_device_online(device: Device) -> bool:
    if device.last_seen_at is None:
        return False
    age = datetime.now(UTC) - device.last_seen_at
    return age < timedelta(seconds=settings.device_online_threshold_seconds)


def create_device(
    db: Session,
    *,
    public_id: str,
    name: str,
    site_id: int | None = None,
    profile_id: int | None = None,
) -> tuple[Device, str]:
    """Alta administrativa de un dispositivo. Devuelve (device, secreto en
    texto plano) — el secreto solo existe fuera del hash en este momento,
    quien lo recibe debe guardarlo."""
    existing = db.query(Device).filter(Device.public_id == public_id).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un dispositivo con ese public_id.",
        )

    device = Device(public_id=public_id, name=name, site_id=site_id, profile_id=profile_id)
    db.add(device)
    db.commit()
    db.refresh(device)

    plain_secret = issue_device_credential(device)
    db.commit()
    db.refresh(device)
    return device, plain_secret


def list_all_devices(db: Session, *, site_id: int | None = None) -> list[Device]:
    query = db.query(Device)
    if site_id is not None:
        query = query.filter(Device.site_id == site_id)
    return query.order_by(Device.id.asc()).all()


def get_device_or_404(db: Session, device_id: int) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado."
        )
    return device


def update_device(
    db: Session, device: Device, *, name: str | None = None, profile_id: int | None = None
) -> Device:
    if name is not None:
        device.name = name
    if profile_id is not None:
        exists = db.query(DeviceProfile).filter(DeviceProfile.id == profile_id).first()
        if exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado."
            )
        device.profile_id = profile_id
    db.commit()
    db.refresh(device)
    return device


def admin_reassign_device(db: Session, device: Device, site_id: int | None) -> Device:
    """A diferencia de `claim_device` (solo para dispositivos sin sitio),
    el admin puede mover un dispositivo entre sitios libremente, o
    desvincularlo (`site_id=None`)."""
    device.site_id = site_id
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device: Device) -> None:
    db.delete(device)  # cascada: credential, telemetry_readings, commands, events, anomaly_alerts
    db.commit()
