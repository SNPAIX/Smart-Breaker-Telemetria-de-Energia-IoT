from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_authorized_device,
    get_current_site_member,
    get_current_user,
)
from app.db import get_db
from app.models.entities import (
    Device,
    Event,
    Notification,
    NotificationPreference,
    Prediction,
    Site,
    SiteMember,
    TelemetryReading,
    User,
)
from app.schemas.admin_api import DeviceCreateOut, SiteUpdateIn
from app.schemas.app_api import (
    ClaimIn,
    ConsumptionPointOut,
    DeviceConsumptionOut,
    DeviceCostOut,
    DeviceMetricsOut,
    DeviceOut,
    DevicePredictionOut,
    DeviceSelfCreateIn,
    DeviceStateOut,
    EventOut,
    MySiteOut,
    NotificationOut,
    NotificationPreferenceIn,
    NotificationPreferenceOut,
    SiteCreateIn,
    SiteOut,
    SwitchIn,
    TelemetryOut,
)
from app.schemas.iot import CommandOut
from app.services.costs import compute_cost_breakdown
from app.services.device_profiles import create_profile
from app.services.devices import (
    claim_device,
    compute_daily_consumption_wh,
    compute_hourly_consumption,
    create_device,
    get_consumption_series,
    get_first_telemetry_date,
    list_device_events,
    list_recent_telemetry,
    reactivate_device,
    switch_device,
    unlink_device,
)
from app.services.notifications import get_notification_preferences, notify_event_by_id
from app.services.predictions import get_or_generate_prediction
from app.services.push import push_command_to_device
from app.services.sites import (
    add_site_member,
    create_site,
    delete_site,
    get_site_or_404,
    list_site_devices,
    list_user_sites_with_role,
    remove_site_member,
    update_site,
)

router = APIRouter(prefix="/api/v1/app", tags=["App (usuario final)"])


@router.get("/sites", response_model=list[MySiteOut])
def get_my_sites(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    return list_user_sites_with_role(db, current_user.id)


@router.post("/sites", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_my_site(
    payload: SiteCreateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Site:
    """Alta de sitio por el usuario final — a diferencia de
    `POST /api/v1/admin/sites`, acá quien lo crea queda automáticamente
    como su primer miembro (rol "owner"), porque no hay un admin del otro
    lado que lo agregue después."""
    site = create_site(db, name=payload.name, kind=payload.kind)
    add_site_member(db, site.id, current_user.id, role="owner")
    return site


@router.patch("/sites/{site_id}", response_model=SiteOut)
def rename_my_site(
    site_id: int,
    payload: SiteUpdateIn,
    membership: SiteMember = Depends(get_current_site_member),
    db: Session = Depends(get_db),
) -> Site:
    """Cualquier miembro del sitio puede renombrarlo (a diferencia de
    borrar, que es solo del dueño) — cambiar el nombre no tiene el mismo
    riesgo que perder el sitio entero."""
    site = get_site_or_404(db, site_id)
    return update_site(db, site, name=payload.name, kind=payload.kind)


@router.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_site(
    site_id: int,
    membership: SiteMember = Depends(get_current_site_member),
    db: Session = Depends(get_db),
) -> None:
    """Solo el dueño del sitio puede eliminarlo — un miembro común
    (agregado por el dueño o vinculado a un dispositivo compartido) no
    debería poder borrar el sitio de otra persona. Reutiliza
    `delete_site` (etapa 7), que ya rechaza el borrado si el sitio
    todavía tiene dispositivos asignados."""
    if membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño del sitio puede eliminarlo.",
        )
    site = get_site_or_404(db, site_id)
    delete_site(db, site)


@router.delete("/sites/{site_id}/membership", status_code=status.HTTP_204_NO_CONTENT)
def leave_my_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    membership: SiteMember = Depends(get_current_site_member),
    db: Session = Depends(get_db),
) -> None:
    """Salida propia de un sitio — nunca de otro usuario (eso sigue siendo
    exclusivo del admin, ver /api/v1/admin/sites/{id}/members/{user_id}).
    Es lo que usa el botón "Desvincular" del acceso de soporte temporal en
    "Mis sitios": un admin que se agregó a sí mismo puede salir sin tener
    que volver al panel de administración."""
    del membership  # solo valida que efectivamente pertenece al sitio
    remove_site_member(db, site_id, current_user.id)


@router.post("/sites/{site_id}/devices", response_model=DeviceCreateOut, status_code=status.HTTP_201_CREATED)
def create_my_device(
    site_id: int,
    payload: DeviceSelfCreateIn,
    db: Session = Depends(get_db),
    _membership: SiteMember = Depends(get_current_site_member),
) -> DeviceCreateOut:
    """Alta de dispositivo por el usuario final dentro de un sitio propio.

    Crea un `DeviceProfile` propio para el dispositivo (el usuario final no
    tiene por qué manejar perfiles como concepto aparte) y devuelve el
    `public_id`/`secret` que hay que cargar en el dispositivo físico vía el
    portal cautivo de aprovisionamiento (etapa 12) — el mismo flujo que ya
    usa el admin, solo que ahora también lo puede iniciar el usuario dueño
    del sitio."""
    profile = create_profile(db, name=f"{payload.name} (auto)", site_id=site_id, max_current_a=payload.max_current_a)
    device, secret = create_device(
        db, public_id=payload.public_id, name=payload.name, site_id=site_id, profile_id=profile.id
    )
    return DeviceCreateOut(
        id=device.id,
        public_id=device.public_id,
        name=device.name,
        site_id=device.site_id,
        profile_id=device.profile_id,
        secret=secret,
    )


@router.get("/sites/{site_id}/devices", response_model=list[DeviceOut])
def get_site_devices(
    site_id: int,
    db: Session = Depends(get_db),
    _membership: SiteMember = Depends(get_current_site_member),
) -> list[Device]:
    return list_site_devices(db, site_id)


@router.post("/devices/claim", response_model=DeviceOut)
def claim_a_device(
    payload: ClaimIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Device:
    """El usuario ingresa el `public_id` que el dispositivo expone en su
    aprovisionamiento local (etapa 12) y el sitio destino, del que debe ser
    miembro. No requiere `get_current_site_member` como dependencia porque
    `site_id` viaja en el body, no en el path — se valida aquí mismo."""
    membership = (
        db.query(SiteMember)
        .filter(SiteMember.site_id == payload.site_id, SiteMember.user_id == current_user.id)
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="El usuario no pertenece a este sitio."
        )

    device = db.query(Device).filter(Device.public_id == payload.public_id).first()
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado."
        )

    return claim_device(db, device, payload.site_id)


@router.post("/devices/{device_id}/unlink", response_model=DeviceOut)
def unlink_a_device(
    device: Device = Depends(get_authorized_device), db: Session = Depends(get_db)
) -> Device:
    """Contraparte de `/devices/claim`: cualquier miembro del sitio actual
    del dispositivo puede desvincularlo (vuelve a quedar sin sitio, listo
    para que alguien lo reclame de nuevo). `get_authorized_device` ya
    confirma la membresía — sin este endpoint, la única forma de
    desvincular un dispositivo era a través de un admin."""
    return unlink_device(db, device)


@router.get("/devices/{device_id}", response_model=DeviceOut)
def get_device_detail(device: Device = Depends(get_authorized_device)) -> Device:
    return device


@router.get("/devices/{device_id}/telemetry", response_model=list[TelemetryOut])
def get_device_telemetry(
    limit: int = 100,
    device: Device = Depends(get_authorized_device),
    db: Session = Depends(get_db),
) -> list[TelemetryReading]:
    return list_recent_telemetry(db, device.id, limit=limit)


@router.get("/devices/{device_id}/events", response_model=list[EventOut])
def get_device_events(
    limit: int = 100,
    device: Device = Depends(get_authorized_device),
    db: Session = Depends(get_db),
) -> list[Event]:
    return list_device_events(db, device.id, limit=limit)


@router.get("/devices/{device_id}/metrics", response_model=DeviceMetricsOut)
def get_device_metrics(
    device: Device = Depends(get_authorized_device), db: Session = Depends(get_db)
) -> DeviceMetricsOut:
    readings = list_recent_telemetry(db, device.id, limit=1)
    latest = readings[0] if readings else None
    _, daily_wh = compute_daily_consumption_wh(db, device.id)
    return DeviceMetricsOut(
        device_id=device.id,
        readings_count=len(daily_wh),
        latest_voltage=latest.voltage if latest else None,
        latest_current=latest.current if latest else None,
        latest_power=latest.power if latest else None,
        last_seen_at=device.last_seen_at,
    )


@router.get("/devices/{device_id}/cost", response_model=DeviceCostOut)
def get_device_cost(
    device: Device = Depends(get_authorized_device), db: Session = Depends(get_db)
) -> DeviceCostOut:
    breakdown = compute_cost_breakdown(db, device)
    return DeviceCostOut(
        device_id=device.id,
        days_analyzed=breakdown.days_analyzed,
        total_kwh=breakdown.total_kwh,
        total_cost=breakdown.total_cost,
        currency=breakdown.currency,
        used_default_tariff=breakdown.used_default_tariff,
    )


@router.get("/devices/{device_id}/consumption", response_model=DeviceConsumptionOut)
def get_device_consumption(
    days: int = 30,
    granularity: str = "day",
    start: str | None = None,
    end: str | None = None,
    device: Device = Depends(get_authorized_device),
    db: Session = Depends(get_db),
) -> DeviceConsumptionOut:
    """Vista para graficar consumo real por rango de tiempo seleccionable
    — misma fuente de verdad que `/cost` (`compute_daily_consumption`),
    solo agregada distinto. `granularity=month` tiene sentido con `days`
    grande (ej. 365); con `days` chico simplemente da uno o dos puntos.

    `start`/`end` (formato "YYYY-MM-DD") arman un rango personalizado en
    vez de `days` — para el selector de fecha, `earliest_date` en la
    respuesta es el límite inferior real (la primera lectura que existe).

    `granularity="hour"` es la vista "hoy, trazado a lo largo del día" —
    ignora `days`/`start`/`end` y siempre usa el día calendario UTC actual
    (ver `compute_hourly_consumption`)."""
    if granularity not in ("hour", "day", "month"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='granularity debe ser "hour", "day" o "month".',
        )

    if granularity == "hour":
        hourly = compute_hourly_consumption(db, device.id, datetime.now(UTC))
        return DeviceConsumptionOut(
            device_id=device.id,
            granularity="hour",
            points=[ConsumptionPointOut(period=period, kwh=kwh) for period, kwh in hourly],
            earliest_date=get_first_telemetry_date(db, device.id),
        )

    range_start: datetime | None = None
    range_end: datetime | None = None
    if start is not None or end is not None:
        try:
            if start is not None:
                range_start = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=UTC)
            if end is not None:
                range_end = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=UTC) + timedelta(
                    days=1, microseconds=-1
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='start/end deben tener formato "YYYY-MM-DD".',
            ) from exc
        if range_start is not None and range_end is not None and range_start > range_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="start no puede ser posterior a end."
            )

    series = get_consumption_series(
        db, device.id, days=days, granularity=granularity, start=range_start, end=range_end
    )
    return DeviceConsumptionOut(
        device_id=device.id,
        granularity=granularity,
        points=[ConsumptionPointOut(period=period, kwh=kwh) for period, kwh in series],
        earliest_date=get_first_telemetry_date(db, device.id),
    )


@router.get("/devices/{device_id}/prediction", response_model=DevicePredictionOut)
def get_device_prediction(
    device: Device = Depends(get_authorized_device), db: Session = Depends(get_db)
) -> Prediction:
    return get_or_generate_prediction(db, device)


@router.post("/devices/{device_id}/switch", response_model=DeviceStateOut)
def switch(
    payload: SwitchIn,
    background_tasks: BackgroundTasks,
    device: Device = Depends(get_authorized_device),
    db: Session = Depends(get_db),
) -> DeviceStateOut:
    command = switch_device(db, device, payload.desired_state)
    # Empuja el comando por WebSocket si hay conexión abierta; si no, el
    # poll de respaldo lo entrega igual en el próximo ciclo.
    background_tasks.add_task(
        push_command_to_device, device.id, CommandOut.model_validate(command).model_dump()
    )
    return DeviceStateOut(
        device_id=device.id,
        desired_state=device.desired_state,
        actual_state=device.actual_state,
        is_locked_out=device.is_locked_out,
    )


@router.post("/devices/{device_id}/reactivate", response_model=DeviceStateOut)
def reactivate(
    background_tasks: BackgroundTasks,
    device: Device = Depends(get_authorized_device),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceStateOut:
    command, event = reactivate_device(db, device, current_user)
    background_tasks.add_task(notify_event_by_id, event.id)
    background_tasks.add_task(
        push_command_to_device, device.id, CommandOut.model_validate(command).model_dump()
    )
    return DeviceStateOut(
        device_id=device.id,
        desired_state=device.desired_state,
        actual_state=device.actual_state,
        is_locked_out=device.is_locked_out,
    )


@router.get("/notifications", response_model=list[NotificationOut])
def get_my_notifications(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.get("/notifications/preferences", response_model=list[NotificationPreferenceOut])
def get_my_notification_preferences(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict[str, bool | str]]:
    return get_notification_preferences(db, current_user.id)


@router.patch("/notifications/preferences", response_model=NotificationPreferenceOut)
def set_notification_preference(
    payload: NotificationPreferenceIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreference:
    preference = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == current_user.id,
            NotificationPreference.channel == payload.channel,
        )
        .first()
    )
    if preference is None:
        preference = NotificationPreference(user_id=current_user.id, channel=payload.channel)
        db.add(preference)

    preference.enabled = payload.enabled
    db.commit()
    db.refresh(preference)
    return preference
