from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import Alert, Device, Reading, User

client = TestClient(app)


def _admin_headers() -> dict[str, str]:
    """Los endpoints de /api/v1/dispositivos/* requieren rol admin (RBAC)."""
    db = SessionLocal()
    existing = db.query(User).filter(User.email == "admin_intel_test@voltguard.com").first()
    if existing is None:
        admin_user = User(
            email="admin_intel_test@voltguard.com",
            hashed_password=get_password_hash("password123"),
            role="admin",
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        admin_id = admin_user.id
    else:
        admin_id = existing.id
    db.close()

    token = create_access_token(subject=str(admin_id), role="admin")
    return {"Authorization": f"Bearer {token}"}


def _ensure_device(device_id: str, max_current_threshold: float = 15.0) -> None:
    db = SessionLocal()
    existing = db.query(Device).filter(Device.id == device_id).first()
    if existing is None:
        db.add(
            Device(
                id=device_id,
                name="Dispositivo de prueba",
                max_current_threshold=max_current_threshold,
                auto_cutoff_enabled=True,
                relay_status=True,
            )
        )
        db.commit()
    else:
        existing.max_current_threshold = max_current_threshold
        existing.auto_cutoff_enabled = True
        existing.relay_status = True
        db.commit()
    db.close()


def _base_payload(device_id: str, current: float, power: float = 300.0) -> dict[str, float | str]:
    return {
        "device_id": device_id,
        "voltage": 127.0,
        "current": current,
        "power": power,
        "frequency": 60.0,
        "power_factor": 0.98,
        "energy": 0.5,
    }


def test_overload_reading_trips_relay_and_logs_safety_event():
    device_id = "DEV-TEST-CUTOFF-01"
    _ensure_device(device_id, max_current_threshold=15.0)

    # La ingesta de telemetría es del ESP32 (sin JWT de usuario), no lleva headers
    response = client.post(
        "/api/v1/telemetry/readings",
        json=_base_payload(device_id, current=20.0),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "critical_overload"
    assert data["relay_status"] is False

    events = client.get(
        f"/api/v1/dispositivos/{device_id}/eventos-seguridad", headers=_admin_headers()
    )
    assert events.status_code == 200
    events_data = events.json()
    assert len(events_data) >= 1
    assert events_data[0]["event_type"] == "CRITICAL_OVERLOAD"
    assert events_data[0]["current"] == 20.0


def test_safety_events_require_admin_auth():
    device_id = "DEV-TEST-CUTOFF-01"
    response = client.get(f"/api/v1/dispositivos/{device_id}/eventos-seguridad")
    assert response.status_code == 401


def test_list_all_safety_events_and_alerts():
    """Cubre las variantes 'globales' (sin filtrar por dispositivo) de
    ambos listados, usadas por un dashboard que ve todos los eventos."""
    device_id = "DEV-TEST-CUTOFF-ALL-01"
    _ensure_device(device_id, max_current_threshold=15.0)

    client.post(
        "/api/v1/telemetry/readings",
        json=_base_payload(device_id, current=20.0),
    )

    events = client.get("/api/v1/dispositivos/eventos-seguridad/todos", headers=_admin_headers())
    assert events.status_code == 200
    assert any(e["device_id"] == device_id for e in events.json())

    alerts = client.get("/api/v1/dispositivos/alertas/todas", headers=_admin_headers())
    assert alerts.status_code == 200


def test_normal_reading_does_not_trip_relay():
    device_id = "DEV-TEST-CUTOFF-02"
    _ensure_device(device_id, max_current_threshold=15.0)

    response = client.post(
        "/api/v1/telemetry/readings",
        json=_base_payload(device_id, current=5.0),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["relay_status"] is True


def test_safety_threshold_can_be_reconfigured():
    device_id = "DEV-TEST-THRESHOLD-01"
    _ensure_device(device_id, max_current_threshold=15.0)

    response = client.patch(
        f"/api/v1/dispositivos/{device_id}/umbral-seguridad",
        json={"max_current_threshold": 10.0, "auto_cutoff_enabled": True},
        headers=_admin_headers(),
    )
    assert response.status_code == 200
    assert response.json()["max_current_threshold"] == 10.0

    # Una lectura de 12A ahora debe disparar el corte con el nuevo umbral
    response = client.post(
        "/api/v1/telemetry/readings",
        json=_base_payload(device_id, current=12.0),
    )
    assert response.json()["status"] == "critical_overload"


def test_anomalous_reading_creates_alert():
    device_id = "DEV-TEST-ANOMALY-01"
    _ensure_device(device_id, max_current_threshold=15.0)

    # La base de pruebas es persistente entre corridas: si no limpiamos las
    # lecturas viejas de este dispositivo, el detector calcula el
    # promedio/desviación sobre un historial contaminado de ejecuciones
    # anteriores, y el pico de 900W puede dejar de verse "anómalo" frente
    # a ese ruido acumulado.
    db = SessionLocal()
    db.query(Alert).filter(Alert.device_id == device_id).delete()
    db.query(Reading).filter(Reading.device_id == device_id).delete()
    db.commit()
    db.close()

    # Historial estable de ~60W
    for _ in range(6):
        client.post(
            "/api/v1/telemetry/readings",
            json=_base_payload(device_id, current=1.0, power=60.0),
        )

    # Lectura muy por encima del historial reciente
    client.post(
        "/api/v1/telemetry/readings",
        json=_base_payload(device_id, current=1.0, power=900.0),
    )

    alerts = client.get(f"/api/v1/dispositivos/{device_id}/alertas", headers=_admin_headers())
    assert alerts.status_code == 200
    assert any(a["detector"] == "rule_based" for a in alerts.json())


def test_cost_projection_for_device_with_no_readings():
    device_id = "DEV-TEST-COST-EMPTY-01"
    _ensure_device(device_id)

    response = client.get(
        f"/api/v1/dispositivos/{device_id}/proyeccion-costo", headers=_admin_headers()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["days_analyzed"] == 0
    assert data["projected_monthly_cost_mxn"] == 0.0


def test_cost_projection_unknown_device_returns_404():
    response = client.get(
        "/api/v1/dispositivos/DEV-DOES-NOT-EXIST/proyeccion-costo", headers=_admin_headers()
    )
    assert response.status_code == 404


def test_cost_projection_computes_trend_from_daily_energy_deltas():
    device_id = "DEV-TEST-COST-TREND-01"
    _ensure_device(device_id)

    db = SessionLocal()
    now = datetime.now(UTC)
    # Consumo acumulado (kWh) creciendo cada día: cada delta ~1000Wh = 1kWh/día
    for day_offset, cumulative_kwh in enumerate([0.0, 1.0, 2.0, 3.0]):
        db.add(
            Reading(
                device_id=device_id,
                voltage=127.0,
                current=1.0,
                power=100.0,
                frequency=60.0,
                power_factor=1.0,
                energy=cumulative_kwh,
                recorded_at=now - timedelta(days=3 - day_offset, hours=1),
            )
        )
    db.commit()
    db.close()

    response = client.get(
        f"/api/v1/dispositivos/{device_id}/proyeccion-costo?days=10", headers=_admin_headers()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["days_analyzed"] == 3
    assert data["avg_daily_energy_wh"] == 1000.0
    assert data["projected_monthly_cost_mxn"] > 0.0