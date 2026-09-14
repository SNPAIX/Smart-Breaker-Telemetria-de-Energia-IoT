import pytest
from fastapi.testclient import TestClient

import app.services.notifications as notifications_module
from app.core.security import get_password_hash
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

TEST_SITE = "Sitio notificaciones (test_notifications)"
TEST_DEVICE = "VG-NOTIFICATIONS-TEST"
TEST_USER_PUSH_ON = "notifications_test_push_on@voltguard.com"
TEST_USER_PUSH_OFF = "notifications_test_push_off@voltguard.com"
TEST_USER_IN_APP_OFF = "notifications_test_in_app_off@voltguard.com"


class RecordingPushSender:
    def __init__(self) -> None:
        self.sent_to: list[int] = []

    def send(self, *, user_id: int, title: str, body: str) -> bool:
        self.sent_to.append(user_id)
        return True


def _cleanup() -> None:
    db = SessionLocal()
    for email in (TEST_USER_PUSH_ON, TEST_USER_PUSH_OFF, TEST_USER_IN_APP_OFF):
        user = db.query(User).filter(User.email == email).first()
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


def test_critical_event_notifies_in_app_always_and_push_only_if_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingPushSender()
    monkeypatch.setattr(notifications_module, "get_push_sender", lambda: recorder)

    _cleanup()
    db = SessionLocal()
    user_push_on = User(
        email=TEST_USER_PUSH_ON, hashed_password=get_password_hash("password123"), role="user"
    )
    user_push_off = User(
        email=TEST_USER_PUSH_OFF, hashed_password=get_password_hash("password123"), role="user"
    )
    db.add_all([user_push_on, user_push_off])
    db.commit()

    site = Site(name=TEST_SITE, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)

    db.add_all(
        [
            SiteMember(site_id=site.id, user_id=user_push_on.id, role="owner"),
            SiteMember(site_id=site.id, user_id=user_push_off.id, role="member"),
            NotificationPreference(user_id=user_push_on.id, channel="push", enabled=True),
        ]
    )
    db.commit()

    profile = DeviceProfile(name=TEST_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=TEST_DEVICE, name="Dispositivo notificaciones", site_id=site.id, profile_id=profile.id
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()

    user_push_on_id, user_push_off_id = user_push_on.id, user_push_off.id
    db.close()

    try:
        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE, secret=secret)
        response = scenario_overload(sim, sequence=1, max_current_a=10.0)
        assert response.status_code == 200
        assert response.json()["command"] is not None

        db = SessionLocal()
        notifications = db.query(Notification).filter(
            Notification.user_id.in_([user_push_on_id, user_push_off_id])
        ).all()
        db.close()

        notified_user_ids = {n.user_id for n in notifications}
        assert notified_user_ids == {user_push_on_id, user_push_off_id}  # ambos, in-app siempre

        assert recorder.sent_to == [user_push_on_id]  # push solo para quien lo habilito
    finally:
        _cleanup()


def test_user_with_in_app_disabled_receives_no_notification() -> None:
    _cleanup()
    db = SessionLocal()
    user = User(
        email=TEST_USER_IN_APP_OFF, hashed_password=get_password_hash("password123"), role="user"
    )
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
            NotificationPreference(user_id=user.id, channel="in_app", enabled=False),
        ]
    )
    db.commit()

    profile = DeviceProfile(name=TEST_SITE, max_current_a=10.0)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(
        public_id=TEST_DEVICE, name="Dispositivo notificaciones", site_id=site.id, profile_id=profile.id
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()

    user_id = user.id
    db.close()

    try:
        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE, secret=secret)
        response = scenario_overload(sim, sequence=1, max_current_a=10.0)
        assert response.status_code == 200

        db = SessionLocal()
        count = db.query(Notification).filter(Notification.user_id == user_id).count()
        db.close()
        assert count == 0
    finally:
        _cleanup()
