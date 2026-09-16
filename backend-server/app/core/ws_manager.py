"""Registro en memoria de conexiones WebSocket activas por usuario —
"Camino B" de notificaciones (ver roadmap/GUIA-PUSH-NOTIFICATIONS-FCM.md
para el contraste con el "Camino A", FCM): funciona mientras la app siga
abierta (aunque esté en segundo plano), pero no sobrevive a que el
sistema operativo mate el proceso — para eso hace falta Firebase, que
queda documentado pero sin implementar hasta que haya un proyecto real.

Vive en `app/core/` (no en `app/services/`) porque tanto el endpoint
WebSocket (`app/api/app/ws.py`) como el `PushSender` (`app/services/push.py`)
necesitan la misma instancia — es infraestructura compartida, no lógica de
negocio de un solo lado."""
from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        # Suscripciones a telemetría en vivo de un dispositivo puntual —
        # separado de `_connections` (que es por usuario, para
        # notificaciones) porque acá lo que importa es "quién está mirando
        # este dispositivo ahora mismo", no de quién es la sesión. La
        # autorización (¿el usuario pertenece al sitio del dispositivo?) se
        # valida una sola vez, al suscribirse (ver app/api/app/ws.py) — no
        # en cada mensaje, porque ya no hace falta re-preguntar por cada
        # lectura que llega.
        self._device_subscribers: dict[int, set[WebSocket]] = {}
        # Conexión saliente PROPIA del dispositivo (no de quien lo mira) —
        # el canal por el que el backend le empuja comandos en tiempo real
        # en vez de que el dispositivo tenga que preguntar por polling. Un
        # dispositivo normalmente mantiene una sola conexión, pero se guarda
        # como set para tolerar el instante de solape entre una reconexión
        # nueva y la vieja todavía sin limpiar.
        self._device_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(user_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(user_id, None)

    def is_connected(self, user_id: int) -> bool:
        return bool(self._connections.get(user_id))

    async def send_to_user(self, user_id: int, message: dict[str, Any]) -> bool:
        """Devuelve False sin error si el usuario no tiene ninguna conexión
        abierta ahora mismo — ese es el caso normal (app cerrada), no una
        falla; el llamador decide si eso importa."""
        connections = self._connections.get(user_id)
        if not connections:
            return False

        sent = False
        for websocket in list(connections):
            try:
                await websocket.send_json(message)
                sent = True
            except Exception:
                self.disconnect(user_id, websocket)
        return sent

    def subscribe_device(self, device_id: int, websocket: WebSocket) -> None:
        self._device_subscribers.setdefault(device_id, set()).add(websocket)

    def unsubscribe_all_devices(self, websocket: WebSocket) -> None:
        """Se llama al desconectar el socket — sin esto, un socket muerto
        quedaría referenciado para siempre en `_device_subscribers` (nunca
        se limpia solo, a diferencia de `_connections` que sí se poda en
        cada intento de envío fallido)."""
        for subscribers in self._device_subscribers.values():
            subscribers.discard(websocket)

    async def send_to_device_subscribers(self, device_id: int, message: dict[str, Any]) -> bool:
        subscribers = self._device_subscribers.get(device_id)
        if not subscribers:
            return False

        sent = False
        dead: list[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
                sent = True
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            subscribers.discard(websocket)
        return sent

    async def connect_device(self, device_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._device_connections.setdefault(device_id, set()).add(websocket)

    def disconnect_device(self, device_id: int, websocket: WebSocket) -> None:
        connections = self._device_connections.get(device_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._device_connections.pop(device_id, None)

    def is_device_connected(self, device_id: int) -> bool:
        return bool(self._device_connections.get(device_id))

    async def send_to_device(self, device_id: int, message: dict[str, Any]) -> bool:
        """Devuelve False sin error si el dispositivo no tiene el socket
        abierto ahora mismo (WiFi caído, todavía arrancando, etc.) — el
        llamador (`app/services/push.py::push_command_to_device`) no lo
        trata como falla: el comando sigue disponible por el poll HTTP de
        respaldo, que nunca se desactiva."""
        connections = self._device_connections.get(device_id)
        if not connections:
            return False

        sent = False
        dead: list[WebSocket] = []
        for websocket in list(connections):
            try:
                await websocket.send_json(message)
                sent = True
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            connections.discard(websocket)
        return sent


manager = ConnectionManager()
