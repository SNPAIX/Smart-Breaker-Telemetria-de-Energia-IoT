from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.entities import Command, Device, TelemetryReading
from app.services.device_auth import issue_device_credential
from simulator.device_simulator import DeviceSimulator
from simulator.scenarios import (
    scenario_duplicate_sequence,
    scenario_invalid_credentials,
    scenario_malformed_telemetry,
    scenario_normal,
    scenario_out_of_order_telemetry,
    scenario_relay_command_failure,
)

client = TestClient(app)

TEST_PUBLIC_ID = "VG-IOT-API-TEST"


def _cleanup() -> None:
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).first()
    if device:
        db.query(Command).filter(Command.device_id == device.id).delete()
        db.query(TelemetryReading).filter(TelemetryReading.device_id == device.id).delete()
        db.commit()
        db.delete(device)
        db.commit()
    db.close()


def _make_device() -> str:
    """Crea el dispositivo de prueba y devuelve solo el secreto en texto
    plano — nunca el objeto ORM: al cerrarse esta sesión, cualquier
    atributo no cargado de antemano dispararía un DetachedInstanceError en
    quien lo use después. Los tests que necesitan datos del dispositivo lo
    vuelven a consultar en su propia sesión, ver `_device_id()`."""
    db = SessionLocal()
    device = Device(public_id=TEST_PUBLIC_ID, name="Dispositivo de prueba API IoT")
    db.add(device)
    db.commit()
    db.refresh(device)
    plain_secret = issue_device_credential(device)
    db.commit()
    db.close()
    return plain_secret


def _device_id() -> int:
    db = SessionLocal()
    device_id: int | None = db.query(Device.id).filter(Device.public_id == TEST_PUBLIC_ID).scalar()
    db.close()
    assert device_id is not None
    return device_id


def test_normal_scenario_telemetry_heartbeat_commands_and_ack() -> None:
    _cleanup()
    secret = _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = scenario_normal(sim, sequence=1)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        heartbeat_response = sim.send_heartbeat()
        assert heartbeat_response.status_code == 200

        db = SessionLocal()
        refreshed = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).one()
        assert refreshed.last_seen_at is not None

        pending_command = Command(device_id=refreshed.id, type="SET_RELAY_ON", status="PENDING")
        db.add(pending_command)
        db.commit()
        command_id = pending_command.id
        db.close()

        pending_response = sim.list_pending_commands()
        assert pending_response.status_code == 200
        pending = pending_response.json()
        assert len(pending) == 1
        assert pending[0]["id"] == command_id

        ack_response = sim.ack_command(command_id, actual_state="ON")
        assert ack_response.status_code == 200
        assert ack_response.json()["actual_state"] == "ON"

        db = SessionLocal()
        acked_command = db.query(Command).filter(Command.id == command_id).one()
        assert acked_command.status == "ACKED"
        assert acked_command.acked_at is not None
        db.close()
    finally:
        _cleanup()


def test_ack_unknown_command_returns_404() -> None:
    _cleanup()
    secret = _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = sim.ack_command(999999, actual_state="ON")
        assert response.status_code == 404
    finally:
        _cleanup()


def test_invalid_credentials_are_rejected_on_every_endpoint() -> None:
    _cleanup()
    _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret="secreto-incorrecto")
    try:
        assert scenario_invalid_credentials(sim, sequence=1).status_code == 401
        assert sim.send_heartbeat().status_code == 401
        assert sim.list_pending_commands().status_code == 401
        assert sim.ack_command(1, actual_state="ON").status_code == 401
    finally:
        _cleanup()


def test_malformed_telemetry_returns_422_and_persists_nothing() -> None:
    _cleanup()
    secret = _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = scenario_malformed_telemetry(sim)
        assert response.status_code == 422

        db = SessionLocal()
        count = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.device_id == _device_id())
            .count()
        )
        db.close()
        assert count == 0
    finally:
        _cleanup()


def test_duplicate_sequence_does_not_duplicate_the_reading() -> None:
    _cleanup()
    secret = _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        first, duplicate = scenario_duplicate_sequence(sim, sequence=1)
        assert first.status_code == 200
        assert first.json()["status"] == "success"
        assert duplicate.status_code == 200
        assert duplicate.json()["status"] == "duplicate"

        db = SessionLocal()
        count = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.device_id == _device_id(), TelemetryReading.sequence == 1)
            .count()
        )
        db.close()
        assert count == 1
    finally:
        _cleanup()


def test_out_of_order_telemetry_is_persisted_and_flagged() -> None:
    _cleanup()
    secret = _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        latest, out_of_order = scenario_out_of_order_telemetry(
            sim, first_sequence=5, out_of_order_sequence=2
        )
        assert latest.status_code == 200
        assert latest.json()["is_out_of_order"] is False
        assert out_of_order.status_code == 200
        assert out_of_order.json()["is_out_of_order"] is True

        db = SessionLocal()
        sequences = {
            r.sequence
            for r in db.query(TelemetryReading).filter(
                TelemetryReading.device_id == _device_id()
            )
        }
        db.close()
        assert sequences == {5, 2}
    finally:
        _cleanup()


def test_relay_command_failure_is_persisted_not_hidden() -> None:
    _cleanup()
    secret = _make_device()
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        db = SessionLocal()
        command = Command(device_id=_device_id(), type="SET_RELAY_ON", status="PENDING")
        db.add(command)
        db.commit()
        command_id = command.id
        db.close()

        response = scenario_relay_command_failure(sim, command_id, desired_state="ON")
        assert response.status_code == 200
        # El firmware reportó lo contrario de lo pedido: se persiste tal
        # cual, no se "corrige" para que coincida con desired_state.
        assert response.json()["actual_state"] == "OFF"
        assert response.json()["desired_state"] == "OFF"  # default de Device, nunca se pidió ON
    finally:
        _cleanup()
