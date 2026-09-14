from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging_config import get_logger
from app.db import get_db
from app.models.entities import Alert, Device, Reading, SafetyEvent
from app.schemas.telemetry import TelemetryReadingCreate, TelemetryResponse
from app.services.anomaly_detector import get_detector
from app.services.cutoff_rules import evaluate_cutoff

router = APIRouter(prefix="/api/v1/telemetry", tags=["Operative IoT"])

logger = get_logger("voltguard.iot")


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
    """Endpoint heredado del repo base, reubicado tal cual bajo app/api/iot/.

    Sin autenticación de dispositivo todavía (brecha conocida, ver
    roadmap/01-gap-analysis.md) — la etapa 4 lo reemplaza por la superficie
    /api/v1/iot/* real con DeviceCredential. Esta etapa 1 solo reorganiza
    routers/ en api/{iot,app,admin}, no cambia comportamiento.
    """
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
    detector = get_detector(settings.anomaly_detector)
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
