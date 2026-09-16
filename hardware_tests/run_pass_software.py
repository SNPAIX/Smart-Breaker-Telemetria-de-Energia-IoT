"""Corre el PASS software del plan HIL (docs/claude/HIL_TEST_PLAN.md) contra
un backend VoltGuard real, sin necesitar el ESP32-C3 físico — reproduce el
mismo contrato HTTP que habla el firmware (ino/iot_client.cpp) con
peticiones HTTP reales.

Requiere:
- Un backend corriendo y accesible en VOLTGUARD_BACKEND_URL
  (default http://localhost:8000).
- Una cuenta admin ya existente (VOLTGUARD_ADMIN_EMAIL /
  VOLTGUARD_ADMIN_PASSWORD) — este script no crea el primer admin de la
  plataforma, eso es un paso de arranque manual (ver docs/despliegue.md,
  etapa 15).

Uso:
    pip install httpx
    VOLTGUARD_ADMIN_EMAIL=admin@ejemplo.com VOLTGUARD_ADMIN_PASSWORD=... \\
        python hardware_tests/run_pass_software.py
"""
from __future__ import annotations

import os
import sys
import time
import uuid

import httpx

BACKEND_URL = os.environ.get("VOLTGUARD_BACKEND_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("VOLTGUARD_ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("VOLTGUARD_ADMIN_PASSWORD")

results: list[tuple[str, bool]] = []


def check(name: str, condition: bool) -> None:
    results.append((name, condition))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")


def main() -> int:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("Faltan VOLTGUARD_ADMIN_EMAIL / VOLTGUARD_ADMIN_PASSWORD.", file=sys.stderr)
        return 2

    client = httpx.Client(base_url=BACKEND_URL, timeout=10.0)

    login = client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    check("login de administrador", login.status_code == 200)
    if login.status_code != 200:
        return 1
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    public_id = f"VG-HIL-{uuid.uuid4().hex[:8].upper()}"

    # Perfil con un umbral bajo a propósito, para poder disparar el evento
    # crítico con una lectura de prueba sin necesitar una sobrecarga real.
    profile_response = client.post(
        "/api/v1/admin/profiles",
        headers=admin_headers,
        json={"name": public_id, "max_current_a": 10.0},
    )
    check("creacion de perfil de prueba", profile_response.status_code == 201)
    if profile_response.status_code != 201:
        return 1
    profile_id = profile_response.json()["id"]

    device_response = client.post(
        "/api/v1/admin/devices",
        headers=admin_headers,
        json={"public_id": public_id, "name": "Dispositivo HIL software", "profile_id": profile_id},
    )
    check("alta de dispositivo via admin", device_response.status_code == 201)
    if device_response.status_code != 201:
        return 1
    device_body = device_response.json()
    device_id = device_body["id"]
    device_headers = {"Authorization": f"Device {public_id}:{device_body['secret']}"}

    bad_auth = client.post(
        "/api/v1/iot/heartbeat", headers={"Authorization": f"Device {public_id}:incorrecto"}
    )
    check("credencial invalida rechazada (401)", bad_auth.status_code == 401)

    telemetry_body = {
        "sequence": 1,
        "timestamp": "2026-01-01T00:00:00Z",
        "voltage_v": 127.0,
        "current_a": 1.5,
        "power_w": 190.0,
        "energy_kwh": 1.0,
        "frequency_hz": 60.0,
        "power_factor": 0.95,
        "relay_state": "ON",
    }
    telemetry_response = client.post(
        "/api/v1/iot/telemetry", headers=device_headers, json=telemetry_body
    )
    check("telemetria aceptada", telemetry_response.status_code == 200)

    device_after = client.get(f"/api/v1/admin/devices/{device_id}", headers=admin_headers)
    check(
        "last_seen_at actualizado",
        device_after.status_code == 200 and device_after.json().get("last_seen_at") is not None,
    )

    # Por encima del umbral del perfil (10.0 A) pero dentro del rango
    # valido del contrato de telemetria (le=100.0), sin necesitar una
    # sobrecarga real.
    overload_body = dict(telemetry_body, sequence=2, current_a=50.0)
    started_at = time.monotonic()
    overload_response = client.post(
        "/api/v1/iot/telemetry", headers=device_headers, json=overload_body
    )
    reaction_seconds = time.monotonic() - started_at
    check(
        "evento critico genera orden de apagado",
        overload_response.status_code == 200 and overload_response.json().get("command") is not None,
    )
    check(
        f"tiempo de reaccion <500ms (medido {reaction_seconds * 1000:.1f}ms, incluye red local)",
        reaction_seconds < 0.5,
    )

    pending_response = client.get("/api/v1/iot/commands/pending", headers=device_headers)
    has_pending = pending_response.status_code == 200 and len(pending_response.json()) >= 1
    check("comando pendiente visible", has_pending)

    if has_pending:
        command_id = pending_response.json()[0]["id"]
        ack_response = client.post(
            f"/api/v1/iot/commands/{command_id}/ack",
            headers=device_headers,
            json={"actual_state": "OFF"},
        )
        check("ACK de comando aceptado", ack_response.status_code == 200)

    failures = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failures)}/{len(results)} verificaciones en verde.")
    if failures:
        print("Fallaron:", ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
