import logging

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.entities import Device, DeviceProfile, Event
from app.services.device_auth import issue_device_credential
from simulator.device_simulator import DeviceSimulator
from simulator.scenarios import (
    scenario_normal,
    scenario_overload,
    scenario_overvoltage,
    scenario_undervoltage,
)

client = TestClient(app)

TEST_PUBLIC_ID = "VG-RULES-ENGINE-TEST"


def _cleanup() -> None:
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).first()
    if device:
        db.query(Event).filter(Event.device_id == device.id).delete()
        db.commit()
        db.delete(device)  # cascada: telemetry_readings, commands, credential
        db.commit()
    db.query(DeviceProfile).filter(DeviceProfile.name == TEST_PUBLIC_ID).delete()
    db.commit()
    db.close()


def _make_device(
    *,
    max_current_a: float = 15.0,
    min_voltage_v: float | None = None,
    max_voltage_v: float | None = None,
) -> str:
    db = SessionLocal()
    profile = DeviceProfile(
        name=TEST_PUBLIC_ID,
        max_current_a=max_current_a,
        min_voltage_v=min_voltage_v,
        max_voltage_v=max_voltage_v,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    device = Device(public_id=TEST_PUBLIC_ID, name="Dispositivo de pruebas motor de reglas", profile_id=profile.id)
    db.add(device)
    db.commit()
    db.refresh(device)
    plain_secret = issue_device_credential(device)
    db.commit()
    db.close()
    return plain_secret


def _reload_device() -> Device:
    db = SessionLocal()
    device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).one()
    db.expunge(device)
    db.close()
    return device


def test_overload_triggers_shutdown_and_locks_device() -> None:
    _cleanup()
    secret = _make_device(max_current_a=10.0)
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = scenario_overload(sim, sequence=1, max_current_a=10.0)
        assert response.status_code == 200
        body = response.json()
        assert body["command"] is not None
        assert body["command"]["type"] == "SET_RELAY_OFF"

        device = _reload_device()
        assert device.desired_state == "OFF"
        assert device.is_locked_out is True

        db = SessionLocal()
        events = db.query(Event).filter(Event.device_id == device.id).all()
        db.close()
        assert len(events) == 1
        assert events[0].type == "CRITICAL_OVERLOAD"
    finally:
        _cleanup()


def test_overvoltage_triggers_shutdown() -> None:
    _cleanup()
    secret = _make_device(max_voltage_v=135.0)
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = scenario_overvoltage(sim, sequence=1, max_voltage_v=135.0)
        assert response.status_code == 200
        assert response.json()["command"]["type"] == "SET_RELAY_OFF"

        db = SessionLocal()
        device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).one()
        events = db.query(Event).filter(Event.device_id == device.id).all()
        db.close()
        assert device.is_locked_out is True
        assert events[0].type == "CRITICAL_OVERVOLTAGE"
    finally:
        _cleanup()


def test_undervoltage_triggers_shutdown() -> None:
    _cleanup()
    secret = _make_device(min_voltage_v=100.0)
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = scenario_undervoltage(sim, sequence=1, min_voltage_v=100.0)
        assert response.status_code == 200
        assert response.json()["command"]["type"] == "SET_RELAY_OFF"

        db = SessionLocal()
        device = db.query(Device).filter(Device.public_id == TEST_PUBLIC_ID).one()
        events = db.query(Event).filter(Event.device_id == device.id).all()
        db.close()
        assert device.is_locked_out is True
        assert events[0].type == "CRITICAL_UNDERVOLTAGE"
    finally:
        _cleanup()


def test_normal_telemetry_with_profile_does_not_trigger_anything() -> None:
    _cleanup()
    secret = _make_device(max_current_a=10.0, min_voltage_v=100.0, max_voltage_v=135.0)
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        response = scenario_normal(sim, sequence=1)
        assert response.status_code == 200
        assert response.json()["command"] is None

        device = _reload_device()
        assert device.is_locked_out is False

        db = SessionLocal()
        events = db.query(Event).filter(Event.device_id == device.id).count()
        db.close()
        assert events == 0
    finally:
        _cleanup()


def test_no_automatic_reactivation_after_lockout() -> None:
    _cleanup()
    secret = _make_device(max_current_a=10.0)
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        overload_response = scenario_overload(sim, sequence=1, max_current_a=10.0)
        lockout_command_id = overload_response.json()["command"]["id"]

        # Telemetria normal inmediatamente despues del corte: no debe
        # generarse un comando NUEVO ni un segundo evento. Si la API
        # devuelve "command" aca es la reentrega del mismo apagado
        # todavia pendiente (ver receive_telemetry: una vez que
        # evaluate_and_act no genera un comando propio, se reusa el
        # PENDING existente para que llegue mas rapido al dispositivo),
        # no un redisparo de la regla de corte.
        normal_response = scenario_normal(sim, sequence=2)
        assert normal_response.status_code == 200
        returned_command = normal_response.json()["command"]
        if returned_command is not None:
            assert returned_command["id"] == lockout_command_id

        device = _reload_device()
        assert device.desired_state == "OFF"  # sigue apagado, no se reactivo solo

        db = SessionLocal()
        events = db.query(Event).filter(Event.device_id == device.id).all()
        db.close()
        assert len(events) == 1  # no se genero un segundo evento por la lectura repetida
    finally:
        _cleanup()


def test_reaction_time_is_under_500ms(caplog: pytest.LogCaptureFixture) -> None:
    """Métrica de la propuesta: <500ms desde que la API recibe la lectura
    hasta que emite la orden de apagado — medido con el log real que deja
    `evaluate_and_act`, no estimado."""
    _cleanup()
    secret = _make_device(max_current_a=10.0)
    sim = DeviceSimulator(client=client, public_id=TEST_PUBLIC_ID, secret=secret)
    try:
        with caplog.at_level(logging.WARNING, logger="voltguard.iot"):
            response = scenario_overload(sim, sequence=1, max_current_a=10.0)
        assert response.status_code == 200

        reaction_records = [r for r in caplog.records if r.message == "critical_event_triggered"]
        assert len(reaction_records) == 1
        reaction_ms = reaction_records[0].__dict__["reaction_ms"]
        assert reaction_ms < 500
    finally:
        _cleanup()
