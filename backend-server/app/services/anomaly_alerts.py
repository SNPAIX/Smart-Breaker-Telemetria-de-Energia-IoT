"""Conecta `app/services/anomaly_detector.py` (puro, sin ORM) al modelo v2:
lee el historial reciente de `TelemetryReading` y persiste `AnomalyAlert`
cuando corresponde. Independiente del motor de reglas de corte (etapa 5)
— una anomalía nunca corta la energía por sí sola."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import AnomalyAlert, Device, TelemetryReading
from app.services.anomaly_detector import get_detector


def evaluate_and_record_anomaly(
    db: Session, device: Device, reading: TelemetryReading
) -> AnomalyAlert | None:
    history = [
        r.power
        for r in db.query(TelemetryReading)
        .filter(TelemetryReading.device_id == device.id, TelemetryReading.id != reading.id)
        .order_by(TelemetryReading.recorded_at.desc())
        .limit(50)
        .all()
    ]

    detector = get_detector(settings.anomaly_detector)
    result = detector.evaluate(history, reading.power)
    if not result.is_anomaly:
        return None

    alert = AnomalyAlert(
        device_id=device.id,
        power=reading.power,
        expected_power=result.expected_power_w,
        detector=result.detector_name,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
