"""Cálculo de costo real (no proyectado) a partir de consumo histórico y
tarifas vigentes por día — etapa 8."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.entities import Device
from app.services.cost_projection import DEFAULT_TARIFF_MXN_PER_KWH
from app.services.devices import compute_daily_consumption
from app.services.tariffs import get_active_tariff


@dataclass
class CostBreakdown:
    days_analyzed: int
    total_kwh: float
    total_cost: float
    currency: str
    used_default_tariff: bool


def compute_cost_breakdown(db: Session, device: Device, days: int = 14) -> CostBreakdown:
    """Precio de cada día analizado con la tarifa que estaba vigente ESE
    día (no la de hoy) — así, si la tarifa cambió a mitad del período, el
    costo total refleja el prorrateo real en vez de aplicar un solo precio
    a todo el rango."""
    _, dated_daily_wh = compute_daily_consumption(db, device.id, days=days)

    total_kwh = 0.0
    total_cost = 0.0
    currency = "MXN"
    used_default_tariff = False

    for date_str, wh in dated_daily_wh:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
        tariff = get_active_tariff(db, device.site_id, day) if device.site_id is not None else None

        if tariff is not None:
            price = tariff.price_per_kwh
            currency = tariff.currency
        else:
            price = DEFAULT_TARIFF_MXN_PER_KWH
            used_default_tariff = True

        kwh = wh / 1000.0
        total_kwh += kwh
        total_cost += kwh * price

    return CostBreakdown(
        days_analyzed=len(dated_daily_wh),
        total_kwh=round(total_kwh, 3),
        total_cost=round(total_cost, 2),
        currency=currency,
        used_default_tariff=used_default_tariff,
    )
