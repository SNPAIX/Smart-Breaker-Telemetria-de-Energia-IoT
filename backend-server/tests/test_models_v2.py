from app.db import SessionLocal
from app.models.entities import (
    Device,
    DeviceProfile,
    Site,
    SiteMember,
    TelemetryReading,
    User,
)

TEST_EMAIL = "models_v2_test@voltguard.com"
TEST_PUBLIC_ID = "VG-MODELS-V2-TEST"
TEST_SITE_NAME = "Taller de pruebas (models_v2_test)"


def _cleanup() -> None:
    """Sin rollback automático entre corridas (Postgres persistente, no
    sqlite en memoria), así que se limpia antes de cada prueba en vez de
    asumir una base vacía. Borra en orden hijo -> padre para no depender
    de cascadas que no todas las relaciones tienen configuradas."""
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).first()
    if device:
        db.delete(device)
        db.commit()
    profile = db.query(DeviceProfile).filter(DeviceProfile.name == TEST_SITE_NAME).first()
    if profile:
        db.delete(profile)
        db.commit()
    site = db.query(Site).filter(Site.name == TEST_SITE_NAME).first()
    if site:
        db.delete(site)  # cascada a SiteMember (Site.members)
        db.commit()
    user = db.query(User).filter(User.email == TEST_EMAIL).first()
    if user:
        db.delete(user)  # cascada a SiteMember (User.site_memberships)
        db.commit()
    db.close()


def test_site_membership_and_device_relationships_round_trip() -> None:
    """Prueba de punta a punta del esquema v2: User -> SiteMember -> Site ->
    Device -> TelemetryReading, confirmando que cada relación se puede leer
    de vuelta tal como quedó definida en app/models/entities.py."""
    _cleanup()
    db = SessionLocal()
    try:
        user = User(email=TEST_EMAIL, hashed_password="hash-no-real", role="user")
        db.add(user)
        db.commit()
        db.refresh(user)

        site = Site(name=TEST_SITE_NAME, kind="taller")
        db.add(site)
        db.commit()
        db.refresh(site)

        membership = SiteMember(site_id=site.id, user_id=user.id, role="owner")
        db.add(membership)
        db.commit()

        profile = DeviceProfile(site_id=site.id, name=TEST_SITE_NAME, max_current_a=12.5)
        db.add(profile)
        db.commit()
        db.refresh(profile)

        device = Device(
            public_id=TEST_PUBLIC_ID,
            name="Bomba de agua",
            site_id=site.id,
            profile_id=profile.id,
        )
        db.add(device)
        db.commit()
        db.refresh(device)

        reading = TelemetryReading(
            device_id=device.id,
            sequence=1,
            voltage=127.4,
            current=1.82,
            power=219.7,
            energy=4.281,
        )
        db.add(reading)
        db.commit()

        # Releer todo desde cero (sesión nueva) para confirmar que las
        # relaciones se resuelven desde la base, no desde objetos en memoria.
        db.close()
        db = SessionLocal()

        reloaded_user = db.query(User).filter(User.email == TEST_EMAIL).one()
        assert len(reloaded_user.site_memberships) == 1
        assert reloaded_user.site_memberships[0].role == "owner"
        assert reloaded_user.site_memberships[0].site.name == TEST_SITE_NAME

        reloaded_site = reloaded_user.site_memberships[0].site
        assert len(reloaded_site.devices) == 1
        reloaded_device = reloaded_site.devices[0]
        assert reloaded_device.public_id == TEST_PUBLIC_ID
        assert reloaded_device.profile is not None
        assert reloaded_device.profile.max_current_a == 12.5
        assert len(reloaded_device.telemetry_readings) == 1
        assert reloaded_device.telemetry_readings[0].sequence == 1
    finally:
        db.close()
        _cleanup()
