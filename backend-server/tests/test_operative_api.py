from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_receive_telemetry_device_not_found():
    # Probar envío de telemetría de un dispositivo no registrado
    payload = {
        "device_id": "DEV-UNREGISTERED",
        "voltage": 127.0,
        "current": 2.5,
        "power": 317.5,
        "frequency": 60.0,
        "power_factor": 0.98,
        "energy": 0.5
    }
    response = client.post("/api/v1/telemetry/readings", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Dispositivo 'DEV-UNREGISTERED' no registrado."