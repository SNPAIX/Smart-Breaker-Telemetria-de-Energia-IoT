"""Motor de reglas de corte por voltaje fuera de rango.

Regla hermana de `app/services/cutoff_rules.py::evaluate_cutoff`, separada
a propósito en vez de fusionarse en una sola función: sobrecorriente y
voltaje fuera de rango son condiciones independientes que evolucionan por
separado (evaluar una no depende de conocer la otra).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class VoltageDecision:
    triggered: bool
    voltage_v: float
    min_voltage_v: float | None
    max_voltage_v: float | None
    reason: Literal["OVERVOLTAGE", "UNDERVOLTAGE"] | None = None


def evaluate_voltage(
    voltage_v: float,
    min_voltage_v: float | None,
    max_voltage_v: float | None,
) -> VoltageDecision:
    """Perfil sin límites configurados (ambos None) nunca dispara esta
    regla — mismo criterio que `evaluate_cutoff` con `max_current_a=None`.
    """
    if max_voltage_v is not None and voltage_v > max_voltage_v:
        return VoltageDecision(True, voltage_v, min_voltage_v, max_voltage_v, "OVERVOLTAGE")
    if min_voltage_v is not None and voltage_v < min_voltage_v:
        return VoltageDecision(True, voltage_v, min_voltage_v, max_voltage_v, "UNDERVOLTAGE")
    return VoltageDecision(False, voltage_v, min_voltage_v, max_voltage_v)
