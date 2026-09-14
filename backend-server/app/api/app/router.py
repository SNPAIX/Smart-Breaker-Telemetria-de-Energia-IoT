from fastapi import APIRouter, Depends, HTTPException, status
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
    Site,
    SiteMember,
    TelemetryReading,
    User,
)
from app.schemas.app_api import (
    ClaimIn,
    DeviceCostOut,
    DeviceMetricsOut,
    DeviceOut,
    DevicePredictionOut,
    DeviceStateOut,
    EventOut,
    NotificationOut,
    NotificationPreferenceIn,
    NotificationPreferenceOut,
    SiteOut,
    SwitchIn,
    TelemetryOut,
)
from app.services.cost_projection import (
    DEFAULT_TARIFF_MXN_PER_KWH,
    project_monthly_cost,
)
from app.services.costs import compute_cost_breakdown
from app.services.devices import (
    claim_device,
    compute_daily_consumption_wh,
    list_device_events,
    list_recent_telemetry,
    reactivate_device,
    switch_device,
)
from app.services.sites import list_site_devices, list_user_sites

router = APIRouter(prefix="/api/v1/app", tags=["App (usuario final)"])


@router.get("/sites", response_model=list[SiteOut])
def get_my_sites(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Site]:
    return list_user_sites(db, current_user.id)


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
            status_code=status.HTTP_403_FORBIDDEN, detail="No perteneces a este sitio."
        )

    device = db.query(Device).filter(Device.public_id == payload.public_id).first()
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado."
        )

    return claim_device(db, device, payload.site_id)


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


@router.get("/devices/{device_id}/prediction", response_model=DevicePredictionOut)
def get_device_prediction(
    device: Device = Depends(get_authorized_device), db: Session = Depends(get_db)
) -> DevicePredictionOut:
    _, daily_wh = compute_daily_consumption_wh(db, device.id)
    result = project_monthly_cost(daily_wh, DEFAULT_TARIFF_MXN_PER_KWH)
    return DevicePredictionOut(
        device_id=device.id,
        projected_monthly_kwh=result.projected_monthly_kwh,
        trend_wh_per_day=result.trend_wh_per_day,
        is_trending_up=result.is_trending_up,
    )


@router.post("/devices/{device_id}/switch", response_model=DeviceStateOut)
def switch(
    payload: SwitchIn,
    device: Device = Depends(get_authorized_device),
    db: Session = Depends(get_db),
) -> DeviceStateOut:
    switch_device(db, device, payload.desired_state)
    return DeviceStateOut(
        device_id=device.id,
        desired_state=device.desired_state,
        actual_state=device.actual_state,
        is_locked_out=device.is_locked_out,
    )


@router.post("/devices/{device_id}/reactivate", response_model=DeviceStateOut)
def reactivate(
    device: Device = Depends(get_authorized_device),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceStateOut:
    reactivate_device(db, device, current_user)
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
