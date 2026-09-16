"""Servicios de dispositivo compartidos entre `/api/v1/app` (etapa 6) y
`/api/v1/admin` (etapa 7) — ninguna de las dos superficies debe reimplementar
esta lógica, solo exponerla vía rutas delgadas con su propia autorización.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
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
    SiteMember,
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


def _compute_bucketed_consumption(
    readings: list[TelemetryReading], bucket_key: Callable[[TelemetryReading], str]
) -> list[tuple[str, float]]:
    """Agrupa lecturas ya filtradas por rango con `bucket_key` (día u hora)
    y calcula el consumo real (Wh) de cada bucket — usada tanto por
    `compute_daily_consumption` como por `compute_hourly_consumption`, para
    no duplicar la regla "el primer bucket se estima con su propio rango,
    el resto por diferencia contra el máximo del bucket anterior" (ver
    docstring de `compute_daily_consumption`)."""
    buckets: dict[str, list[TelemetryReading]] = defaultdict(list)
    for reading in readings:
        buckets[bucket_key(reading)].append(reading)

    sorted_keys = sorted(buckets)
    if not sorted_keys:
        return []

    max_kwh = [max(r.energy for r in buckets[key]) for key in sorted_keys]
    first_min_kwh = min(r.energy for r in buckets[sorted_keys[0]])

    first_wh = max(0.0, (max_kwh[0] - first_min_kwh) * 1000.0)
    rest_wh = [max(0.0, (current - previous) * 1000.0) for previous, current in pairwise(max_kwh)]
    bucket_wh = [first_wh, *rest_wh]

    return list(zip(sorted_keys, bucket_wh, strict=True))


def compute_daily_consumption(
    db: Session,
    device_id: int,
    days: int = 14,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[int, list[tuple[str, float]]]:
    """Devuelve (lecturas_analizadas, [(fecha_iso, consumo_Wh), ...]).

    `energy` es la lectura acumulada del medidor en kWh (nunca se resetea
    sola), no el consumo del día. Para el segundo día en adelante, el
    consumo real es la diferencia entre el máximo acumulado de ese día y
    el del día anterior (línea base real). El *primer* día del rango no
    tiene un día anterior con el que diferenciar — en vez de descartarlo
    (como hacía esta función hasta el 15-sep), se estima con el propio
    rango de sus lecturas (máximo menos mínimo de ESE día): subestima un
    poco si hubo consumo antes de la primera lectura del día, pero evita
    mostrar "sin datos" el primer día real de un dispositivo recién
    conectado (bug reportado: consumo/costo en 0 con un solo día de
    telemetría). Misma lógica base que usaba
    `app/api/admin/devices_intelligence.py` en el repo base (ver ADR 0009).

    `start`/`end` permiten un rango explícito (para el selector de fechas
    personalizado); si no se dan, se usa `days` hacia atrás desde ahora.

    Se conserva la fecha de cada bucket (no solo el valor en Wh) porque la
    etapa 8 necesita saber qué tarifa estaba vigente cada día para
    prorratear el costo cuando el precio cambió a mitad del período.
    """
    range_end = end if end is not None else datetime.now(UTC)
    range_start = start if start is not None else range_end - timedelta(days=days)
    readings = (
        db.query(TelemetryReading)
        .filter(
            TelemetryReading.device_id == device_id,
            TelemetryReading.recorded_at >= range_start,
            TelemetryReading.recorded_at <= range_end,
        )
        .order_by(TelemetryReading.recorded_at.asc())
        .all()
    )

    dated_daily_wh = _compute_bucketed_consumption(
        readings, lambda r: r.recorded_at.strftime("%Y-%m-%d")
    )
    return len(readings), dated_daily_wh


def compute_hourly_consumption(
    db: Session, device_id: int, day: datetime
) -> list[tuple[str, float]]:
    """Consumo por hora de UN día calendario (UTC) — la vista "trazado a lo
    largo del día" pedida explícitamente para la gráfica, en vez de un solo
    punto por día. Misma regla de estimación que `compute_daily_consumption`,
    solo que el bucket es la hora en vez del día; como es un único día, no
    hace falta línea base de un día anterior. Devuelve
    [("YYYY-MM-DDTHH", kwh), ...] ya ordenado."""
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1, microseconds=-1)
    readings = (
        db.query(TelemetryReading)
        .filter(
            TelemetryReading.device_id == device_id,
            TelemetryReading.recorded_at >= day_start,
            TelemetryReading.recorded_at <= day_end,
        )
        .order_by(TelemetryReading.recorded_at.asc())
        .all()
    )

    hourly_wh = _compute_bucketed_consumption(
        readings, lambda r: r.recorded_at.strftime("%Y-%m-%dT%H")
    )
    return [(hour, round(wh / 1000.0, 4)) for hour, wh in hourly_wh]


def compute_minutely_consumption(
    db: Session, device_id: int, day: datetime
) -> list[tuple[str, float]]:
    """Igual que `compute_hourly_consumption`, con el bucket en minuto en
    vez de hora — vista "Hoy" con más resolución cuando la telemetría del
    dispositivo llega varias veces por segundo y un solo punto por hora
    se ve demasiado espaciado. Devuelve [("YYYY-MM-DDTHH:MM", kwh), ...]
    ya ordenado."""
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1, microseconds=-1)
    readings = (
        db.query(TelemetryReading)
        .filter(
            TelemetryReading.device_id == device_id,
            TelemetryReading.recorded_at >= day_start,
            TelemetryReading.recorded_at <= day_end,
        )
        .order_by(TelemetryReading.recorded_at.asc())
        .all()
    )

    minutely_wh = _compute_bucketed_consumption(
        readings, lambda r: r.recorded_at.strftime("%Y-%m-%dT%H:%M")
    )
    return [(minute, round(wh / 1000.0, 4)) for minute, wh in minutely_wh]


# Antes de sincronizar por NTP el firmware reporta timestamps desde epoch
# — sin este filtro, get_first_telemetry_date las toma como la primera
# lectura real y devuelve "1970-01-01" en vez de la fecha correcta.
MIN_PLAUSIBLE_TELEMETRY_AT = datetime(2020, 1, 1, tzinfo=UTC)


def get_first_telemetry_date(db: Session, device_id: int) -> str | None:
    """Fecha (YYYY-MM-DD) de la lectura más antigua *plausible* del
    dispositivo — límite inferior real para el selector de rango
    personalizado del consumo, no tiene sentido dejar elegir una fecha
    anterior a la primera lectura real."""
    first = (
        db.query(TelemetryReading)
        .filter(
            TelemetryReading.device_id == device_id,
            TelemetryReading.recorded_at >= MIN_PLAUSIBLE_TELEMETRY_AT,
        )
        .order_by(TelemetryReading.recorded_at.asc())
        .first()
    )
    return first.recorded_at.strftime("%Y-%m-%d") if first is not None else None


def get_consumption_series(
    db: Session,
    device_id: int,
    *,
    days: int,
    granularity: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[tuple[str, float]]:
    """Serie de consumo para graficar (etapa "vista de consumo") —
    reutiliza `compute_daily_consumption` tal cual (misma fuente de
    verdad que ya usa el costo real de la etapa 8) y, si se pide
    granularidad mensual, suma los días de cada mes calendario dentro del
    período. Devuelve [(periodo, kwh), ...] ya ordenado cronológicamente;
    `periodo` es "YYYY-MM-DD" para "day" o "YYYY-MM" para "month".

    `start`/`end` (rango personalizado, ver endpoint) tienen prioridad
    sobre `days` cuando se dan."""
    _, dated_daily_wh = compute_daily_consumption(db, device_id, days=days, start=start, end=end)

    if granularity == "day":
        return [(date_str, round(wh / 1000.0, 3)) for date_str, wh in dated_daily_wh]

    monthly_wh: dict[str, float] = defaultdict(float)
    for date_str, wh in dated_daily_wh:
        monthly_wh[date_str[:7]] += wh
    return [(month, round(wh / 1000.0, 3)) for month, wh in sorted(monthly_wh.items())]


def compute_daily_consumption_wh(
    db: Session, device_id: int, days: int = 14, *, drop_partial_first_day: bool = False
) -> tuple[int, list[float]]:
    """Igual que `compute_daily_consumption`, pero sin las fechas — lo que
    necesita la etapa 9 (tendencia) para no acoplarse a Tariff.

    `drop_partial_first_day=True` descarta el primer día del rango — la
    regresión lineal de la proyección (`app/services/predictions.py`) es
    sensible a un primer punto que representa un día parcial (su consumo
    real puede ser mayor al observado si hubo actividad antes de la
    primera lectura), y un salto artificial ahí distorsiona la pendiente
    calculada mucho más de lo que aporta incluirlo. `/cost` y
    `/consumption` sí lo incluyen (ver `compute_daily_consumption`) porque
    ahí un total aproximado es mejor que "sin datos"."""
    count, dated = compute_daily_consumption(db, device_id, days=days)
    wh_values = [wh for _, wh in dated]
    if drop_partial_first_day and len(wh_values) > 1:
        wh_values = wh_values[1:]
    return count, wh_values


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


def unlink_device(db: Session, device: Device) -> Device:
    """Contraparte de `claim_device`: desvincula un dispositivo de su sitio
    actual (`site_id = None`), disponible para cualquier miembro del sitio
    (autorización ya validada por `get_authorized_device` en el router, no
    acá). Es la vía que le permite a un usuario común liberar un
    dispositivo sin depender de un admin — antes de esto, solo existía la
    reasignación administrativa (`admin_reassign_device`)."""
    device.site_id = None
    db.commit()
    db.refresh(device)
    return device


def is_user_authorized_for_device(db: Session, user_id: int, device_id: int) -> bool:
    """Misma regla que `get_authorized_device` (dependencia HTTP en
    app/core/dependencies.py) pero como función pura que devuelve bool en
    vez de levantar HTTPException — la necesita también la suscripción a
    telemetría en vivo por WebSocket (app/api/app/ws.py), que no tiene
    dónde levantar un 404 HTTP a mitad de una conexión ya abierta."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None or device.site_id is None:
        return False
    membership = (
        db.query(SiteMember)
        .filter(SiteMember.site_id == device.site_id, SiteMember.user_id == user_id)
        .first()
    )
    return membership is not None


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
