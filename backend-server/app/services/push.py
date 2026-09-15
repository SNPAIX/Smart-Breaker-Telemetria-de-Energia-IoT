"""Envío de notificaciones push (web/mobile).

Dos implementaciones conviven a propósito:

- `WebSocketPushSender` ("Camino B", sin credenciales externas): empuja
  el mensaje por el WebSocket de `app/api/app/ws.py` si el usuario tiene
  una conexión abierta ahora mismo — funciona mientras la app está
  abierta (aunque sea en segundo plano), pero no sobrevive a que el
  sistema operativo mate el proceso.
- `NoopPushSender`: registra el intento en el log, para cuando no hay
  conexión activa o se quiera desactivar el envío real sin tocar el resto
  del sistema.

El "Camino A" (Firebase Cloud Messaging, sobrevive a la app cerrada) no
está implementado todavía — requiere credenciales externas reales que no
existen en este entorno (ver roadmap/GUIA-PUSH-NOTIFICATIONS-FCM.md).
Conectarlo más adelante es agregar una clase nueva con la misma interfaz
`PushSender` y cambiar `get_push_sender()` — nada más del sistema tiene
que cambiar.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import anyio

from app.core.logging_config import get_logger
from app.core.ws_manager import manager

logger = get_logger("voltguard.push")


class PushSender(ABC):
    @abstractmethod
    def send(self, *, user_id: int, title: str, body: str) -> bool:
        """Intenta enviar una notificación push. Devuelve True si el envío
        (o el registro del intento, en el adaptador Noop) se realizó."""


class NoopPushSender(PushSender):
    def send(self, *, user_id: int, title: str, body: str) -> bool:
        logger.info(
            "push_notification_noop",
            extra={"user_id": user_id, "title": title, "hint": "sin proveedor push configurado"},
        )
        return True


class WebSocketPushSender(PushSender):
    """Se llama desde `BackgroundTasks` (contexto sincrónico, en un hilo
    del threadpool de Starlette) pero `ConnectionManager.send_to_user` es
    una corrutina — `anyio.from_thread.run` es el puente correcto porque
    ese hilo fue creado por el propio `run_in_threadpool` de Starlette,
    que sí deja el portal de anyio disponible."""

    def send(self, *, user_id: int, title: str, body: str) -> bool:
        message = {"type": "notification", "title": title, "body": body}
        try:
            sent = anyio.from_thread.run(manager.send_to_user, user_id, message)
        except RuntimeError:
            # Se llamo fuera de un hilo con portal de anyio (ej. un script
            # suelto, no un BackgroundTask real) — no es un error del
            # envio en si, solo no hay como empujarlo ahora.
            logger.warning("push_no_event_loop_portal", extra={"user_id": user_id})
            return False

        if not sent:
            logger.info(
                "push_notification_no_active_connection",
                extra={"user_id": user_id, "title": title},
            )
        return sent


def get_push_sender() -> PushSender:
    return WebSocketPushSender()


def push_telemetry_update(device_id: int, reading: dict[str, Any]) -> None:
    """Empuja una lectura nueva a quien esté suscrito a este dispositivo
    ahora mismo (ver app/api/app/ws.py) — se llama desde `BackgroundTasks`
    en `receive_telemetry` (app/api/iot/router.py), nunca desde el propio
    request síncrono: la respuesta al ESP32 no debe esperar a que esto
    termine (es la misma razón por la que las notificaciones van por
    background_tasks, ver ADR de la etapa 10). Sin conexión activa para
    ese dispositivo simplemente no hace nada — es el caso normal, no un
    error (nadie tiene esa pantalla abierta en este momento)."""
    message = {"type": "telemetry", "device_id": device_id, "reading": reading}
    try:
        anyio.from_thread.run(manager.send_to_device_subscribers, device_id, message)
    except RuntimeError:
        logger.warning("push_no_event_loop_portal_telemetry", extra={"device_id": device_id})


def push_command_to_device(device_id: int, command: dict[str, Any]) -> None:
    """Empuja un comando nuevo al propio dispositivo por su WebSocket
    (`app/api/iot/ws.py`) apenas se crea — el acelerador de latencia
    pedido explícitamente ("no debe haber delay"). Se llama siempre desde
    `BackgroundTasks`, nunca bloquea la respuesta HTTP del endpoint que
    creó el comando.

    Sin conexión activa (WiFi caído, dispositivo apagado, reconectando)
    no es un error: el comando sigue `PENDING` en la base y lo recoge el
    poll de respaldo (`GET /commands/pending`, cada 3s del lado del
    firmware) o el catch-up de la próxima reconexión del WebSocket — este
    canal nunca es el único camino de entrega."""
    message = {"type": "command", "command": command}
    try:
        sent = anyio.from_thread.run(manager.send_to_device, device_id, message)
    except RuntimeError:
        logger.warning("push_no_event_loop_portal_command", extra={"device_id": device_id})
        return

    if not sent:
        logger.info(
            "push_command_no_active_connection",
            extra={"device_id": device_id, "command_id": command.get("id")},
        )
