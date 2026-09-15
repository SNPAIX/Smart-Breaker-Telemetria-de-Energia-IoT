from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import Device, DeviceProfile, Event, Site, SiteMember, User
from app.services.device_auth import issue_device_credential
from simulator.device_simulator import DeviceSimulator
from simulator.scenarios import scenario_overload

client = TestClient(app)

TEST_SITE_A = "Sitio A (app_api_test)"
TEST_SITE_B = "Sitio B (app_api_test)"
TEST_DEVICE_A = "VG-APP-API-TEST-A"
TEST_DEVICE_B = "VG-APP-API-TEST-B"
TEST_USER_A = "app_api_test_a@voltguard.com"
TEST_USER_B = "app_api_test_b@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    # Usuarios primero (db.delete() por fila, no en bloque): las
    # notificaciones de la etapa 10 referencian Event, asi que hay que
    # borrarlas (via cascada de User.notifications) antes de poder borrar
    # los Event de mas abajo.
    for email in (TEST_USER_A, TEST_USER_B):
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    for public_id in (TEST_DEVICE_A, TEST_DEVICE_B):
        device = db.query(Device).filter(Device.public_id == public_id).first()
        if device:
            db.query(Event).filter(Event.device_id == device.id).delete()
            db.commit()
            db.delete(device)
            db.commit()
    for site_name in (TEST_SITE_A, TEST_SITE_B):
        site = db.query(Site).filter(Site.name == site_name).first()
        if site:
            db.delete(site)  # cascada a SiteMember
            db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name.in_([TEST_SITE_A, TEST_SITE_B])).delete(
        synchronize_session=False
    )
    db.commit()
    db.close()


def _setup_user_with_site_and_device(
    email: str, site_name: str, device_public_id: str, *, max_current_a: float = 15.0
) -> tuple[int, str, int, int]:
    """Devuelve (user_id, jwt_token, site_id, device_id)."""
    db = SessionLocal()
    user = User(email=email, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    site = Site(name=site_name, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)

    db.add(SiteMember(site_id=site.id, user_id=user.id, role="owner"))
    db.commit()

    profile = DeviceProfile(name=site_name, max_current_a=max_current_a)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=device_public_id,
        name="Dispositivo de prueba app_api",
        site_id=site.id,
        profile_id=profile.id,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    user_id, site_id, device_id = user.id, site.id, device.id
    db.close()

    token = create_access_token(subject=str(user_id), role="user")
    return user_id, token, site_id, device_id


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_user_sees_only_their_own_site_and_device() -> None:
    _cleanup()
    try:
        _user_a, token_a, site_a, device_a = _setup_user_with_site_and_device(
            TEST_USER_A, TEST_SITE_A, TEST_DEVICE_A
        )
        _user_b, token_b, _site_b, _device_b = _setup_user_with_site_and_device(
            TEST_USER_B, TEST_SITE_B, TEST_DEVICE_B
        )

        sites_response = client.get("/api/v1/app/sites", headers=_auth_headers(token_a))
        assert sites_response.status_code == 200
        assert [s["id"] for s in sites_response.json()] == [site_a]

        devices_response = client.get(
            f"/api/v1/app/sites/{site_a}/devices", headers=_auth_headers(token_a)
        )
        assert devices_response.status_code == 200
        assert [d["id"] for d in devices_response.json()] == [device_a]

        detail_response = client.get(
            f"/api/v1/app/devices/{device_a}", headers=_auth_headers(token_a)
        )
        assert detail_response.status_code == 200
        assert detail_response.json()["public_id"] == TEST_DEVICE_A

        # B no puede ver el sitio ni el dispositivo de A.
        assert (
            client.get(f"/api/v1/app/sites/{site_a}/devices", headers=_auth_headers(token_b)).status_code
            == 403
        )
        assert (
            client.get(f"/api/v1/app/devices/{device_a}", headers=_auth_headers(token_b)).status_code
            == 404
        )
    finally:
        _cleanup()


def test_usuario_no_puede_controlar_ni_consultar_dispositivo_ajeno() -> None:
    """No alcanza con que B no pueda *listar* el dispositivo de A — acá se
    prueba explícitamente que tampoco puede *actuar* sobre él (switch,
    reactivate) ni leer sus datos operativos (telemetría, eventos, costo,
    predicción), con el dispositivo real en el estado que B intentaría
    explotar (encendido, para que un 404 no se confunda con un 409)."""
    _cleanup()
    try:
        _user_a, _token_a, _site_a, device_a = _setup_user_with_site_and_device(
            TEST_USER_A, TEST_SITE_A, TEST_DEVICE_A
        )
        _user_b, token_b, _site_b, _device_b = _setup_user_with_site_and_device(
            TEST_USER_B, TEST_SITE_B, TEST_DEVICE_B
        )
        headers_b = _auth_headers(token_b)

        assert (
            client.post(
                f"/api/v1/app/devices/{device_a}/switch", json={"desired_state": "OFF"}, headers=headers_b
            ).status_code
            == 404
        )
        assert (
            client.post(f"/api/v1/app/devices/{device_a}/reactivate", headers=headers_b).status_code == 404
        )
        assert (
            client.get(f"/api/v1/app/devices/{device_a}/telemetry", headers=headers_b).status_code == 404
        )
        assert client.get(f"/api/v1/app/devices/{device_a}/events", headers=headers_b).status_code == 404
        assert client.get(f"/api/v1/app/devices/{device_a}/cost", headers=headers_b).status_code == 404
        assert (
            client.get(f"/api/v1/app/devices/{device_a}/prediction", headers=headers_b).status_code == 404
        )
    finally:
        _cleanup()


def test_switch_rejected_after_lockout_until_reactivate() -> None:
    _cleanup()
    try:
        _user_id, token, _site_id, device_id = _setup_user_with_site_and_device(
            TEST_USER_A, TEST_SITE_A, TEST_DEVICE_A, max_current_a=10.0
        )

        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).one()
        secret = issue_device_credential(device)
        db.commit()
        db.close()

        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE_A, secret=secret)
        overload_response = scenario_overload(sim, sequence=1, max_current_a=10.0)
        assert overload_response.status_code == 200
        assert overload_response.json()["command"] is not None

        switch_on_response = client.post(
            f"/api/v1/app/devices/{device_id}/switch",
            headers=_auth_headers(token),
            json={"desired_state": "ON"},
        )
        assert switch_on_response.status_code == 409

        reactivate_response = client.post(
            f"/api/v1/app/devices/{device_id}/reactivate", headers=_auth_headers(token)
        )
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["is_locked_out"] is False
        assert reactivate_response.json()["desired_state"] == "ON"

        db = SessionLocal()
        events = (
            db.query(Event)
            .filter(Event.device_id == device_id, Event.type == "MANUAL_REACTIVATION")
            .count()
        )
        db.close()
        assert events == 1

        switch_on_again = client.post(
            f"/api/v1/app/devices/{device_id}/switch",
            headers=_auth_headers(token),
            json={"desired_state": "ON"},
        )
        assert switch_on_again.status_code == 200
    finally:
        _cleanup()


def test_claim_unbound_device_and_reject_double_claim() -> None:
    _cleanup()
    db = SessionLocal()
    user = User(email=TEST_USER_A, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    site = Site(name=TEST_SITE_A, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)
    db.add(SiteMember(site_id=site.id, user_id=user.id, role="owner"))
    db.commit()

    unbound_device = Device(public_id=TEST_DEVICE_A, name="Dispositivo sin reclamar")
    db.add(unbound_device)
    db.commit()

    user_id, site_id = user.id, site.id
    db.close()
    token = create_access_token(subject=str(user_id), role="user")

    try:
        claim_response = client.post(
            "/api/v1/app/devices/claim",
            headers=_auth_headers(token),
            json={"public_id": TEST_DEVICE_A, "site_id": site_id},
        )
        assert claim_response.status_code == 200
        assert claim_response.json()["site_id"] == site_id

        second_claim_response = client.post(
            "/api/v1/app/devices/claim",
            headers=_auth_headers(token),
            json={"public_id": TEST_DEVICE_A, "site_id": site_id},
        )
        assert second_claim_response.status_code == 409
    finally:
        _cleanup()


def test_read_only_device_endpoints_return_data() -> None:
    _cleanup()
    try:
        _user_id, token, _site_id, device_id = _setup_user_with_site_and_device(
            TEST_USER_A, TEST_SITE_A, TEST_DEVICE_A
        )

        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).one()
        secret = issue_device_credential(device)
        db.commit()
        db.close()

        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE_A, secret=secret)
        telemetry_response = sim.send_telemetry(sequence=1, voltage_v=127.0, current_a=2.0)
        assert telemetry_response.status_code == 200

        telemetry = client.get(
            f"/api/v1/app/devices/{device_id}/telemetry", headers=_auth_headers(token)
        )
        assert telemetry.status_code == 200
        assert len(telemetry.json()) == 1
        assert telemetry.json()[0]["sequence"] == 1

        events = client.get(f"/api/v1/app/devices/{device_id}/events", headers=_auth_headers(token))
        assert events.status_code == 200
        assert events.json() == []  # sin evento critico, telemetria dentro de rango

        metrics = client.get(f"/api/v1/app/devices/{device_id}/metrics", headers=_auth_headers(token))
        assert metrics.status_code == 200
        assert metrics.json()["latest_voltage"] == 127.0

        cost = client.get(f"/api/v1/app/devices/{device_id}/cost", headers=_auth_headers(token))
        assert cost.status_code == 200
        # Una sola lectura arma un dia (el primero del rango se estima con
        # su propio maximo-minimo, no se descarta — ver compute_daily_consumption),
        # pero sin spread dentro del dia el consumo estimado es 0; el
        # prorrateo de tarifas multi-dia se prueba a fondo en
        # tests/test_tariffs.py.
        assert "total_cost" in cost.json()
        assert cost.json()["days_analyzed"] == 1
        assert cost.json()["total_kwh"] == 0.0

        prediction = client.get(
            f"/api/v1/app/devices/{device_id}/prediction", headers=_auth_headers(token)
        )
        assert prediction.status_code == 200
        assert "projected_kwh" in prediction.json()
    finally:
        _cleanup()


def test_consumption_hourly_traza_el_dia_actual() -> None:
    """Vista "hoy, por hora" pedida explícitamente para la gráfica de
    consumo (15-sep) — a diferencia de granularity=day/month, ignora
    days/start/end y siempre usa el día calendario UTC actual."""
    from datetime import UTC, datetime

    _cleanup()
    try:
        _user_id, token, _site_id, device_id = _setup_user_with_site_and_device(
            TEST_USER_A, TEST_SITE_A, TEST_DEVICE_A
        )

        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).one()
        secret = issue_device_credential(device)
        db.commit()
        db.close()

        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE_A, secret=secret)
        now = datetime.now(UTC)
        # 3 lecturas dentro del dia de hoy, en horas distintas, energia
        # acumulada subiendo — cada hora deberia reflejar su propio tramo.
        hour_0 = now.replace(hour=0, minute=30, second=0, microsecond=0)
        hour_1 = now.replace(hour=1, minute=0, second=0, microsecond=0) if now.hour >= 1 else hour_0
        for sequence, (timestamp, energy) in enumerate(
            [(hour_0, 0.0), (hour_0, 0.5), (hour_1, 1.5)], start=1
        ):
            response = sim.send_telemetry(sequence=sequence, energy_kwh=energy, timestamp=timestamp)
            assert response.status_code == 200

        result = client.get(
            f"/api/v1/app/devices/{device_id}/consumption?granularity=hour",
            headers=_auth_headers(token),
        )
        assert result.status_code == 200
        body = result.json()
        assert body["granularity"] == "hour"
        assert len(body["points"]) >= 1
        total_kwh = sum(point["kwh"] for point in body["points"])
        assert total_kwh > 0  # se registro consumo real dentro del dia
        for point in body["points"]:
            assert len(point["period"]) == 13  # "YYYY-MM-DDTHH"
    finally:
        _cleanup()


def test_notification_preferences_upsert() -> None:
    _cleanup()
    db = SessionLocal()
    user = User(email=TEST_USER_A, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token(subject=str(user_id), role="user")

    try:
        response = client.patch(
            "/api/v1/app/notifications/preferences",
            headers=_auth_headers(token),
            json={"channel": "push", "enabled": False},
        )
        assert response.status_code == 200
        assert response.json() == {"channel": "push", "enabled": False}

        updated = client.patch(
            "/api/v1/app/notifications/preferences",
            headers=_auth_headers(token),
            json={"channel": "push", "enabled": True},
        )
        assert updated.status_code == 200
        assert updated.json()["enabled"] is True

        notifications_response = client.get(
            "/api/v1/app/notifications", headers=_auth_headers(token)
        )
        assert notifications_response.status_code == 200
        assert notifications_response.json() == []
    finally:
        _cleanup()


SELF_SERVICE_USER = "self_service_test@voltguard.com"
SELF_SERVICE_SITE = "Sitio Self Service (app_api_test)"
SELF_SERVICE_DEVICE = "VG-SELF-SERVICE-TEST"


def _cleanup_self_service() -> None:
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == SELF_SERVICE_DEVICE).first()
    profile_id = device.profile_id if device else None
    if device:
        db.delete(device)
        db.commit()
    if profile_id is not None:
        profile = db.query(DeviceProfile).filter(DeviceProfile.id == profile_id).first()
        if profile:
            db.delete(profile)
            db.commit()
    site = db.query(Site).filter(Site.name == SELF_SERVICE_SITE).first()
    if site:
        db.delete(site)  # cascada a SiteMember
        db.commit()
    user = db.query(User).filter(User.email == SELF_SERVICE_USER).first()
    if user:
        db.delete(user)
        db.commit()
    db.close()


def test_usuario_final_crea_su_propio_sitio_y_dispositivo() -> None:
    """Un usuario final puede crear su sitio (queda como owner automático,
    sin que un admin lo agregue) y dar de alta un dispositivo dentro de
    ese sitio, sin tener que manejar el concepto de DeviceProfile — el
    endpoint le crea uno propio detrás de escena."""
    _cleanup_self_service()
    db = SessionLocal()
    user = User(email=SELF_SERVICE_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token(subject=str(user_id), role="user")

    try:
        site_response = client.post(
            "/api/v1/app/sites",
            headers=_auth_headers(token),
            json={"name": SELF_SERVICE_SITE, "kind": "casa"},
        )
        assert site_response.status_code == 201
        site_id = site_response.json()["id"]

        # El usuario ya ve el sitio que acaba de crear, sin que nadie más lo agregue.
        sites_response = client.get("/api/v1/app/sites", headers=_auth_headers(token))
        assert site_id in [s["id"] for s in sites_response.json()]

        device_response = client.post(
            f"/api/v1/app/sites/{site_id}/devices",
            headers=_auth_headers(token),
            json={"public_id": SELF_SERVICE_DEVICE, "name": "Bomba de prueba", "max_current_a": 12.0},
        )
        assert device_response.status_code == 201
        body = device_response.json()
        assert body["public_id"] == SELF_SERVICE_DEVICE
        assert body["site_id"] == site_id
        assert "secret" in body and len(body["secret"]) > 0

        devices_response = client.get(
            f"/api/v1/app/sites/{site_id}/devices", headers=_auth_headers(token)
        )
        assert [d["public_id"] for d in devices_response.json()] == [SELF_SERVICE_DEVICE]
    finally:
        _cleanup_self_service()


def test_dueno_puede_borrar_su_propio_sitio_vacio() -> None:
    _cleanup_self_service()
    db = SessionLocal()
    user = User(email=SELF_SERVICE_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token(subject=str(user_id), role="user")

    try:
        site_response = client.post(
            "/api/v1/app/sites",
            headers=_auth_headers(token),
            json={"name": SELF_SERVICE_SITE, "kind": "casa"},
        )
        site_id = site_response.json()["id"]

        delete_response = client.delete(
            f"/api/v1/app/sites/{site_id}", headers=_auth_headers(token)
        )
        assert delete_response.status_code == 204

        sites_response = client.get("/api/v1/app/sites", headers=_auth_headers(token))
        assert site_id not in [s["id"] for s in sites_response.json()]
    finally:
        _cleanup_self_service()


def test_miembro_puede_renombrar_el_sitio() -> None:
    _cleanup_self_service()
    db = SessionLocal()
    user = User(email=SELF_SERVICE_USER, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    token = create_access_token(subject=str(user_id), role="user")

    try:
        site_response = client.post(
            "/api/v1/app/sites",
            headers=_auth_headers(token),
            json={"name": SELF_SERVICE_SITE, "kind": "casa"},
        )
        site_id = site_response.json()["id"]

        rename_response = client.patch(
            f"/api/v1/app/sites/{site_id}",
            headers=_auth_headers(token),
            json={"name": "Casa renombrada"},
        )
        assert rename_response.status_code == 200
        assert rename_response.json()["name"] == "Casa renombrada"
    finally:
        db = SessionLocal()
        renamed_site = db.query(Site).filter(Site.name == "Casa renombrada").first()
        if renamed_site:
            db.delete(renamed_site)  # cascada a SiteMember, igual que _cleanup_self_service
            db.commit()
        db.close()
        _cleanup_self_service()


def test_miembro_no_dueno_no_puede_borrar_el_sitio() -> None:
    _cleanup_self_service()
    db = SessionLocal()
    owner = User(email=SELF_SERVICE_USER, hashed_password=get_password_hash("password123"), role="user")
    member = User(
        email="self_service_member_test@voltguard.com",
        hashed_password=get_password_hash("password123"),
        role="user",
    )
    db.add_all([owner, member])
    db.commit()
    db.refresh(owner)
    db.refresh(member)

    site = Site(name=SELF_SERVICE_SITE, kind="casa")
    db.add(site)
    db.commit()
    db.refresh(site)
    db.add_all(
        [
            SiteMember(site_id=site.id, user_id=owner.id, role="owner"),
            SiteMember(site_id=site.id, user_id=member.id, role="member"),
        ]
    )
    db.commit()

    site_id, member_id = site.id, member.id
    db.close()
    member_token = create_access_token(subject=str(member_id), role="user")

    try:
        delete_response = client.delete(
            f"/api/v1/app/sites/{site_id}", headers=_auth_headers(member_token)
        )
        assert delete_response.status_code == 403
    finally:
        _cleanup_self_service()
        db = SessionLocal()
        db.query(User).filter(User.email == "self_service_member_test@voltguard.com").delete()
        db.commit()
        db.close()
