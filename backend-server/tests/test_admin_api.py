from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import Device, DeviceProfile, Site, SiteMember, User
from simulator.device_simulator import DeviceSimulator

client = TestClient(app)

ADMIN_EMAIL = "admin_api_test@voltguard.com"
NORMAL_EMAIL = "admin_api_test_normal@voltguard.com"
TEST_SITE_1 = "Sitio admin 1 (admin_api_test)"
TEST_SITE_2 = "Sitio admin 2 (admin_api_test)"
TEST_DEVICE = "VG-ADMIN-API-TEST"


def _cleanup() -> None:
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_DEVICE).first()
    if device:
        db.delete(device)
        db.commit()
    for site_name in (TEST_SITE_1, TEST_SITE_2):
        site = db.query(Site).filter(Site.name == site_name).first()
        if site:
            db.delete(site)
            db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name.in_([TEST_SITE_1, TEST_SITE_2])).delete(
        synchronize_session=False
    )
    db.commit()
    for email in (ADMIN_EMAIL, NORMAL_EMAIL):
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
    db.close()


def _admin_token() -> str:
    db = SessionLocal()
    user = User(email=ADMIN_EMAIL, hashed_password=get_password_hash("password123"), role="admin")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return create_access_token(subject=str(user_id), role="admin")


def _normal_token() -> str:
    db = SessionLocal()
    user = User(email=NORMAL_EMAIL, hashed_password=get_password_hash("password123"), role="user")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return create_access_token(subject=str(user_id), role="user")


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_full_admin_flow_site_device_reassign_metrics_online_offline() -> None:
    _cleanup()
    try:
        token = _admin_token()

        site1 = client.post("/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_1, "kind": "taller"})
        assert site1.status_code == 201
        site1_id = site1.json()["id"]

        site2 = client.post("/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_2, "kind": "taller"})
        assert site2.status_code == 201
        site2_id = site2.json()["id"]

        profile = client.post(
            "/api/v1/admin/profiles",
            headers=_auth(token),
            json={"name": TEST_SITE_1, "site_id": site1_id, "max_current_a": 12.0},
        )
        assert profile.status_code == 201
        profile_id = profile.json()["id"]

        device_response = client.post(
            "/api/v1/admin/devices",
            headers=_auth(token),
            json={
                "public_id": TEST_DEVICE,
                "name": "Dispositivo de prueba admin",
                "site_id": site1_id,
                "profile_id": profile_id,
            },
        )
        assert device_response.status_code == 201
        device_body = device_response.json()
        device_id = device_body["id"]
        secret = device_body["secret"]

        # La credencial recien emitida debe funcionar de verdad contra /api/v1/iot/*.
        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE, secret=secret)
        telemetry_response = sim.send_telemetry(sequence=1, voltage_v=127.0, current_a=1.0)
        assert telemetry_response.status_code == 200

        # Reasignar a otro sitio.
        reassign_response = client.post(
            f"/api/v1/admin/devices/{device_id}/reassign",
            headers=_auth(token),
            json={"site_id": site2_id},
        )
        assert reassign_response.status_code == 200
        assert reassign_response.json()["site_id"] == site2_id

        # Metricas globales y agrupadas.
        global_metrics = client.get("/api/v1/admin/dashboard/metrics", headers=_auth(token))
        assert global_metrics.status_code == 200
        assert global_metrics.json()["total_devices"] >= 1
        assert global_metrics.json()["devices_online"] >= 1  # justo envio telemetria

        by_site = client.get("/api/v1/admin/dashboard/by-site", headers=_auth(token))
        assert by_site.status_code == 200
        site2_metrics = next(s for s in by_site.json() if s["site_id"] == site2_id)
        assert site2_metrics["device_count"] == 1

        overview = client.get("/api/v1/admin/dashboard/overview", headers=_auth(token))
        assert overview.status_code == 200
        assert "global_metrics" in overview.json()

        # Offline: retroceder last_seen_at mas alla del umbral configurado.
        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).one()
        device.last_seen_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
        db.close()

        global_metrics_after = client.get("/api/v1/admin/dashboard/metrics", headers=_auth(token))
        assert global_metrics_after.json()["devices_offline"] >= 1
    finally:
        _cleanup()


def test_non_admin_rejected_on_admin_routes() -> None:
    _cleanup()
    try:
        token = _normal_token()
        assert client.get("/api/v1/admin/users", headers=_auth(token)).status_code == 403
        assert (
            client.post(
                "/api/v1/admin/sites", headers=_auth(token), json={"name": "x", "kind": "otro"}
            ).status_code
            == 403
        )
        assert client.get("/api/v1/admin/dashboard/metrics", headers=_auth(token)).status_code == 403
    finally:
        _cleanup()


def test_site_deletion_blocked_while_devices_assigned() -> None:
    _cleanup()
    try:
        token = _admin_token()
        site_response = client.post(
            "/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_1, "kind": "taller"}
        )
        site_id = site_response.json()["id"]

        client.post(
            "/api/v1/admin/devices",
            headers=_auth(token),
            json={"public_id": TEST_DEVICE, "name": "Dispositivo", "site_id": site_id},
        )

        delete_response = client.delete(f"/api/v1/admin/sites/{site_id}", headers=_auth(token))
        assert delete_response.status_code == 409
    finally:
        _cleanup()


def test_profile_deletion_blocked_while_in_use() -> None:
    _cleanup()
    try:
        token = _admin_token()
        profile_response = client.post(
            "/api/v1/admin/profiles", headers=_auth(token), json={"name": TEST_SITE_1}
        )
        profile_id = profile_response.json()["id"]

        client.post(
            "/api/v1/admin/devices",
            headers=_auth(token),
            json={"public_id": TEST_DEVICE, "name": "Dispositivo", "profile_id": profile_id},
        )

        delete_response = client.delete(f"/api/v1/admin/profiles/{profile_id}", headers=_auth(token))
        assert delete_response.status_code == 409
    finally:
        _cleanup()


def test_duplicate_public_id_rejected() -> None:
    _cleanup()
    try:
        token = _admin_token()
        payload = {"public_id": TEST_DEVICE, "name": "Dispositivo"}
        first = client.post("/api/v1/admin/devices", headers=_auth(token), json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/admin/devices", headers=_auth(token), json=payload)
        assert second.status_code == 400
    finally:
        _cleanup()


def test_site_and_profile_read_and_update() -> None:
    _cleanup()
    try:
        token = _admin_token()
        site_response = client.post(
            "/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_1, "kind": "taller"}
        )
        site_id = site_response.json()["id"]

        get_site = client.get(f"/api/v1/admin/sites/{site_id}", headers=_auth(token))
        assert get_site.status_code == 200
        assert get_site.json()["name"] == TEST_SITE_1

        updated_site = client.patch(
            f"/api/v1/admin/sites/{site_id}", headers=_auth(token), json={"kind": "negocio"}
        )
        assert updated_site.status_code == 200
        assert updated_site.json()["kind"] == "negocio"

        profile_response = client.post(
            "/api/v1/admin/profiles",
            headers=_auth(token),
            json={"name": TEST_SITE_1, "site_id": site_id, "max_current_a": 10.0},
        )
        profile_id = profile_response.json()["id"]

        get_profile = client.get(f"/api/v1/admin/profiles/{profile_id}", headers=_auth(token))
        assert get_profile.status_code == 200

        updated_profile = client.patch(
            f"/api/v1/admin/profiles/{profile_id}",
            headers=_auth(token),
            json={"max_current_a": 20.0, "max_voltage_v": 135.0},
        )
        assert updated_profile.status_code == 200
        assert updated_profile.json()["max_current_a"] == 20.0
        assert updated_profile.json()["max_voltage_v"] == 135.0
    finally:
        _cleanup()


def test_not_found_responses_for_unknown_ids() -> None:
    _cleanup()
    try:
        token = _admin_token()
        assert client.get("/api/v1/admin/sites/999999", headers=_auth(token)).status_code == 404
        assert client.get("/api/v1/admin/devices/999999", headers=_auth(token)).status_code == 404
        assert client.get("/api/v1/admin/profiles/999999", headers=_auth(token)).status_code == 404
        assert client.get("/api/v1/admin/users/999999", headers=_auth(token)).status_code == 404
    finally:
        _cleanup()


def test_admin_can_add_and_remove_site_members() -> None:
    _cleanup()
    try:
        token = _admin_token()
        site_response = client.post(
            "/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_1, "kind": "casa"}
        )
        site_id = site_response.json()["id"]

        db = SessionLocal()
        normal_user = User(
            email=NORMAL_EMAIL, hashed_password=get_password_hash("password123"), role="user"
        )
        db.add(normal_user)
        db.commit()
        user_id = normal_user.id
        db.close()

        add_response = client.post(
            f"/api/v1/admin/sites/{site_id}/members",
            headers=_auth(token),
            json={"user_id": user_id, "role": "owner"},
        )
        assert add_response.status_code == 201
        assert add_response.json()["role"] == "owner"

        duplicate_response = client.post(
            f"/api/v1/admin/sites/{site_id}/members",
            headers=_auth(token),
            json={"user_id": user_id, "role": "member"},
        )
        assert duplicate_response.status_code == 400

        list_response = client.get(f"/api/v1/admin/sites/{site_id}/members", headers=_auth(token))
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        remove_response = client.delete(
            f"/api/v1/admin/sites/{site_id}/members/{user_id}", headers=_auth(token)
        )
        assert remove_response.status_code == 204

        list_after_remove = client.get(
            f"/api/v1/admin/sites/{site_id}/members", headers=_auth(token)
        )
        assert list_after_remove.json() == []
    finally:
        _cleanup()


def test_user_crud() -> None:
    _cleanup()
    try:
        token = _admin_token()
        created = client.post(
            "/api/v1/admin/users",
            headers=_auth(token),
            json={"email": NORMAL_EMAIL, "password": "password123", "role": "user"},
        )
        assert created.status_code == 201
        user_id = created.json()["id"]

        updated = client.patch(
            f"/api/v1/admin/users/{user_id}", headers=_auth(token), json={"is_active": False}
        )
        assert updated.status_code == 200
        assert updated.json()["is_active"] is False

        deleted = client.delete(f"/api/v1/admin/users/{user_id}", headers=_auth(token))
        assert deleted.status_code == 204
    finally:
        _cleanup()


def test_admin_site_list_incluye_el_correo_del_dueno() -> None:
    """La consola de admin da soporte sobre sitios de terceros — sin el
    dueño resuelto en la lista, no hay forma de saber de quién es cada
    sitio con solo ver /api/v1/admin/sites."""
    _cleanup()
    try:
        token = _admin_token()

        with_owner = client.post(
            "/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_1, "kind": "taller"}
        )
        assert with_owner.status_code == 201
        site1_id = with_owner.json()["id"]

        without_owner = client.post(
            "/api/v1/admin/sites", headers=_auth(token), json={"name": TEST_SITE_2, "kind": "taller"}
        )
        assert without_owner.status_code == 201

        db = SessionLocal()
        owner = User(
            email=NORMAL_EMAIL, hashed_password=get_password_hash("password123"), role="user"
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)
        db.add(SiteMember(site_id=site1_id, user_id=owner.id, role="owner"))
        db.commit()
        db.close()

        site2_id = without_owner.json()["id"]

        db = SessionLocal()
        admin_user = db.query(User).filter(User.email == ADMIN_EMAIL).one()
        db.add(SiteMember(site_id=site2_id, user_id=admin_user.id, role="member"))
        db.commit()
        db.close()

        listed = client.get("/api/v1/admin/sites", headers=_auth(token))
        assert listed.status_code == 200
        by_id = {site["id"]: site for site in listed.json()}
        assert by_id[site1_id]["owner_email"] == NORMAL_EMAIL
        assert by_id[site2_id]["owner_email"] is None

        # El admin se vinculó (soporte) a site2, nunca a site1.
        assert by_id[site2_id]["admin_is_member"] is True
        assert by_id[site1_id]["admin_is_member"] is False
    finally:
        _cleanup()


def _crear_sitio_con_dueno_unico_y_dispositivo(admin_token: str) -> tuple[int, int, int]:
    """Devuelve (owner_user_id, site_id, device_id) — un sitio con un solo
    owner (NORMAL_EMAIL) y un dispositivo, listo para probar el impacto de
    borrar a ese usuario."""
    site = client.post(
        "/api/v1/admin/sites", headers=_auth(admin_token), json={"name": TEST_SITE_1, "kind": "casa"}
    )
    site_id = site.json()["id"]

    db = SessionLocal()
    owner = User(email=NORMAL_EMAIL, hashed_password=get_password_hash("password123"), role="user")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    db.add(SiteMember(site_id=site_id, user_id=owner.id, role="owner"))
    device = Device(public_id=TEST_DEVICE, name="Dispositivo de prueba", site_id=site_id)
    db.add(device)
    db.commit()
    owner_id, device_id = owner.id, device.id
    db.close()
    return owner_id, site_id, device_id


def test_preview_de_borrado_lista_sitios_que_quedarian_huerfanos() -> None:
    _cleanup()
    try:
        admin_token = _admin_token()
        owner_id, site_id, _device_id = _crear_sitio_con_dueno_unico_y_dispositivo(admin_token)

        preview = client.get(
            f"/api/v1/admin/users/{owner_id}/deletion-impact", headers=_auth(admin_token)
        )
        assert preview.status_code == 200
        orphaned = preview.json()["orphaned_sites"]
        assert len(orphaned) == 1
        assert orphaned[0]["id"] == site_id
        assert orphaned[0]["device_count"] == 1
    finally:
        _cleanup()


def test_borrar_usuario_sin_flag_deja_el_sitio_huerfano_pero_intacto() -> None:
    _cleanup()
    try:
        admin_token = _admin_token()
        owner_id, site_id, device_id = _crear_sitio_con_dueno_unico_y_dispositivo(admin_token)

        deleted = client.delete(f"/api/v1/admin/users/{owner_id}", headers=_auth(admin_token))
        assert deleted.status_code == 204

        site_check = client.get(f"/api/v1/admin/sites/{site_id}", headers=_auth(admin_token))
        assert site_check.status_code == 200

        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).one()
        assert device.site_id == site_id  # el dispositivo no se movió
        db.close()
    finally:
        _cleanup()


def test_borrar_usuario_con_flag_borra_el_sitio_y_desvincula_sus_dispositivos() -> None:
    _cleanup()
    try:
        admin_token = _admin_token()
        owner_id, site_id, device_id = _crear_sitio_con_dueno_unico_y_dispositivo(admin_token)

        deleted = client.delete(
            f"/api/v1/admin/users/{owner_id}?delete_orphaned_sites=true", headers=_auth(admin_token)
        )
        assert deleted.status_code == 204

        site_check = client.get(f"/api/v1/admin/sites/{site_id}", headers=_auth(admin_token))
        assert site_check.status_code == 404

        db = SessionLocal()
        device = db.query(Device).filter(Device.id == device_id).one()
        assert device.site_id is None  # desvinculado, no borrado
        db.delete(device)
        db.commit()
        db.close()
    finally:
        _cleanup()


def test_sitio_con_coowner_no_se_borra_aunque_se_use_el_flag() -> None:
    _cleanup()
    try:
        admin_token = _admin_token()
        owner_id, site_id, device_id = _crear_sitio_con_dueno_unico_y_dispositivo(admin_token)

        db = SessionLocal()
        co_owner = User(
            email=NORMAL_EMAIL + ".co", hashed_password=get_password_hash("password123"), role="user"
        )
        db.add(co_owner)
        db.commit()
        db.refresh(co_owner)
        db.add(SiteMember(site_id=site_id, user_id=co_owner.id, role="owner"))
        db.commit()
        co_owner_id = co_owner.id
        db.close()

        preview = client.get(
            f"/api/v1/admin/users/{owner_id}/deletion-impact", headers=_auth(admin_token)
        )
        assert preview.json()["orphaned_sites"] == []  # hay un co-owner, no queda huérfano

        deleted = client.delete(
            f"/api/v1/admin/users/{owner_id}?delete_orphaned_sites=true", headers=_auth(admin_token)
        )
        assert deleted.status_code == 204

        site_check = client.get(f"/api/v1/admin/sites/{site_id}", headers=_auth(admin_token))
        assert site_check.status_code == 200  # el sitio sigue vivo gracias al co-owner

        db = SessionLocal()
        db.query(Device).filter(Device.id == device_id).delete()
        db.query(SiteMember).filter(SiteMember.user_id == co_owner_id).delete()
        db.query(User).filter(User.id == co_owner_id).delete()
        db.commit()
        db.close()
    finally:
        _cleanup()
