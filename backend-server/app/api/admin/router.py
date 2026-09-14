from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.db import get_db
from app.models.entities import (
    AnomalyAlert,
    Device,
    DeviceProfile,
    Event,
    Site,
    Tariff,
    User,
)
from app.schemas.admin_api import (
    AdminEventOut,
    AdminOverviewOut,
    DeviceCreateIn,
    DeviceCreateOut,
    DeviceReassignIn,
    DeviceUpdateIn,
    GlobalMetricsOut,
    ProfileCreateIn,
    ProfileMetricsOut,
    ProfileOut,
    ProfileUpdateIn,
    SiteCreateIn,
    SiteMetricsOut,
    SiteUpdateIn,
    TariffCreateIn,
    TariffOut,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)
from app.schemas.app_api import DeviceOut, SiteOut
from app.services.admin_metrics import (
    global_metrics,
    metrics_by_profile,
    metrics_by_site,
    overview,
)
from app.services.device_profiles import (
    create_profile,
    delete_profile,
    get_profile_or_404,
    list_profiles,
    update_profile,
)
from app.services.devices import (
    admin_reassign_device,
    create_device,
    delete_device,
    get_device_or_404,
    list_all_devices,
    list_events,
    update_device,
)
from app.services.sites import (
    create_site,
    delete_site,
    get_site_or_404,
    list_all_sites,
    update_site,
)
from app.services.tariffs import create_tariff, list_tariffs
from app.services.users import (
    create_user,
    delete_user,
    get_user_or_404,
    list_users,
    update_user,
)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin & Dashboard"],
    dependencies=[Depends(get_current_admin)],
)


# --- Usuarios ---
@router.post("/users", response_model=UserOut, status_code=201)
def admin_create_user(payload: UserCreateIn, db: Session = Depends(get_db)) -> User:
    return create_user(db, email=payload.email, password=payload.password, role=payload.role)


@router.get("/users", response_model=list[UserOut])
def admin_list_users(db: Session = Depends(get_db)) -> list[User]:
    return list_users(db)


@router.get("/users/{user_id}", response_model=UserOut)
def admin_get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    return get_user_or_404(db, user_id)


@router.patch("/users/{user_id}", response_model=UserOut)
def admin_update_user(user_id: int, payload: UserUpdateIn, db: Session = Depends(get_db)) -> User:
    user = get_user_or_404(db, user_id)
    return update_user(db, user, role=payload.role, is_active=payload.is_active)


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    delete_user(db, get_user_or_404(db, user_id))


# --- Sitios ---
@router.post("/sites", response_model=SiteOut, status_code=201)
def admin_create_site(payload: SiteCreateIn, db: Session = Depends(get_db)) -> Site:
    return create_site(db, name=payload.name, kind=payload.kind)


@router.get("/sites", response_model=list[SiteOut])
def admin_list_sites(db: Session = Depends(get_db)) -> list[Site]:
    return list_all_sites(db)


@router.get("/sites/{site_id}", response_model=SiteOut)
def admin_get_site(site_id: int, db: Session = Depends(get_db)) -> Site:
    return get_site_or_404(db, site_id)


@router.patch("/sites/{site_id}", response_model=SiteOut)
def admin_update_site(site_id: int, payload: SiteUpdateIn, db: Session = Depends(get_db)) -> Site:
    site = get_site_or_404(db, site_id)
    return update_site(db, site, name=payload.name, kind=payload.kind)


@router.delete("/sites/{site_id}", status_code=204)
def admin_delete_site(site_id: int, db: Session = Depends(get_db)) -> None:
    delete_site(db, get_site_or_404(db, site_id))


@router.post("/sites/{site_id}/tariffs", response_model=TariffOut, status_code=201)
def admin_create_tariff(
    site_id: int, payload: TariffCreateIn, db: Session = Depends(get_db)
) -> Tariff:
    get_site_or_404(db, site_id)  # 404 antes de crear si el sitio no existe
    return create_tariff(
        db, site_id=site_id, price_per_kwh=payload.price_per_kwh, currency=payload.currency
    )


@router.get("/sites/{site_id}/tariffs", response_model=list[TariffOut])
def admin_list_tariffs(site_id: int, db: Session = Depends(get_db)) -> list[Tariff]:
    get_site_or_404(db, site_id)
    return list_tariffs(db, site_id)


# --- Dispositivos ---
@router.post("/devices", response_model=DeviceCreateOut, status_code=201)
def admin_create_device(payload: DeviceCreateIn, db: Session = Depends(get_db)) -> DeviceCreateOut:
    device, secret = create_device(
        db,
        public_id=payload.public_id,
        name=payload.name,
        site_id=payload.site_id,
        profile_id=payload.profile_id,
    )
    return DeviceCreateOut(
        id=device.id,
        public_id=device.public_id,
        name=device.name,
        site_id=device.site_id,
        profile_id=device.profile_id,
        secret=secret,
    )


@router.get("/devices", response_model=list[DeviceOut])
def admin_list_devices(site_id: int | None = None, db: Session = Depends(get_db)) -> list[Device]:
    return list_all_devices(db, site_id=site_id)


@router.get("/devices/{device_id}", response_model=DeviceOut)
def admin_get_device(device_id: int, db: Session = Depends(get_db)) -> Device:
    return get_device_or_404(db, device_id)


@router.patch("/devices/{device_id}", response_model=DeviceOut)
def admin_update_device(
    device_id: int, payload: DeviceUpdateIn, db: Session = Depends(get_db)
) -> Device:
    device = get_device_or_404(db, device_id)
    return update_device(db, device, name=payload.name, profile_id=payload.profile_id)


@router.post("/devices/{device_id}/reassign", response_model=DeviceOut)
def admin_reassign(
    device_id: int, payload: DeviceReassignIn, db: Session = Depends(get_db)
) -> Device:
    device = get_device_or_404(db, device_id)
    return admin_reassign_device(db, device, payload.site_id)


@router.delete("/devices/{device_id}", status_code=204)
def admin_delete_device(device_id: int, db: Session = Depends(get_db)) -> None:
    delete_device(db, get_device_or_404(db, device_id))


# --- Perfiles de dispositivo ---
@router.post("/profiles", response_model=ProfileOut, status_code=201)
def admin_create_profile(payload: ProfileCreateIn, db: Session = Depends(get_db)) -> DeviceProfile:
    return create_profile(
        db,
        name=payload.name,
        site_id=payload.site_id,
        max_current_a=payload.max_current_a,
        min_voltage_v=payload.min_voltage_v,
        max_voltage_v=payload.max_voltage_v,
        auto_cutoff_enabled=payload.auto_cutoff_enabled,
    )


@router.get("/profiles", response_model=list[ProfileOut])
def admin_list_profiles(
    site_id: int | None = None, db: Session = Depends(get_db)
) -> list[DeviceProfile]:
    return list_profiles(db, site_id=site_id)


@router.get("/profiles/{profile_id}", response_model=ProfileOut)
def admin_get_profile(profile_id: int, db: Session = Depends(get_db)) -> DeviceProfile:
    return get_profile_or_404(db, profile_id)


@router.patch("/profiles/{profile_id}", response_model=ProfileOut)
def admin_update_profile(
    profile_id: int, payload: ProfileUpdateIn, db: Session = Depends(get_db)
) -> DeviceProfile:
    profile = get_profile_or_404(db, profile_id)
    return update_profile(
        db,
        profile,
        max_current_a=payload.max_current_a,
        min_voltage_v=payload.min_voltage_v,
        max_voltage_v=payload.max_voltage_v,
        auto_cutoff_enabled=payload.auto_cutoff_enabled,
    )


@router.delete("/profiles/{profile_id}", status_code=204)
def admin_delete_profile(profile_id: int, db: Session = Depends(get_db)) -> None:
    delete_profile(db, get_profile_or_404(db, profile_id))


# --- Eventos y anomalías ---
@router.get("/events", response_model=list[AdminEventOut])
def admin_list_events(
    device_id: int | None = None,
    type: str | None = None,
    db: Session = Depends(get_db),
) -> list[Event]:
    return list_events(db, device_id=device_id, event_type=type)


@router.get("/anomalies")
def admin_list_anomalies(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    """Mínimo viable: la etapa 9 es la que puebla `AnomalyAlert` de verdad."""
    alerts = db.query(AnomalyAlert).order_by(AnomalyAlert.created_at.desc()).limit(100).all()
    return [
        {
            "id": a.id,
            "device_id": a.device_id,
            "power": a.power,
            "expected_power": a.expected_power,
            "detector": a.detector,
            "acknowledged": a.acknowledged,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


# --- Dashboard ---
@router.get("/dashboard/metrics", response_model=GlobalMetricsOut)
def admin_dashboard_metrics(db: Session = Depends(get_db)) -> GlobalMetricsOut:
    return GlobalMetricsOut.model_validate(global_metrics(db))


@router.get("/dashboard/by-site", response_model=list[SiteMetricsOut])
def admin_dashboard_by_site(db: Session = Depends(get_db)) -> list[SiteMetricsOut]:
    return [SiteMetricsOut.model_validate(m) for m in metrics_by_site(db)]


@router.get("/dashboard/by-profile", response_model=list[ProfileMetricsOut])
def admin_dashboard_by_profile(db: Session = Depends(get_db)) -> list[ProfileMetricsOut]:
    return [ProfileMetricsOut.model_validate(m) for m in metrics_by_profile(db)]


@router.get("/dashboard/overview", response_model=AdminOverviewOut)
def admin_dashboard_overview(db: Session = Depends(get_db)) -> AdminOverviewOut:
    return AdminOverviewOut.model_validate(overview(db))
