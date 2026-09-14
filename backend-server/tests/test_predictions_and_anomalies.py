from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

import app.config as config_module
from app.core.security import create_access_token, get_password_hash
from app.db import SessionLocal
from app.main import app
from app.models.entities import AnomalyAlert, Device, User
from app.services.device_auth import issue_device_credential
from simulator.device_simulator import DeviceSimulator

client = TestClient(app)

TEST_DEVICE_PREDICTION = "VG-PREDICTION-TEST"
TEST_DEVICE_ANOMALY = "VG-ANOMALY-TEST"
TEST_ADMIN_EMAIL = "predictions_admin_test@voltguard.com"


def _cleanup() -> None:
    db = SessionLocal()
    for public_id in (TEST_DEVICE_PREDICTION, TEST_DEVICE_ANOMALY):
        device = db.query(Device).filter(Device.public_id == public_id).first()
        if device:
            db.delete(device)
            db.commit()
    db.query(User).filter(User.email == TEST_ADMIN_EMAIL).delete()
    db.commit()
    db.close()


def _day_at_noon(days_ago: int) -> datetime:
    now = datetime.now(UTC)
    return (now - timedelta(days=days_ago)).replace(hour=12, minute=0, second=0, microsecond=0)


def test_prediction_matches_hand_calculation_within_10_percent() -> None:
    """Consumo diario constante de 2 kWh/dia: la proyeccion mensual debe
    acercarse a 2 kWh * 30 = 60 kWh, dentro del margen de error del 10%
    que exige la propuesta."""
    _cleanup()
    db = SessionLocal()
    device = Device(public_id=TEST_DEVICE_PREDICTION, name="Dispositivo prediccion")
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()
    device_id = device.id
    db.close()

    try:
        sim = DeviceSimulator(client=client, public_id=TEST_DEVICE_PREDICTION, secret=secret)
        # dia -6 (baseline) = 0 kWh; dias -5..-1 suben 2 kWh cada uno.
        for offset in range(6, -1, -1):
            energy = 0.0 if offset == 6 else 2.0 * (6 - offset)
            response = sim.send_telemetry(
                sequence=6 - offset,
                voltage_v=127.0,
                current_a=2.0,
                energy_kwh=energy,
                timestamp=_day_at_noon(offset),
            )
            assert response.status_code == 200

        # El dispositivo no esta vinculado a ningun sitio (la autorizacion
        # de /api/v1/app/* ya se prueba a fondo en test_app_api.py), asi
        # que aqui se llama al servicio directo para validar el numero.
        db = SessionLocal()
        from app.services.predictions import get_or_generate_prediction

        prediction = get_or_generate_prediction(db, db.query(Device).filter(Device.id == device_id).one())
        db.close()

        expected_kwh = 60.0
        error = abs(prediction.projected_kwh - expected_kwh) / expected_kwh
        assert error < 0.10
    finally:
        _cleanup()


def _admin_token() -> str:
    db = SessionLocal()
    user = User(
        email=TEST_ADMIN_EMAIL, hashed_password=get_password_hash("password123"), role="admin"
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return create_access_token(subject=str(user_id), role="admin")


def _run_anomaly_scenario() -> int:
    """Crea un dispositivo, manda 10 lecturas estables y una anomala.
    Devuelve el device_id."""
    db = SessionLocal()
    device = Device(public_id=TEST_DEVICE_ANOMALY, name="Dispositivo anomalias")
    db.add(device)
    db.commit()
    db.refresh(device)
    secret = issue_device_credential(device)
    db.commit()
    device_id = device.id
    db.close()

    sim = DeviceSimulator(client=client, public_id=TEST_DEVICE_ANOMALY, secret=secret)
    # 30 lecturas estables con jitter pequeno y determinista (197-203 W) —
    # IsolationForest necesita suficiente historial variado para aislar un
    # outlier real de forma confiable; con solo 10 puntos casi idénticos no
    # construye splits utiles (falso negativo observado en pruebas).
    stable_powers = [200.0 + ((i % 7) - 3) for i in range(30)]
    for i, power in enumerate(stable_powers):
        response = sim.send_telemetry(sequence=i + 1, power_w=power, energy_kwh=float(i))
        assert response.status_code == 200

    anomalous_response = sim.send_telemetry(sequence=len(stable_powers) + 1, power_w=5000.0)
    assert anomalous_response.status_code == 200
    return device_id


def test_anomaly_alert_created_and_visible_to_admin_rule_based() -> None:
    _cleanup()
    try:
        device_id = _run_anomaly_scenario()

        db = SessionLocal()
        alerts = db.query(AnomalyAlert).filter(AnomalyAlert.device_id == device_id).all()
        db.close()
        assert len(alerts) >= 1
        assert alerts[0].detector == "rule_based"

        token = _admin_token()
        response = client.get("/api/v1/admin/anomalies", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert any(a["device_id"] == device_id for a in response.json())
    finally:
        _cleanup()


def test_anomaly_alert_created_with_isolation_forest_strategy() -> None:
    _cleanup()
    original_strategy = config_module.settings.anomaly_detector
    config_module.settings.anomaly_detector = "isolation_forest"
    try:
        device_id = _run_anomaly_scenario()

        db = SessionLocal()
        alerts = db.query(AnomalyAlert).filter(AnomalyAlert.device_id == device_id).all()
        db.close()
        assert len(alerts) >= 1
        assert alerts[0].detector == "isolation_forest"
    finally:
        config_module.settings.anomaly_detector = original_strategy
        _cleanup()
