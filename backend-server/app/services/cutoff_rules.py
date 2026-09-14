"""Motor de reglas de corte por sobrecarga crítica (RF-4 de VoltGuard).

Esto es intencionalmente independiente del detector de anomalías
(app/services/anomaly_detector.py). La diferencia importa:

- El detector de anomalías responde "¿esto es raro comparado con el
  historial de este dispositivo?" — es relativo, aprende del patrón normal
  de cada aparato, y nunca corta la corriente por sí solo.
- El motor de reglas de corte responde "¿esto es peligroso, sin importar
  el historial?" — es un umbral absoluto configurado por perfil (ej. "este
  circuito nunca debe pasar de 15A"), y SIEMPRE dispara una orden de
  apagado inmediata si se excede. No aprende nada ni necesita historial.

Se evalúa de forma síncrona e in-proceso (sin llamadas de red ni a un
modelo) precisamente para cumplir la métrica de reacción de seguridad
(<500ms desde que la API recibe la lectura hasta que emite la orden de
apagado) — evaluar un umbral es una comparación numérica, no hay nada que
optimizar ahí.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CutoffDecision:
    triggered: bool
    current_a: float
    max_current_a: float | None


def evaluate_cutoff(
    current_a: float,
    max_current_a: float | None,
    auto_cutoff_enabled: bool,
) -> CutoffDecision:
    """Decide si una lectura de corriente viola el umbral de seguridad.

    Si el dispositivo no tiene umbral configurado, o el corte automático
    está deshabilitado para ese perfil, nunca dispara — el umbral es
    opcional por diseño (no todos los aparatos necesitan uno).
    """
    if not auto_cutoff_enabled or max_current_a is None:
        return CutoffDecision(False, current_a, max_current_a)

    triggered = current_a > max_current_a
    return CutoffDecision(triggered, current_a, max_current_a)
