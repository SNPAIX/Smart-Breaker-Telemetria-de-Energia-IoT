import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db import get_db
from app.models.entities import Alert, Device, Reading, SafetyEvent
from app.schemas.device import DeviceOut
from app.schemas.intelligence import (
    AlertOut,
    CostProjectionFactor,
    CostProjectionOut,
    SafetyEventOut,
    SafetyThresholdUpdate,
)
from app.schemas.telemetry import TelemetryReadingCreate, TelemetryResponse
from app.services.anomaly_detector import get_detector
from app.services.cost_projection import (
    DEFAULT_TARIFF_MXN_PER_KWH,
    project_monthly_cost,
)
from app.services.cutoff_rules import evaluate_cutoff

router = APIRouter(prefix="/api/v1/telemetry", tags=["Operative IoT"])
devices_router = APIRouter(prefix="/api/v1/devices", tags=["Devices - Safety & Intelligence"])

# Estrategia activa de detección: "rule_based" (sin IA, default) o
# "isolation_forest" (con IA). Configurable por variable de entorno para
# poder demostrar ambas versiones sin tocar código ni reiniciar servicios.
DETECTOR_STRATEGY = os.getenv("ANOMALY_DETECTOR", "rule_based")

logger = get_logger("voltguard.operative")


def _get_device_or_404(db: Session, device_id: str) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispositivo '{device_id}' no registrado.",
        )
    return device


@router.post("/readings", response_model=TelemetryResponse)
def receive_telemetry(
    payload: TelemetryReadingCreate, db: Session = Depends(get_db)
) -> TelemetryResponse:
    device = _get_device_or_404(db, payload.device_id)

    # 1. Motor de reglas de corte (RF-4): umbral absoluto de seguridad.
    # Se evalúa primero y de forma síncrona, antes que cualquier otra
    # lógica, para minimizar el tiempo de reacción de seguridad (<500ms).
    alert_msg = None
    cutoff = evaluate_cutoff(
        current_a=payload.current,
        max_current_a=device.max_current_threshold,
        auto_cutoff_enabled=device.auto_cutoff_enabled,
    )
    if cutoff.triggered:
        device.relay_status = False
        db.add(
            SafetyEvent(
                device_id=device.id,
                event_type="CRITICAL_OVERLOAD",
                current=cutoff.current_a,
                max_current_threshold=cutoff.max_current_a,
                action_taken="SHUTDOWN_ORDER_ISSUED",
            )
        )
        alert_msg = (
            f"SOBRECARGA DETECTADA: {payload.current}A excede el límite de "
            f"{device.max_current_threshold}A"
        )
        logger.warning(
            "safety_cutoff_triggered",
            extra={
                "device_id": device.id,
                "event_type": "CRITICAL_OVERLOAD",
                "current": cutoff.current_a,
                "max_current_threshold": cutoff.max_current_a,
                "action_taken": "SHUTDOWN_ORDER_ISSUED",
            },
        )

    # 2. Detector de anomalías (estadístico, relativo al historial del
    # propio dispositivo) — informativo, nunca corta la energía.
    history = [
        r.power
        for r in db.query(Reading)
        .filter(Reading.device_id == device.id)
        .order_by(Reading.recorded_at.desc())
        .limit(50)
        .all()
    ]
    detector = get_detector(DETECTOR_STRATEGY)
    result = detector.evaluate(history, payload.power)

    new_reading = Reading(
        device_id=payload.device_id,
        voltage=payload.voltage,
        current=payload.current,
        power=payload.power,
        frequency=payload.frequency,
        power_factor=payload.power_factor,
        energy=payload.energy,
    )
    db.add(new_reading)

    if result.is_anomaly:
        db.add(
            Alert(
                device_id=device.id,
                power=payload.power,
                expected_power=result.expected_power_w,
                detector=result.detector_name,
            )
        )
        logger.info(
            "anomaly_detected",
            extra={
                "device_id": device.id,
                "power": payload.power,
                "expected_power": result.expected_power_w,
                "detector": result.detector_name,
            },
        )

    db.commit()

    return TelemetryResponse(
        status="critical_overload" if cutoff.triggered else "success",
        relay_status=device.relay_status,
        alert=alert_msg,
    )


# --- Motor de reglas de corte: configuración y auditoría ---
@devices_router.patch(
    "/{device_id}/safety-threshold",
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
    "/safety-events/all",
    response_model=list[SafetyEventOut],
    summary="Listar todos los eventos de corte automático (CRITICAL_OVERLOAD)",
)
def list_all_safety_events(db: Session = Depends(get_db)) -> list[SafetyEvent]:
    return db.query(SafetyEvent).order_by(SafetyEvent.created_at.desc()).all()


@devices_router.get(
    "/{device_id}/safety-events",
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
    "/alerts/all",
    response_model=list[AlertOut],
    summary="Listar todas las alertas de anomalías",
)
def list_all_alerts(db: Session = Depends(get_db)) -> list[Alert]:
    return db.query(Alert).order_by(Alert.created_at.desc()).all()


@devices_router.get(
    "/{device_id}/alerts",
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
    "/{device_id}/cost-projection",
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
