"""Servicios de sitio compartidos entre `/api/v1/app` (etapa 6) y
`/api/v1/admin` (etapa 7)."""
from __future__ import annotations

from fastapi import HTTPException, status
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


def create_site(db: Session, *, name: str, kind: str = "otro") -> Site:
    site = Site(name=name, kind=kind)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def list_all_sites(db: Session) -> list[Site]:
    return db.query(Site).order_by(Site.id.asc()).all()


def get_site_or_404(db: Session, site_id: int) -> Site:
    site = db.query(Site).filter(Site.id == site_id).first()
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sitio no encontrado.")
    return site


def update_site(db: Session, site: Site, *, name: str | None = None, kind: str | None = None) -> Site:
    if name is not None:
        site.name = name
    if kind is not None:
        site.kind = kind
    db.commit()
    db.refresh(site)
    return site


def delete_site(db: Session, site: Site) -> None:
    """No se permite borrar un sitio con dispositivos todavía asignados —
    a diferencia de `SiteMember` (que sí cascada), un `Device` no debe
    desvincularse silenciosamente solo porque se borró su sitio."""
    if list_site_devices(db, site.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El sitio tiene dispositivos asignados; reasígnalos o desvincúlalos primero.",
        )
    db.delete(site)  # cascada: SiteMember, Tariff
    db.commit()


def list_site_members(db: Session, site_id: int) -> list[SiteMember]:
    return db.query(SiteMember).filter(SiteMember.site_id == site_id).all()


def add_site_member(db: Session, site_id: int, user_id: int, role: str = "member") -> SiteMember:
    existing = (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id, SiteMember.user_id == user_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya pertenece a este sitio.",
        )
    member = SiteMember(site_id=site_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_site_member(db: Session, site_id: int, user_id: int) -> None:
    member = (
        db.query(SiteMember)
        .filter(SiteMember.site_id == site_id, SiteMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="El usuario no pertenece a este sitio."
        )
    db.delete(member)
    db.commit()
