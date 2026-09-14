from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_device
from app.core.logging_config import get_logger
from app.db import get_db
from app.models.entities import Command, Device, TelemetryReading
from app.schemas.iot import (
    CommandAckIn,
    CommandOut,
    DeviceStateOut,
    HeartbeatAck,
    TelemetryAck,
    TelemetryIn,
)

# Aprovisionamiento (dispositivo sin site_id -> vinculado a una cuenta): el
# endpoint que resuelve el vínculo vive en /api/v1/app/devices/claim, lo
# inicia el usuario desde la app (etapa 6) — no se duplica aquí. Este router
# asume que el dispositivo ya tiene credenciales emitidas (ver etapa 3
# app/services/device_auth.py, usado por el alta de dispositivo de la
# etapa 7); no expone ningún alta de dispositivo por sí mismo.
router = APIRouter(prefix="/api/v1/iot", tags=["IoT"])

logger = get_logger("voltguard.iot")


def evaluate_and_act(
    device: Device, reading: TelemetryReading, db: Session
) -> Command | None:
    """Punto de integración del motor de reglas de corte (etapa 5).

    Por ahora es un stub que no hace nada: esta etapa entrega el transporte
    de telemetría/comandos, no la decisión de seguridad.
    """
    return None


@router.post("/telemetry", response_model=TelemetryAck)
def receive_telemetry(
    payload: TelemetryIn,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> TelemetryAck:
    already_seen = (
        db.query(TelemetryReading)
        .filter(
            TelemetryReading.device_id == device.id,
            TelemetryReading.sequence == payload.sequence,
        )
        .first()
    )
    if already_seen is not None:
        # Idempotente: mismo sequence ya procesado no es un error, tampoco
        # se duplica el registro.
        return TelemetryAck(status="duplicate")

    last_sequence = (
        db.query(TelemetryReading.sequence)
        .filter(TelemetryReading.device_id == device.id)
        .order_by(TelemetryReading.sequence.desc())
        .limit(1)
        .scalar()
    )
    is_out_of_order = last_sequence is not None and payload.sequence < last_sequence
    if is_out_of_order:
        logger.warning(
            "telemetry_out_of_order",
            extra={
                "device_id": device.id,
                "sequence": payload.sequence,
                "last_sequence": last_sequence,
            },
        )

    reading = TelemetryReading(
        device_id=device.id,
        sequence=payload.sequence,
        voltage=payload.voltage_v,
        current=payload.current_a,
        power=payload.power_w,
        frequency=payload.frequency_hz,
        power_factor=payload.power_factor,
        energy=payload.energy_kwh,
        recorded_at=payload.timestamp,
    )
    db.add(reading)
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(reading)

    command = evaluate_and_act(device, reading, db)

    return TelemetryAck(
        status="success",
        is_out_of_order=is_out_of_order,
        command=CommandOut.model_validate(command) if command else None,
    )


@router.post("/heartbeat", response_model=HeartbeatAck)
def heartbeat(
    device: Device = Depends(get_current_device), db: Session = Depends(get_db)
) -> HeartbeatAck:
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    return HeartbeatAck()


@router.get("/commands/pending", response_model=list[CommandOut])
def list_pending_commands(
    device: Device = Depends(get_current_device), db: Session = Depends(get_db)
) -> list[Command]:
    return (
        db.query(Command)
        .filter(Command.device_id == device.id, Command.status == "PENDING")
        .order_by(Command.created_at.asc())
        .all()
    )


@router.post("/commands/{command_id}/ack", response_model=DeviceStateOut)
def ack_command(
    command_id: int,
    payload: CommandAckIn,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> DeviceStateOut:
    command = (
        db.query(Command)
        .filter(Command.id == command_id, Command.device_id == device.id)
        .first()
    )
    if command is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comando no encontrado para este dispositivo.",
        )

    command.status = "ACKED"
    command.acked_at = datetime.now(UTC)

    # El estado reportado se persiste tal cual, coincida o no con
    # desired_state — una orden enviada no demuestra que el relé haya
    # cambiado físicamente (ver Device.desired_state vs actual_state).
    device.actual_state = payload.actual_state
    db.commit()

    return DeviceStateOut(
        device_id=device.id,
        desired_state=device.desired_state,
        actual_state=device.actual_state,
    )
