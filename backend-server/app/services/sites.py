"""Servicios de sitio compartidos entre `/api/v1/app` (etapa 6) y
`/api/v1/admin` (etapa 7)."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Device, Site, SiteMember, User


def list_user_sites(db: Session, user_id: int) -> list[Site]:
    return (
        db.query(Site)
        .join(SiteMember, SiteMember.site_id == Site.id)
        .filter(SiteMember.user_id == user_id)
        .all()
    )


def list_user_sites_with_role(db: Session, user_id: int) -> list[dict[str, object]]:
    """Igual que `list_user_sites`, pero con el rol propio (`owner` o
    `member`) y el correo del dueño real resueltos para cada sitio — "Mis
    sitios" necesita mostrar a primera vista si el usuario es dueño de ese
    sitio, o solo está ahí como invitado/soporte y de quién es en realidad
    (ver `admin_is_member` en la consola de admin, mismo concepto visto
    desde el otro lado: acá cada usuario ve su propio rol, no el de
    terceros)."""
    rows = (
        db.query(Site, SiteMember.role)
        .join(SiteMember, SiteMember.site_id == Site.id)
        .filter(SiteMember.user_id == user_id)
        .all()
    )
    if not rows:
        return []
    owner_emails: dict[int, str] = {
        site_id: email
        for site_id, email in db.query(SiteMember.site_id, User.email)
        .join(User, User.id == SiteMember.user_id)
        .filter(SiteMember.role == "owner", SiteMember.site_id.in_([site.id for site, _ in rows]))
        .all()
    }
    return [
        {
            "id": site.id,
            "name": site.name,
            "kind": site.kind,
            "my_role": role,
            "owner_email": owner_emails.get(site.id),
        }
        for site, role in rows
    ]


def list_site_devices(db: Session, site_id: int) -> list[Device]:
    return db.query(Device).filter(Device.site_id == site_id).all()


def list_user_devices(db: Session, user_id: int) -> list[Device]:
    """Todos los dispositivos visibles para un usuario, sin importar en
    cuál de sus sitios estén — lo usa el asistente de voz (etapa 14) para
    resolver un comando contra el universo completo de dispositivos del
    usuario, no solo los de un sitio puntual."""
    return (
        db.query(Device)
        .join(Site, Site.id == Device.site_id)
        .join(SiteMember, SiteMember.site_id == Site.id)
        .filter(SiteMember.user_id == user_id)
        .all()
    )


def create_site(db: Session, *, name: str, kind: str = "otro") -> Site:
    site = Site(name=name, kind=kind)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def list_all_sites(db: Session) -> list[Site]:
    return db.query(Site).order_by(Site.id.asc()).all()


def list_all_sites_with_owner(db: Session, *, admin_user_id: int) -> list[dict[str, object]]:
    """Igual que `list_all_sites`, pero con el correo del dueño (el
    `SiteMember` con `role="owner"`) resuelto para cada sitio — la consola
    de admin es una vista operativa de soporte sobre sitios de terceros,
    nunca "sus" sitios; sin esto, la tabla no tiene forma de distinguir de
    quién es cada uno. Un sitio sin dueño (caso raro, ej. datos de prueba)
    devuelve `owner_email=None` en vez de fallar.

    También marca `admin_is_member`: si el admin que pide la lista está
    vinculado a ese sitio en este momento (vía el botón de soporte
    temporal) — para que la tabla lo muestre sin tener que abrir cada fila
    una por una a ver si ahí sigue vinculado."""
    sites = list_all_sites(db)
    owner_emails: dict[int, str] = {
        site_id: email
        for site_id, email in db.query(SiteMember.site_id, User.email)
        .join(User, User.id == SiteMember.user_id)
        .filter(SiteMember.role == "owner")
        .all()
    }
    admin_site_ids: set[int] = {
        row[0]
        for row in db.query(SiteMember.site_id)
        .filter(SiteMember.user_id == admin_user_id)
        .all()
    }
    return [
        {
            "id": site.id,
            "name": site.name,
            "kind": site.kind,
            "owner_email": owner_emails.get(site.id),
            "admin_is_member": site.id in admin_site_ids,
        }
        for site in sites
    ]


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
            detail="El sitio tiene dispositivos asignados; deben reasignarse o desvincularse primero.",
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
