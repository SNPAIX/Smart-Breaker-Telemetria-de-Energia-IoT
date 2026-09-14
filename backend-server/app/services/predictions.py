"""Proyección de consumo/costo mensual persistida (etapa 9).

Se genera de forma perezosa: si ya existe una `Prediction` reciente para el
dispositivo (dentro de `max_age_hours`), se reutiliza en vez de recalcular
— evita montar un scheduler/worker separado solo para esto, que sería
sobre-ingeniería para el tamaño de este MVP.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.entities import Device, Prediction
from app.services.cost_projection import (
    DEFAULT_TARIFF_MXN_PER_KWH,
    project_monthly_cost,
)
from app.services.devices import compute_daily_consumption_wh

PREDICTION_METHOD = "linear_trend_v1"


def get_or_generate_prediction(
    db: Session, device: Device, *, max_age_hours: int = 24
) -> Prediction:
    latest = (
        db.query(Prediction)
        .filter(Prediction.device_id == device.id, Prediction.horizon == "monthly")
        .order_by(Prediction.generated_at.desc())
        .first()
    )
    if latest is not None and (datetime.now(UTC) - latest.generated_at) < timedelta(
        hours=max_age_hours
    ):
        return latest

    _, daily_wh = compute_daily_consumption_wh(db, device.id)
    result = project_monthly_cost(daily_wh, DEFAULT_TARIFF_MXN_PER_KWH)

    prediction = Prediction(
        device_id=device.id,
        horizon="monthly",
        projected_kwh=result.projected_monthly_kwh,
        projected_cost=result.projected_monthly_cost_mxn,
        method=PREDICTION_METHOD,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
