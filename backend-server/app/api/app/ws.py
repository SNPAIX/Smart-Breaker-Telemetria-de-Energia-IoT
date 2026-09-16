"""Endpoint de notificaciones y telemetría en vivo (mismo socket para
ambas cosas — un usuario ya autenticado una vez no necesita una segunda
conexión para lo otro).

- Notificaciones ("Camino B", sin Firebase — ver
  roadmap/GUIA-PUSH-NOTIFICATIONS-FCM.md): la app se conecta acá apenas
  inicia sesión y se queda escuchando; mientras el socket sigue abierto,
  `app/services/push.py` puede empujarle mensajes en el momento.
- Telemetría en vivo: el cliente manda `{"type":"subscribe","device_id":N}`
  para pasar de polling a recibir cada lectura nueva de ESE dispositivo en
  cuanto llega (`app/api/iot/router.py` la empuja tras guardarla) — la
  suscripción se valida contra la misma regla de autorización que ya usan
  los endpoints REST de dispositivo (¿el usuario pertenece al sitio del
  dispositivo?), no cualquiera puede suscribirse a cualquier `device_id`.

Autenticación por query param (`?token=...`) en vez del header
`Authorization` de siempre: la API `WebSocket` del navegador/WebView no
permite mandar headers custom en el handshake, así que no se puede
reusar `get_current_user` (que depende de `oauth2_scheme` leyendo un
header) tal cual — se decodifica el mismo JWT a mano, mismo algoritmo y
clave."""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM, SECRET_KEY
from app.core.ws_manager import manager
from app.db import SessionLocal
from app.models.entities import User
from app.services.devices import is_user_authorized_for_device

router = APIRouter(prefix="/api/v1/app", tags=["Notificaciones en vivo"])


def _authenticate(token: str | None, db: Session) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()


async def _handle_subscribe(user: User, raw: str, websocket: WebSocket) -> None:
    try:
        message = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return
    if not isinstance(message, dict) or message.get("type") != "subscribe":
        return
    device_id = message.get("device_id")
    if not isinstance(device_id, int):
        return

    db = SessionLocal()
    try:
        authorized = is_user_authorized_for_device(db, user.id, device_id)
    finally:
        db.close()

    if authorized:
        manager.subscribe_device(device_id, websocket)


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    db = SessionLocal()
    try:
        user = _authenticate(token, db)
    finally:
        db.close()

    if user is None:
        await websocket.close(code=4401)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_subscribe(user, raw, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user.id, websocket)
        manager.unsubscribe_all_devices(websocket)
