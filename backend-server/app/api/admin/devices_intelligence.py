from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.iot.router import _get_device_or_404
from app.core.dependencies import get_current_admin
from app.db import get_db
from app.models.entities import Alert, Reading, SafetyEvent
from app.schemas.device import DeviceOut
from app.schemas.intelligence import (
    AlertOut,
    CostProjectionFactor,
    CostProjectionOut,
    SafetyEventOut,
    SafetyThresholdUpdate,
)
from app.services.cost_projection import (
    DEFAULT_TARIFF_MXN_PER_KWH,
    project_monthly_cost,
)

devices_router = APIRouter(
    prefix="/api/v1/dispositivos",
    tags=["Devices - Safety & Intelligence"],
    dependencies=[Depends(get_current_admin)],  # Protege TODAS las rutas de este router
)


# --- Motor de reglas de corte: configuración y auditoría ---
@devices_router.patch(
    "/{device_id}/umbral-seguridad",
    response_model=DeviceOut,
    summary="Configurar el umbral de corte automático (RF-4)",
)
def update_safety_threshold(
    device_id: str, payload: SafetyThresholdUpdate, db: Session = Depends(get_db)
) -> DeviceOut:
    device = _get_device_or_404(db, device_id)
    device.max_current_threshold = payload.max_current_threshold
    device.auto_cutoff_enabled = payload.auto_cutoff_enabled
    db.commit()
    db.refresh(device)
    return DeviceOut.model_validate(device)


@devices_router.get(
    "/eventos-seguridad/todos",
    response_model=list[SafetyEventOut],
    summary="Listar todos los eventos de corte automático (CRITICAL_OVERLOAD)",
)
def list_all_safety_events(db: Session = Depends(get_db)) -> list[SafetyEvent]:
    return db.query(SafetyEvent).order_by(SafetyEvent.created_at.desc()).all()


@devices_router.get(
    "/{device_id}/eventos-seguridad",
    response_model=list[SafetyEventOut],
    summary="Listar eventos de corte automático de un dispositivo",
)
def list_device_safety_events(device_id: str, db: Session = Depends(get_db)) -> list[SafetyEvent]:
    _get_device_or_404(db, device_id)
    return (
        db.query(SafetyEvent)
        .filter(SafetyEvent.device_id == device_id)
        .order_by(SafetyEvent.created_at.desc())
        .all()
    )


# --- Detector de anomalías: consulta de alertas generadas ---
@devices_router.get(
    "/alertas/todas",
    response_model=list[AlertOut],
    summary="Listar todas las alertas de anomalías",
)
def list_all_alerts(db: Session = Depends(get_db)) -> list[Alert]:
    return db.query(Alert).order_by(Alert.created_at.desc()).all()


@devices_router.get(
    "/{device_id}/alertas",
    response_model=list[AlertOut],
    summary="Listar alertas de anomalías de un dispositivo",
)
def list_device_alerts(device_id: str, db: Session = Depends(get_db)) -> list[Alert]:
    _get_device_or_404(db, device_id)
    return (
        db.query(Alert)
        .filter(Alert.device_id == device_id)
        .order_by(Alert.created_at.desc())
        .all()
    )


# --- Proyección de costo mensual (inferencia de IA de apoyo) ---
@devices_router.get(
    "/{device_id}/proyeccion-costo",
    response_model=CostProjectionOut,
    summary="Proyección de consumo y costo mensual",
)
def get_cost_projection(
    device_id: str,
    days: int = 14,
    tariff_mxn_per_kwh: float = DEFAULT_TARIFF_MXN_PER_KWH,
    db: Session = Depends(get_db),
) -> CostProjectionOut:
    _get_device_or_404(db, device_id)

    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    readings = (
        db.query(Reading)
        .filter(Reading.device_id == device_id, Reading.recorded_at >= start)
        .order_by(Reading.recorded_at.asc())
        .all()
    )

    buckets: dict[str, list[Reading]] = defaultdict(list)
    for reading in readings:
        buckets[reading.recorded_at.strftime("%Y-%m-%d")].append(reading)

    # `energy` es la lectura acumulada del medidor en kWh (nunca se resetea
    # sola), no el consumo del día. El consumo diario real es la diferencia
    # entre el máximo acumulado de un día y el del día anterior. El primer
    # día del rango se descarta porque no hay línea base previa.
    daily_energy_kwh = [max(r.energy for r in buckets[day]) for day in sorted(buckets)]
    daily_consumption_wh = [
        max(0.0, (current - previous) * 1000.0)
        for previous, current in pairwise(daily_energy_kwh)
    ]

    result = project_monthly_cost(daily_consumption_wh, tariff_mxn_per_kwh)

    return CostProjectionOut(
        device_id=device_id,
        days_analyzed=result.days_analyzed,
        avg_daily_energy_wh=result.avg_daily_energy_wh,
        trend_wh_per_day=result.trend_wh_per_day,
        projected_monthly_kwh=result.projected_monthly_kwh,
        tariff_mxn_per_kwh=result.tariff_mxn_per_kwh,
        projected_monthly_cost_mxn=result.projected_monthly_cost_mxn,
        is_trending_up=result.is_trending_up,
        percent_change_vs_previous_period=result.percent_change_vs_previous_period,
        factors=[CostProjectionFactor(**f) for f in result.factors],
    )
