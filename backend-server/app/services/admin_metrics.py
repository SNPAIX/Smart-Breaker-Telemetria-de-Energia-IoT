"""Métricas globales y agrupadas para el dashboard administrativo (etapa 7).

"Online" nunca se guarda como columna — se calcula comparando
`last_seen_at` contra `settings.device_online_threshold_seconds` en el
momento de la consulta (ver `app/services/devices.py::is_device_online`),
para no tener un campo booleano que alguien tenga que mantener sincronizado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.entities import Device, DeviceProfile, Event, Site, User
from app.services.devices import is_device_online


@dataclass
class GlobalMetrics:
    total_sites: int
    total_users: int
    total_devices: int
    devices_online: int
    devices_offline: int
    critical_events_last_24h: int


@dataclass
class SiteMetrics:
    site_id: int
    site_name: str
    device_count: int
    devices_online: int


@dataclass
class ProfileMetrics:
    profile_id: int
    profile_name: str
    device_count: int


@dataclass
class AdminOverview:
    global_metrics: GlobalMetrics
    by_site: list[SiteMetrics] = field(default_factory=list)
    by_profile: list[ProfileMetrics] = field(default_factory=list)


def global_metrics(db: Session) -> GlobalMetrics:
    devices = db.query(Device).all()
    online_count = sum(1 for d in devices if is_device_online(d))
    since = datetime.now(UTC) - timedelta(hours=24)
    critical_events = (
        db.query(Event)
        .filter(Event.type.like("CRITICAL_%"), Event.created_at >= since)
        .count()
    )

    return GlobalMetrics(
        total_sites=db.query(Site).count(),
        total_users=db.query(User).count(),
        total_devices=len(devices),
        devices_online=online_count,
        devices_offline=len(devices) - online_count,
        critical_events_last_24h=critical_events,
    )


def metrics_by_site(db: Session) -> list[SiteMetrics]:
    result = []
    for site in db.query(Site).order_by(Site.id.asc()).all():
        devices = db.query(Device).filter(Device.site_id == site.id).all()
        result.append(
            SiteMetrics(
                site_id=site.id,
                site_name=site.name,
                device_count=len(devices),
                devices_online=sum(1 for d in devices if is_device_online(d)),
            )
        )
    return result


def metrics_by_profile(db: Session) -> list[ProfileMetrics]:
    result = []
    for profile in db.query(DeviceProfile).order_by(DeviceProfile.id.asc()).all():
        device_count = db.query(Device).filter(Device.profile_id == profile.id).count()
        result.append(
            ProfileMetrics(profile_id=profile.id, profile_name=profile.name, device_count=device_count)
        )
    return result


def overview(db: Session) -> AdminOverview:
    return AdminOverview(
        global_metrics=global_metrics(db),
        by_site=metrics_by_site(db),
        by_profile=metrics_by_profile(db),
    )
