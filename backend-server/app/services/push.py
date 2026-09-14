"""Envío de notificaciones push (web/mobile).

No hay credenciales de un proveedor real (FCM, Expo Push, APNs) — es
exactamente el caso de "falta una credencial externa real" de las reglas
de ejecución del roadmap. En vez de bloquear la etapa, se deja la interfaz
completa (`PushSender`) y un adaptador `NoopPushSender` que registra el
intento en el log estructurado. Conectar un proveedor real es implementar
una clase nueva con la misma interfaz y cambiar `get_push_sender()` — nada
más del sistema tiene que cambiar.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.logging_config import get_logger

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


def get_push_sender() -> PushSender:
    return NoopPushSender()
