from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_device
from app.core.logging_config import get_logger
from app.db import get_db
from app.models.entities import Command, Device, Event, TelemetryReading
from app.schemas.iot import (
    CommandAckIn,
    CommandOut,
    DeviceStateOut,
    HeartbeatAck,
    TelemetryAck,
    TelemetryIn,
)
from app.services.cutoff_rules import evaluate_cutoff
from app.services.voltage_rules import evaluate_voltage

# Aprovisionamiento (dispositivo sin site_id -> vinculado a una cuenta): el
# endpoint que resuelve el vínculo vive en /api/v1/app/devices/claim, lo
# inicia el usuario desde la app (etapa 6) — no se duplica aquí. Este router
# asume que el dispositivo ya tiene credenciales emitidas (ver etapa 3
# app/services/device_auth.py, usado por el alta de dispositivo de la
# etapa 7); no expone ningún alta de dispositivo por sí mismo.
router = APIRouter(prefix="/api/v1/iot", tags=["IoT"])

logger = get_logger("voltguard.iot")


def evaluate_and_act(
    device: Device, reading: TelemetryReading, db: Session, received_at: datetime
) -> Command | None:
    """Motor de reglas de corte (RF-4): evalúa la lectura contra el perfil
    del dispositivo y, si es peligrosa, crea el Event/Command de apagado en
    la misma transacción síncrona (sin colas ni jobs async) para cumplir la
    métrica de reacción <500ms de la propuesta.

    Si el dispositivo ya está bloqueado por un evento crítico anterior
    (`is_locked_out`), no genera un evento/comando nuevo por cada lectura
    repetida en la misma condición — la reactivación es explícita y llega
    en la etapa 6, nunca automática desde este flujo.
    """
    if device.is_locked_out or device.profile is None:
        return None

    cutoff = evaluate_cutoff(
        current_a=reading.current,
        max_current_a=device.profile.max_current_a,
        auto_cutoff_enabled=device.profile.auto_cutoff_enabled,
    )
    voltage = evaluate_voltage(
        voltage_v=reading.voltage,
        min_voltage_v=device.profile.min_voltage_v,
        max_voltage_v=device.profile.max_voltage_v,
    )

    if cutoff.triggered:
        event_type = "CRITICAL_OVERLOAD"
        payload: dict[str, float | None] = {
            "current_a": cutoff.current_a,
            "max_current_a": cutoff.max_current_a,
        }
    elif voltage.triggered:
        event_type = f"CRITICAL_{voltage.reason}"
        payload = {
            "voltage_v": voltage.voltage_v,
            "min_voltage_v": voltage.min_voltage_v,
            "max_voltage_v": voltage.max_voltage_v,
        }
    else:
        return None

    db.add(Event(device_id=device.id, type=event_type, payload=payload))
    command = Command(device_id=device.id, type="SET_RELAY_OFF", status="PENDING")
    db.add(command)
    device.desired_state = "OFF"
    device.is_locked_out = True
    db.commit()
    db.refresh(command)

    reaction_ms = (datetime.now(UTC) - received_at).total_seconds() * 1000
    logger.warning(
        "critical_event_triggered",
        extra={
            "device_id": device.id,
            "event_type": event_type,
            "command_id": command.id,
            "reaction_ms": round(reaction_ms, 2),
        },
    )
    return command


@router.post("/telemetry", response_model=TelemetryAck)
def receive_telemetry(
    payload: TelemetryIn,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
) -> TelemetryAck:
    received_at = datetime.now(UTC)
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

    command = evaluate_and_act(device, reading, db, received_at)

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
