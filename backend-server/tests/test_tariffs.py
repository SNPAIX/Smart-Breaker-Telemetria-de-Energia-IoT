from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.entities import Device, DeviceProfile, Site, Tariff, TelemetryReading
from app.services.costs import compute_cost_breakdown

client = TestClient(app)

TEST_SITE = "Sitio tarifas (test_tariffs)"
TEST_DEVICE = "VG-TARIFFS-TEST"


def _cleanup() -> None:
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_DEVICE).first()
    if device:
        db.delete(device)
        db.commit()
    site = db.query(Site).filter(Site.name == TEST_SITE).first()
    if site:
        db.query(Tariff).filter(Tariff.site_id == site.id).delete()
        db.commit()
        db.delete(site)
        db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name == TEST_SITE).delete()
    db.commit()
    db.close()


def _day_at_noon(days_ago: int) -> datetime:
    now = datetime.now(UTC)
    return (now - timedelta(days=days_ago)).replace(hour=12, minute=0, second=0, microsecond=0)


def test_cost_is_prorated_when_tariff_changes_mid_period() -> None:
    _cleanup()
    db = SessionLocal()
    try:
        site = Site(name=TEST_SITE, kind="taller")
        db.add(site)
        db.commit()
        db.refresh(site)

        device = Device(public_id=TEST_DEVICE, name="Dispositivo tarifas", site_id=site.id)
        db.add(device)
        db.commit()
        db.refresh(device)

        # Baseline (dia -3): 0 kWh acumulado. Dia -2: sube a 1.0 kWh (consumo
        # de ese dia = 1 kWh). Dia -1: sube a 3.0 kWh (consumo = 2 kWh).
        day_minus_3 = _day_at_noon(3)
        day_minus_2 = _day_at_noon(2)
        day_minus_1 = _day_at_noon(1)

        db.add_all(
            [
                TelemetryReading(
                    device_id=device.id, sequence=1, voltage=127.0, current=1.0, power=127.0,
                    energy=0.0, recorded_at=day_minus_3,
                ),
                TelemetryReading(
                    device_id=device.id, sequence=2, voltage=127.0, current=1.0, power=127.0,
                    energy=1.0, recorded_at=day_minus_2,
                ),
                TelemetryReading(
                    device_id=device.id, sequence=3, voltage=127.0, current=1.0, power=127.0,
                    energy=3.0, recorded_at=day_minus_1,
                ),
            ]
        )
        db.commit()

        # Tarifa A vigente desde antes del rango analizado (cubre dia -2).
        # Tarifa B empieza justo al inicio del dia -1 (la cierra de facto).
        db.add(
            Tariff(
                site_id=site.id,
                currency="MXN",
                price_per_kwh=2.0,
                valid_from=day_minus_3 - timedelta(days=1),
                valid_to=day_minus_1.replace(hour=0, minute=0, second=0, microsecond=0),
            )
        )
        db.add(
            Tariff(
                site_id=site.id,
                currency="MXN",
                price_per_kwh=3.0,
                valid_from=day_minus_1.replace(hour=0, minute=0, second=0, microsecond=0),
                valid_to=None,
            )
        )
        db.commit()

        breakdown = compute_cost_breakdown(db, device, days=14)

        # dia -3: primer dia del rango, una sola lectura -> sin spread que
        # estimar, 0 kWh. dia -2: 1 kWh * 2.0 = 2.0 ; dia -1: 2 kWh * 3.0 =
        # 6.0 ; total = 8.0 (el dia -3 no descartado, pero no suma nada).
        assert breakdown.days_analyzed == 3
        assert breakdown.total_kwh == 3.0
        assert breakdown.total_cost == 8.0
        assert breakdown.used_default_tariff is False

        # Si no se prorrateara y se aplicara la tarifa vigente HOY (3.0) a
        # todo el consumo, el total habria sido 9.0, no 8.0 — confirma que
        # el prorrateo real esta ocurriendo, no una casualidad aritmetica.
        assert breakdown.total_cost != 3.0 * 3.0
    finally:
        db.close()
        _cleanup()


def test_admin_tariff_crud_and_history() -> None:
    from app.core.security import create_access_token, get_password_hash
    from app.models.entities import User

    _cleanup()
    db = SessionLocal()
    admin = User(
        email="tariffs_admin_test@voltguard.com",
        hashed_password=get_password_hash("password123"),
        role="admin",
    )
    db.add(admin)
    db.commit()
    admin_id = admin.id

    site = Site(name=TEST_SITE, kind="taller")
    db.add(site)
    db.commit()
    db.refresh(site)
    site_id = site.id
    db.close()

    token = create_access_token(subject=str(admin_id), role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        first = client.post(
            f"/api/v1/admin/sites/{site_id}/tariffs",
            headers=headers,
            json={"price_per_kwh": 2.0},
        )
        assert first.status_code == 201
        assert first.json()["valid_to"] is None

        second = client.post(
            f"/api/v1/admin/sites/{site_id}/tariffs",
            headers=headers,
            json={"price_per_kwh": 2.5},
        )
        assert second.status_code == 201

        history = client.get(f"/api/v1/admin/sites/{site_id}/tariffs", headers=headers)
        assert history.status_code == 200
        tariffs = history.json()
        assert len(tariffs) == 2
        closed = next(t for t in tariffs if t["id"] == first.json()["id"])
        assert closed["valid_to"] is not None  # la primera tarifa quedo cerrada
    finally:
        db = SessionLocal()
        db.query(User).filter(User.email == "tariffs_admin_test@voltguard.com").delete()
        db.commit()
        db.close()
        _cleanup()
