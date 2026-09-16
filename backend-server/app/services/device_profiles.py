"""CRUD de `DeviceProfile` para la superficie administrativa (etapa 7)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Device, DeviceProfile


def create_profile(
    db: Session,
    *,
    name: str,
    site_id: int | None = None,
    max_current_a: float = 15.0,
    min_voltage_v: float | None = None,
    max_voltage_v: float | None = None,
    auto_cutoff_enabled: bool = True,
) -> DeviceProfile:
    profile = DeviceProfile(
        name=name,
        site_id=site_id,
        max_current_a=max_current_a,
        min_voltage_v=min_voltage_v,
        max_voltage_v=max_voltage_v,
        auto_cutoff_enabled=auto_cutoff_enabled,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_profiles(db: Session, *, site_id: int | None = None) -> list[DeviceProfile]:
    query = db.query(DeviceProfile)
    if site_id is not None:
        query = query.filter(DeviceProfile.site_id == site_id)
    return query.order_by(DeviceProfile.id.asc()).all()


def get_profile_or_404(db: Session, profile_id: int) -> DeviceProfile:
    profile = db.query(DeviceProfile).filter(DeviceProfile.id == profile_id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado.")
    return profile


def update_profile(
    db: Session,
    profile: DeviceProfile,
    *,
    max_current_a: float | None = None,
    min_voltage_v: float | None = None,
    max_voltage_v: float | None = None,
    auto_cutoff_enabled: bool | None = None,
) -> DeviceProfile:
    if max_current_a is not None:
        profile.max_current_a = max_current_a
    if min_voltage_v is not None:
        profile.min_voltage_v = min_voltage_v
    if max_voltage_v is not None:
        profile.max_voltage_v = max_voltage_v
    if auto_cutoff_enabled is not None:
        profile.auto_cutoff_enabled = auto_cutoff_enabled
    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile: DeviceProfile) -> None:
    in_use = db.query(Device).filter(Device.profile_id == profile.id).first()
    if in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El perfil está en uso por al menos un dispositivo; reasígnalo primero.",
        )
    db.delete(profile)
    db.commit()
