"""Prueba end-to-end del canal WebSocket de comandos del dispositivo
(app/api/iot/ws.py): un dispositivo real se conecta autenticado con sus
credenciales, y un `switch` real disparado por un usuario le llega al
instante por el socket — sin pasar por polling. Cubre también el
catch-up (comando ya pendiente antes de conectar) y el rechazo de
credenciales inválidas."""
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import (
    Command,
    Device,
    DeviceProfile,
    Site,
    SiteMember,
    User,
)
from app.services.device_auth import issue_device_credential

client = TestClient(app)

TEST_SITE = "Sitio WS comandos (test_ws_device_commands)"
TEST_DEVICE = "VG-WS-COMMANDS-TEST"
TEST_USER = "ws_commands_test@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    user = db.query(User).filter(User.email == TEST_USER).first()
    if user:
        db.delete(user)
        db.commit()
    device = db.query(Device).filter(Device.public_id == TEST_DEVICE).first()
    if device:
        db.query(Command).filter(Command.device_id == device.id).delete()
        db.commit()
        db.delete(device)
        db.commit()
    site = db.query(Site).filter(Site.name == TEST_SITE).first()
    if site:
        db.delete(site)
        db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name == TEST_SITE).delete()
    db.commit()
    db.close()


def _setup() -> tuple[int, int, str]:
    db = SessionLocal()
    user = User(email=TEST_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    site = Site(name=TEST_SITE, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)
    db.add(SiteMember(site_id=site.id, user_id=user.id, role="owner"))
    db.commit()

    profile = DeviceProfile(name=TEST_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=TEST_DEVICE, name="Dispositivo WS comandos", site_id=site.id, profile_id=profile.id
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()

    user_id, device_id = user.id, device.id
    db.close()
    return user_id, device_id, secret


def test_switch_real_llega_por_ws_al_dispositivo_conectado() -> None:
    _cleanup()
    user_id, device_id, secret = _setup()
    user_token = create_access_token(subject=str(user_id), role="user")

    try:
        with client.websocket_connect(
            "/api/v1/iot/ws", headers={"Authorization": f"Device {TEST_DEVICE}:{secret}"}
        ) as device_socket:
            response = client.post(
                f"/api/v1/app/devices/{device_id}/switch",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"desired_state": "OFF"},
            )
            assert response.status_code == 200

            message = device_socket.receive_json()
            assert message["type"] == "command"
            assert message["command"]["type"] == "SET_RELAY_OFF"

            db = SessionLocal()
            command = db.query(Command).filter(Command.id == message["command"]["id"]).one()
            assert command.status == "PENDING"  # el push no lo marca ACKED por si solo
            db.close()
    finally:
        _cleanup()


def test_catch_up_entrega_comando_pendiente_al_conectar() -> None:
    """Un comando creado ANTES de que el dispositivo abra el socket (ej.
    se mandó mientras el dispositivo estaba desconectado) debe llegar de
    una apenas se conecta, sin esperar ningún poll."""
    _cleanup()
    _user_id, device_id, secret = _setup()

    db = SessionLocal()
    pending_command = Command(device_id=device_id, type="SET_RELAY_ON", status="PENDING")
    db.add(pending_command)
    db.commit()
    command_id = pending_command.id
    db.close()

    try:
        with client.websocket_connect(
            "/api/v1/iot/ws", headers={"Authorization": f"Device {TEST_DEVICE}:{secret}"}
        ) as device_socket:
            message = device_socket.receive_json()
            assert message["type"] == "command"
            assert message["command"]["id"] == command_id
            assert message["command"]["type"] == "SET_RELAY_ON"
    finally:
        _cleanup()


def test_credenciales_invalidas_se_rechazan_con_codigo_4401() -> None:
    _cleanup()
    _user_id, _device_id, _secret = _setup()
    try:
        with client.websocket_connect(
            "/api/v1/iot/ws", headers={"Authorization": f"Device {TEST_DEVICE}:secreto-incorrecto"}
        ):
            raise AssertionError("Se esperaba que el servidor cerrara la conexión.")
    except Exception as exc:
        assert "4401" in str(exc) or getattr(exc, "code", None) == 4401
    finally:
        _cleanup()
