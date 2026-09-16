"""CRUD de `Tariff` (etapa 8). Conserva histórico: crear una tarifa nueva
cierra (`valid_to`) la anterior en vez de sobrescribirla, para poder
prorratear el costo cuando el precio cambió a mitad de un período."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import Tariff


def create_tariff(
    db: Session,
    *,
    site_id: int,
    price_per_kwh: float,
    currency: str = "MXN",
    valid_from: datetime | None = None,
) -> Tariff:
    effective_from = valid_from or datetime.now(UTC)

    open_tariff = (
        db.query(Tariff)
        .filter(Tariff.site_id == site_id, Tariff.valid_to.is_(None))
        .first()
    )
    if open_tariff is not None:
        open_tariff.valid_to = effective_from

    tariff = Tariff(
        site_id=site_id, currency=currency, price_per_kwh=price_per_kwh, valid_from=effective_from
    )
    db.add(tariff)
    db.commit()
    db.refresh(tariff)
    return tariff


def list_tariffs(db: Session, site_id: int) -> list[Tariff]:
    return (
        db.query(Tariff)
        .filter(Tariff.site_id == site_id)
        .order_by(Tariff.valid_from.desc())
        .all()
    )


def get_active_tariff(db: Session, site_id: int, at: datetime) -> Tariff | None:
    return (
        db.query(Tariff)
        .filter(
            Tariff.site_id == site_id,
            Tariff.valid_from <= at,
            or_(Tariff.valid_to.is_(None), Tariff.valid_to > at),
        )
        .order_by(Tariff.valid_from.desc())
        .first()
    )
