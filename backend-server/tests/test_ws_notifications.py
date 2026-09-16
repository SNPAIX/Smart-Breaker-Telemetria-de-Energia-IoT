"""Prueba end-to-end del "Camino B" (WebSocket, sin Firebase — ver
roadmap/GUIA-PUSH-NOTIFICATIONS-FCM.md): un cliente WS real se conecta
autenticado, se dispara un evento crítico real (mismo camino que ya
prueba `test_notifications.py`) y se verifica que el mensaje llega por el
socket abierto — sin mockear `get_push_sender`, a diferencia de
`test_notifications.py`, para validar la implementación real
(`WebSocketPushSender` + `ConnectionManager`)."""
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import (
    Device,
    DeviceProfile,
    Notification,
    NotificationPreference,
    Site,
    SiteMember,
    User,
)
from app.services.device_auth import issue_device_credential
from simulator.device_simulator import DeviceSimulator
from simulator.scenarios import scenario_overload

client = TestClient(app)

TEST_SITE = "Sitio WS (test_ws_notifications)"
TEST_DEVICE = "VG-WS-NOTIFICATIONS-TEST"
TEST_USER = "ws_notifications_test@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    user = db.query(User).filter(User.email == TEST_USER).first()
    if user:
        db.delete(user)  # cascada: SiteMember, Notification, NotificationPreference
        db.commit()
    device = db.query(Device).filter(Device.public_id == TEST_DEVICE).first()
    if device:
        db.delete(device)
        db.commit()
    site = db.query(Site).filter(Site.name == TEST_SITE).first()
    if site:
        db.delete(site)
        db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name == TEST_SITE).delete()
    db.commit()
    db.close()


def test_evento_critico_real_llega_por_websocket_a_conexion_abierta() -> None:
    _cleanup()
    db = SessionLocal()
    user = User(email=TEST_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    site = Site(name=TEST_SITE, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)

    db.add_all(
        [
            SiteMember(site_id=site.id, user_id=user.id, role="owner"),
            NotificationPreference(user_id=user.id, channel="push", enabled=True),
        ]
    )
    db.commit()

    profile = DeviceProfile(name=TEST_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=TEST_DEVICE, name="Dispositivo WS", site_id=site.id, profile_id=profile.id
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()

    user_id = user.id
    db.close()

    token = create_access_token(subject=str(user_id), role="user")

    try:
        with client.websocket_connect(f"/api/v1/app/ws?token={token}") as websocket:
            sim = DeviceSimulator(client=client, public_id=TEST_DEVICE, secret=secret)
            response = scenario_overload(sim, sequence=1, max_current_a=10.0)
            assert response.status_code == 200
            assert response.json()["command"] is not None

            message = websocket.receive_json()
            assert message["type"] == "notification"
            assert message["title"]
            assert message["body"]

        db = SessionLocal()
        notification_count = db.query(Notification).filter(Notification.user_id == user_id).count()
        db.close()
        assert notification_count == 1  # in-app siempre se registra además del push
    finally:
        _cleanup()


def test_token_invalido_se_rechaza_con_codigo_4401() -> None:
    try:
        with client.websocket_connect("/api/v1/app/ws?token=esto-no-es-un-jwt-valido"):
            raise AssertionError("Se esperaba que el servidor cerrara la conexión.")
    except Exception as exc:
        # Starlette expone el cierre WS como excepción del lado del cliente
        # de prueba — se valida el código, no solo que haya fallado.
        assert "4401" in str(exc) or getattr(exc, "code", None) == 4401
