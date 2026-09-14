"""Convierte eventos y anomalías en notificaciones — único responsable de
"quién debe enterarse" (el motor de reglas de la etapa 5 solo crea el
`Event`, nunca decide notificaciones, para no duplicar esa lógica).

Se ejecuta como `BackgroundTasks` de FastAPI (no bloquea la respuesta HTTP
que originó el evento) y abre su propia sesión de base de datos — la
sesión de la request ya se cierra antes de que la tarea de fondo corra.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.entities import (
    AnomalyAlert,
    Device,
    Event,
    Notification,
    NotificationPreference,
    SiteMember,
)
from app.services.push import get_push_sender

EVENT_MESSAGES: dict[str, tuple[str, str]] = {
    "CRITICAL_OVERLOAD": (
        "Sobrecarga crítica",
        "Se detectó una sobrecarga y el dispositivo se apagó automáticamente.",
    ),
    "CRITICAL_OVERVOLTAGE": (
        "Sobrevoltaje crítico",
        "Se detectó un voltaje por encima del límite seguro y el dispositivo se apagó.",
    ),
    "CRITICAL_UNDERVOLTAGE": (
        "Bajo voltaje crítico",
        "Se detectó un voltaje por debajo del límite seguro y el dispositivo se apagó.",
    ),
    "MANUAL_REACTIVATION": (
        "Dispositivo reactivado",
        "El dispositivo fue reactivado manualmente tras un evento crítico.",
    ),
}


def _channel_enabled(db: Session, user_id: int, channel: str, *, default: bool) -> bool:
    preference = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id, NotificationPreference.channel == channel)
        .first()
    )
    return preference.enabled if preference is not None else default


def _notify_site_members(
    db: Session, device: Device, title: str, body: str, *, event_id: int | None = None
) -> None:
    if device.site_id is None:
        return

    sender = get_push_sender()
    members = db.query(SiteMember).filter(SiteMember.site_id == device.site_id).all()
    for member in members:
        if _channel_enabled(db, member.user_id, "in_app", default=True):
            db.add(
                Notification(
                    user_id=member.user_id,
                    event_id=event_id,
                    channel="in_app",
                    title=title,
                    body=body,
                )
            )
        if _channel_enabled(db, member.user_id, "push", default=False):
            sender.send(user_id=member.user_id, title=title, body=body)
    db.commit()


def notify_event_by_id(event_id: int) -> None:
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event is None:
            return
        device = db.query(Device).filter(Device.id == event.device_id).first()
        if device is None:
            return
        title, body = EVENT_MESSAGES.get(
            event.type, (event.type, "Se generó un evento nuevo en tu dispositivo.")
        )
        _notify_site_members(db, device, title, body, event_id=event.id)
    finally:
        db.close()


def notify_anomaly_by_id(alert_id: int) -> None:
    db = SessionLocal()
    try:
        alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == alert_id).first()
        if alert is None:
            return
        device = db.query(Device).filter(Device.id == alert.device_id).first()
        if device is None:
            return
        title = "Consumo inusual detectado"
        body = (
            f"Se detectó una potencia de {alert.power:.1f} W, distinta de lo esperado "
            f"(~{alert.expected_power:.1f} W)."
        )
        _notify_site_members(db, device, title, body)
    finally:
        db.close()
