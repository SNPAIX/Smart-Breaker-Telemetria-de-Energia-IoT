"""Servicios de sitio compartidos entre `/api/v1/app` (etapa 6) y
`/api/v1/admin` (etapa 7)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entities import Device, Site, SiteMember


def list_user_sites(db: Session, user_id: int) -> list[Site]:
    return (
        db.query(Site)
        .join(SiteMember, SiteMember.site_id == Site.id)
        .filter(SiteMember.user_id == user_id)
        .all()
    )


def list_site_devices(db: Session, site_id: int) -> list[Device]:
    return db.query(Device).filter(Device.site_id == site_id).all()
