"""Prueba end-to-end de la suscripción a telemetría en vivo por
WebSocket (complementa test_ws_telemetry.py, que prueba notificaciones
sobre el mismo socket): un cliente se suscribe a un device_id, el
dispositivo real manda una lectura, y se valida que llegue por el socket
sin pasar por polling — y que un usuario sin acceso a ese dispositivo no
puede suscribirse."""
import time

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.core.ws_manager import manager
from app.db import SessionLocal
from app.main import app
from app.models.entities import Device, DeviceProfile, Site, SiteMember, User
from app.services.device_auth import issue_device_credential
from simulator.device_simulator import DeviceSimulator

client = TestClient(app)

TEST_SITE = "Sitio WS telemetria (test_ws_telemetry)"
TEST_DEVICE = "VG-WS-TELEMETRY-TEST"
TEST_OWNER = "ws_telemetry_owner@voltguard.com"
TEST_OUTSIDER = "ws_telemetry_outsider@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    for email in (TEST_OWNER, TEST_OUTSIDER):
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
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


def _setup() -> tuple[int, int, int, str]:
    db = SessionLocal()
    owner = User(email=TEST_OWNER, hashed_password=get_password_hash("password123"), role="user")
    outsider = User(
        email=TEST_OUTSIDER, hashed_password=get_password_hash("password123"), role="user"
    )
    db.add_all([owner, outsider])
    db.commit()
    db.refresh(owner)
    db.refresh(outsider)

    site = Site(name=TEST_SITE, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)
    db.add(SiteMember(site_id=site.id, user_id=owner.id, role="owner"))
    db.commit()

    profile = DeviceProfile(name=TEST_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(public_id=TEST_DEVICE, name="Dispositivo WS telemetria", site_id=site.id, profile_id=profile.id)
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()

    owner_id, outsider_id, device_id = owner.id, outsider.id, device.id
    db.close()
    return owner_id, outsider_id, device_id, secret


def test_telemetria_real_llega_por_ws_a_suscriptor_autorizado() -> None:
    _cleanup()
    owner_id, _outsider_id, device_id, secret = _setup()
    token = create_access_token(subject=str(owner_id), role="user")

    try:
        with client.websocket_connect(f"/api/v1/app/ws?token={token}") as websocket:
            websocket.send_json({"type": "subscribe", "device_id": device_id})

            sim = DeviceSimulator(client=client, public_id=TEST_DEVICE, secret=secret)
            response = sim.send_telemetry(sequence=1, voltage_v=127.0, current_a=1.5)
            assert response.status_code == 200

            message = websocket.receive_json()
            assert message["type"] == "telemetry"
            assert message["device_id"] == device_id
            assert message["reading"]["voltage"] == 127.0
            assert message["reading"]["current"] == 1.5
    finally:
        _cleanup()


def test_usuario_sin_acceso_no_puede_suscribirse_a_telemetria_ajena() -> None:
    _cleanup()
    _owner_id, outsider_id, device_id, _secret = _setup()
    token = create_access_token(subject=str(outsider_id), role="user")

    try:
        with client.websocket_connect(f"/api/v1/app/ws?token={token}") as websocket:
            websocket.send_json({"type": "subscribe", "device_id": device_id})
            # La conexion de TestClient corre en un hilo aparte — dar
            # tiempo a que el servidor procese el mensaje antes de revisar
            # el estado del manager.
            time.sleep(0.2)
            subscribers = manager._device_subscribers.get(device_id)
            assert not subscribers  # la suscripcion no autorizada nunca se registro
    finally:
        _cleanup()
