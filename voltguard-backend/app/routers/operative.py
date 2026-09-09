from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.entities import Device, Reading
from app.schemas.telemetry import TelemetryReadingCreate, TelemetryResponse

router = APIRouter(prefix="/api/v1/telemetry", tags=["Operative IoT"])


@router.post("/readings", response_model=TelemetryResponse)
def receive_telemetry(payload: TelemetryReadingCreate, db: Session = Depends(get_db)):
    # 1. Verificar si el dispositivo existe
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispositivo '{payload.device_id}' no registrado."
        )

    # 2. Guardar la lectura en PostgreSQL
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

    # 3. Evaluar el motor de reglas (Sobrecarga de corriente)
    relay_order = device.relay_status
    alert_msg = None

    if payload.current > device.max_current_threshold:
        relay_order = False
        device.relay_status = False  # Actualizar estado en BD
        alert_msg = f"SOBRECARGA DETECTADA: {payload.current}A excede el límite de {device.max_current_threshold}A"

    db.commit()

    return TelemetryResponse(
        status="critical_overload" if not relay_order else "success",
        relay_status=relay_order,
        alert=alert_msg,
    )