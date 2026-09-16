"""Canal WebSocket del propio dispositivo (distinto del de usuarios en
`app/api/app/ws.py`): el ESP32 abre una conexión persistente acá al
arrancar y el backend le empuja cada comando nuevo al instante, en vez de
que el dispositivo tenga que esperar a su próxima lectura de telemetría o
al poll de respaldo cada 3s (`GET /commands/pending`, que sigue existiendo
tal cual — este canal es un acelerador, nunca el único camino).

Autenticación: mismo esquema que el resto de `/api/v1/iot/*`
(`Authorization: Device <public_id>:<secret>`), leído del header del
handshake WebSocket — reusa `authenticate_device_credential` para no
duplicar la verificación.

Robustez explícitamente considerada:
- Reconexión: el dispositivo reintenta solo (`setReconnectInterval` del
  lado del firmware); acá no hace falta ningún estado de sesión entre
  conexiones porque cada reconexión hace catch-up de comandos pendientes.
- Pérdida del mensaje empujado (el socket se cae justo cuando se manda):
  `send_to_device` no lanza si falla, y el comando sigue `PENDING` en la
  base — lo recoge el poll HTTP de respaldo o el catch-up de la próxima
  reconexión, nunca se pierde de verdad.
- Condición de carrera con la entrega por poll/telemetría: no hace falta
  nada especial acá — el firmware ya trata `applyCommand()` como
  idempotente (aplicar el mismo comando dos veces es un no-op seguro) y
  el backend marca el comando `ACKED` una sola vez.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.dependencies import authenticate_device_credential
from app.core.logging_config import get_logger
from app.core.ws_manager import manager
from app.db import SessionLocal
from app.models.entities import Command, Device
from app.schemas.iot import CommandOut

router = APIRouter(prefix="/api/v1/iot", tags=["IoT"])
logger = get_logger("voltguard.iot.ws")


def _pending_commands(db: Session, device_id: int) -> list[Command]:
    return (
        db.query(Command)
        .filter(Command.device_id == device_id, Command.status == "PENDING")
        .order_by(Command.id.asc())
        .all()
    )


@router.websocket("/ws")
async def device_ws(websocket: WebSocket) -> None:
    authorization = websocket.headers.get("authorization")
    db = SessionLocal()
    try:
        device: Device | None = authenticate_device_credential(db, authorization)
        pending = _pending_commands(db, device.id) if device is not None else []
    finally:
        db.close()

    if device is None:
        # 4401: mismo código que ya usa app/api/app/ws.py para "no
        # autenticado" — no es un código WS estándar, es un rango libre
        # para uso de aplicación (4000-4999) segun RFC 6455.
        await websocket.close(code=4401)
        return

    await manager.connect_device(device.id, websocket)
    logger.info("device_ws_connected", extra={"device_id": device.id, "public_id": device.public_id})

    try:
        # Catch-up: cualquier comando que haya quedado pendiente mientras
        # el dispositivo estaba desconectado (o entre que se creó y esta
        # reconexión) se entrega de una, en vez de esperar al poll.
        for command in pending:
            await websocket.send_json(
                {"type": "command", "command": CommandOut.model_validate(command).model_dump()}
            )

        while True:
            # No se espera nada del dispositivo por este canal — el bucle
            # solo mantiene la corrutina viva hasta que el cliente cierra.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_device(device.id, websocket)
        logger.info("device_ws_disconnected", extra={"device_id": device.id})
