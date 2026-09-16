"""Escenarios reutilizables sobre `DeviceSimulator`.

Lista completa exigida por `roadmap/ORIGINAL-SPEC-HARDWARE-VALIDATION.md`.
Los que dependen del motor de reglas (overload/overvoltage/undervoltage,
relay command failure evaluado por el servidor) solo ejercitan aquí el
transporte — la etapa 5 conecta la decisión de seguridad y agrega sus
propias aserciones sobre el resultado.
"""

from __future__ import annotations

from typing import Any

from simulator.device_simulator import DeviceSimulator


def scenario_normal(sim: DeviceSimulator, sequence: int) -> Any:
    return sim.send_telemetry(sequence=sequence)


def scenario_overload(sim: DeviceSimulator, sequence: int, max_current_a: float) -> Any:
    return sim.send_telemetry(sequence=sequence, current_a=max_current_a + 5.0)


def scenario_overvoltage(sim: DeviceSimulator, sequence: int, max_voltage_v: float) -> Any:
    return sim.send_telemetry(sequence=sequence, voltage_v=max_voltage_v + 20.0)


def scenario_undervoltage(sim: DeviceSimulator, sequence: int, min_voltage_v: float) -> Any:
    return sim.send_telemetry(sequence=sequence, voltage_v=max(0.0, min_voltage_v - 20.0))


def scenario_duplicate_sequence(sim: DeviceSimulator, sequence: int) -> tuple[Any, Any]:
    first = sim.send_telemetry(sequence=sequence)
    duplicate = sim.send_telemetry(sequence=sequence)
    return first, duplicate


def scenario_out_of_order_telemetry(
    sim: DeviceSimulator, first_sequence: int, out_of_order_sequence: int
) -> tuple[Any, Any]:
    latest = sim.send_telemetry(sequence=first_sequence)
    out_of_order = sim.send_telemetry(sequence=out_of_order_sequence)
    return latest, out_of_order


def scenario_invalid_credentials(sim: DeviceSimulator, sequence: int) -> Any:
    """`sim` debe construirse con un secreto incorrecto o revocado — este
    escenario solo documenta la llamada esperada, la credencial la decide
    quien arma el `DeviceSimulator`."""
    return sim.send_telemetry(sequence=sequence)


def scenario_malformed_telemetry(sim: DeviceSimulator) -> Any:
    return sim.send_malformed_telemetry({"sequence": "no-es-un-entero"})


def scenario_relay_command_failure(
    sim: DeviceSimulator, command_id: int, desired_state: str
) -> Any:
    """El dispositivo confirma el comando pero reporta el estado contrario
    al pedido — simula que el relé físico no respondió como se esperaba."""
    reported_state = "OFF" if desired_state == "ON" else "ON"
    return sim.ack_command(command_id, actual_state=reported_state)


def scenario_delayed_ack(sim: DeviceSimulator, command_id: int, actual_state: str) -> Any:
    """Semánticamente idéntico a un ACK normal — el "delay" es que quien
    llama a esta función lo hace varios ciclos de telemetría después de ver
    el comando en `list_pending_commands()`, no algo que el simulador deba
    modelar como un temporizador."""
    return sim.ack_command(command_id, actual_state=actual_state)
