"""CRUD de usuarios para la superficie administrativa (etapa 7)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.entities import Device, Site, SiteMember, User


def create_user(db: Session, *, email: str, password: str, role: str = "user") -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado.",
        )
    user = User(email=email, hashed_password=get_password_hash(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return user


def update_user(
    db: Session, user: User, *, role: str | None = None, is_active: bool | None = None
) -> User:
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def list_sites_solely_owned_by(db: Session, user_id: int) -> list[Site]:
    """Sitios donde `user_id` es el único `owner` — borrarlo dejaría a ese
    sitio sin ningún dueño. No importa si hay otros `member`: la pregunta
    es específicamente por la propiedad (`role="owner"`), que es lo único
    que habilita borrar el sitio o administrar su membresía (ver
    `delete_site` / `SiteMember.role`).

    Se usa para avisar ANTES de borrar un usuario (`delete_user`), nunca
    para bloquear el borrado — el admin decide informado, no se le impide."""
    owner_counts: dict[int, int] = {
        site_id: count
        for site_id, count in db.query(SiteMember.site_id, func.count(SiteMember.id))
        .filter(SiteMember.role == "owner")
        .group_by(SiteMember.site_id)
        .all()
    }
    my_owned_site_ids = {
        row[0]
        for row in db.query(SiteMember.site_id)
        .filter(SiteMember.user_id == user_id, SiteMember.role == "owner")
        .all()
    }
    solely_owned_ids = {
        site_id for site_id in my_owned_site_ids if owner_counts.get(site_id) == 1
    }
    if not solely_owned_ids:
        return []
    return db.query(Site).filter(Site.id.in_(solely_owned_ids)).all()


def preview_user_deletion_impact(db: Session, user_id: int) -> list[dict[str, object]]:
    """Igual que `list_sites_solely_owned_by`, pero con el conteo de
    dispositivos de cada sitio — lo que la UI necesita mostrar en el aviso
    de confirmación antes de borrar (cuántos dispositivos quedarían
    huérfanos de sitio, no solo cuántos sitios)."""
    sites = list_sites_solely_owned_by(db, user_id)
    if not sites:
        return []
    device_counts: dict[int | None, int] = {
        site_id: count
        for site_id, count in db.query(Device.site_id, func.count(Device.id))
        .filter(Device.site_id.in_([site.id for site in sites]))
        .group_by(Device.site_id)
        .all()
    }
    return [
        {"id": site.id, "name": site.name, "device_count": device_counts.get(site.id, 0)}
        for site in sites
    ]


def delete_user(db: Session, user: User, *, delete_orphaned_sites: bool = False) -> None:
    """Borra al usuario. Si `delete_orphaned_sites` es True, primero borra
    (irreversiblemente) cada sitio del que este usuario es el único
    `owner`: sus dispositivos se desvinculan (`site_id = None`, quedan
    disponibles para vincularse a otro sitio después) en vez de borrarse
    ellos también — el hardware físico no desaparece porque su sitio en el
    sistema se haya borrado."""
    if delete_orphaned_sites:
        for site in list_sites_solely_owned_by(db, user.id):
            db.query(Device).filter(Device.site_id == site.id).update({"site_id": None})
            db.delete(site)  # cascada: SiteMember, Tariff (ver Site.members/tariffs)

    db.delete(user)  # cascada: site_memberships, notifications, notification_preferences
    db.commit()
