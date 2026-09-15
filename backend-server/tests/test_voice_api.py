"""Verifica el endpoint del asistente de voz (etapa 14) end-to-end contra
la base de datos real — mismo patrón que el resto de `tests/test_app_api.py`.

Este endpoint solo se registra cuando `settings.voice_assistant_enabled` es
`True`, así que el test activa el flag y recarga `app.main` antes de
construir su propio `TestClient` — el resto de la suite sigue importando
`app.main.app` normalmente y no se ve afectado, porque cada módulo de test
ya capturó su propia referencia al `app` original al importarse."""
import importlib

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.models.entities import Device, DeviceProfile, Site, SiteMember, User

pytest.importorskip("ia_assistant", reason="Asistente de voz no instalado en este entorno (feature opcional).")

TEST_SITE = "Sitio Voz (voice_api_test)"
TEST_DEVICE_LUZ = "VG-VOICE-TEST-LUZ"
TEST_USER = "voice_api_test@voltguard.com"

OTHER_SITE = "Sitio Voz B (voice_api_test)"
OTHER_DEVICE = "VG-VOICE-TEST-BOMBA"
OTHER_USER = "voice_api_test_b@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    for email in (TEST_USER, OTHER_USER):
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    for public_id in (TEST_DEVICE_LUZ, OTHER_DEVICE):
        device = db.query(Device).filter(Device.public_id == public_id).first()
        if device:
            db.delete(device)
            db.commit()
    for site_name in (TEST_SITE, OTHER_SITE):
        site = db.query(Site).filter(Site.name == site_name).first()
        if site:
            db.delete(site)  # cascada a SiteMember
            db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name.in_([TEST_SITE, OTHER_SITE])).delete(
        synchronize_session=False
    )
    db.commit()
    db.close()


def _setup() -> tuple[str, int]:
    """Devuelve (jwt_token, device_id) de un usuario con un dispositivo
    llamado "Luz Sala" — para poder probar "apaga el foco de la sala"."""
    db = SessionLocal()
    user = User(email=TEST_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    site = Site(name=TEST_SITE, kind="casa")
    db.add(site)
    db.commit()
    db.refresh(site)

    db.add(SiteMember(site_id=site.id, user_id=user.id, role="owner"))
    profile = DeviceProfile(name=TEST_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=TEST_DEVICE_LUZ,
        name="Luz Sala",
        site_id=site.id,
        profile_id=profile.id,
        desired_state="ON",
        actual_state="ON",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    device_id = device.id
    user_id = user.id
    db.close()

    token = create_access_token(subject=str(user_id), role="user")
    return token, device_id


def _setup_other_user_with_device() -> tuple[str, int]:
    """Un segundo usuario, sin relación con el primero, con un dispositivo
    de nombre bien distinto ("Bomba Jardin") — para probar que el
    asistente de voz de un usuario nunca alcanza el dispositivo de otro,
    ni siquiera nombrándolo explícitamente."""
    db = SessionLocal()
    user = User(email=OTHER_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    site = Site(name=OTHER_SITE, kind="casa")
    db.add(site)
    db.commit()
    db.refresh(site)

    db.add(SiteMember(site_id=site.id, user_id=user.id, role="owner"))
    profile = DeviceProfile(name=OTHER_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=OTHER_DEVICE,
        name="Bomba Jardin",
        site_id=site.id,
        profile_id=profile.id,
        desired_state="ON",
        actual_state="ON",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    device_id = device.id
    user_id = user.id
    db.close()

    token = create_access_token(subject=str(user_id), role="user")
    return token, device_id


@pytest.fixture
def voice_client():
    _cleanup()
    original_flag = settings.voice_assistant_enabled
    settings.voice_assistant_enabled = True
    try:
        import app.main as main_module

        importlib.reload(main_module)
        yield TestClient(main_module.app)
    finally:
        settings.voice_assistant_enabled = original_flag
        _cleanup()


def test_apaga_el_foco_de_la_sala_ejecuta_la_accion_real(voice_client: TestClient) -> None:
    token, device_id = _setup()
    headers = {"Authorization": f"Bearer {token}"}

    response = voice_client.post(
        "/api/v1/app/voice/query", json={"text": "apaga el foco de la sala"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action_taken"] is True
    assert body["device_id"] == device_id
    assert "sala" in body["spoken_text"].lower() or "luz sala" in body["spoken_text"].lower()

    db = SessionLocal()
    device = db.query(Device).filter(Device.id == device_id).first()
    assert device is not None
    assert device.desired_state == "OFF"
    db.close()


def test_consulta_de_estado_no_ejecuta_ninguna_accion(voice_client: TestClient) -> None:
    token, device_id = _setup()
    headers = {"Authorization": f"Bearer {token}"}

    response = voice_client.post(
        "/api/v1/app/voice/query", json={"text": "esta encendida la luz de la sala"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action_taken"] is False
    assert body["device_id"] == device_id
    assert "encendid" in body["spoken_text"].lower()


def test_comando_sin_dispositivo_reconocible_no_rompe_nada(voice_client: TestClient) -> None:
    token, _ = _setup()
    headers = {"Authorization": f"Bearer {token}"}

    response = voice_client.post(
        "/api/v1/app/voice/query", json={"text": "hola como estas hoy"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action_taken"] is False
    assert body["intent_type"] == "unknown"


def test_asistente_de_voz_no_alcanza_dispositivos_de_otro_usuario(voice_client: TestClient) -> None:
    """El usuario A nombra explícitamente el dispositivo del usuario B
    ("apaga la bomba jardin") — `list_user_devices` ya lo excluyó antes de
    que el matcher viera el texto, así que ningún nombre ajeno debería
    poder resolverse, sin importar qué tan bien coincida la frase."""
    token_a, _device_a_id = _setup()
    _token_b, device_b_id = _setup_other_user_with_device()
    headers_a = {"Authorization": f"Bearer {token_a}"}

    response = voice_client.post(
        "/api/v1/app/voice/query", json={"text": "apaga la bomba jardin"}, headers=headers_a
    )
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] != device_b_id
    assert body["device_id"] is None
    assert body["action_taken"] is False

    db = SessionLocal()
    device_b = db.query(Device).filter(Device.id == device_b_id).first()
    assert device_b is not None
    assert device_b.desired_state == "ON"  # intacto, nunca se tocó
    db.close()
