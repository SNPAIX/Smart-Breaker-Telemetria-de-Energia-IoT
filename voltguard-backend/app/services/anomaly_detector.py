"""Detectores de anomalías de consumo, intercambiables (patrón strategy).

La idea: el resto del sistema (servicio, router, firmware) no necesita saber
si la decisión "esto es una anomalía" viene de una regla estadística simple
o de un modelo de machine learning. Ambos implementan la misma interfaz
(AnomalyDetector.evaluate), así que se pueden intercambiar con una sola
línea de configuración — no son dos proyectos separados, son dos
estrategias del mismo pipeline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AnomalyResult:
    is_anomaly: bool
    expected_power_w: float
    detector_name: str


class AnomalyDetector(ABC):
    """Interfaz común para cualquier estrategia de detección."""

    name: str

    @abstractmethod
    def evaluate(self, history_power_w: list[float], new_power_w: float) -> AnomalyResult:
        """Decide si new_power_w es anómalo dado el historial reciente."""


class RuleBasedDetector(AnomalyDetector):
    """Detector 'sin IA': z-score sobre el historial reciente.

    Marca anomalía si la lectura nueva está a más de `z_threshold`
    desviaciones estándar del promedio reciente. Es la versión piso —
    explicable con una fórmula de estadística básica, sin entrenar nada.
    """

    name = "rule_based"

    def __init__(self, z_threshold: float = 3.0, min_history: int = 5) -> None:
        self._z_threshold = z_threshold
        self._min_history = min_history

    def evaluate(self, history_power_w: list[float], new_power_w: float) -> AnomalyResult:
        if len(history_power_w) < self._min_history:
            return AnomalyResult(False, new_power_w, self.name)

        mean = sum(history_power_w) / len(history_power_w)
        variance = sum((x - mean) ** 2 for x in history_power_w) / len(history_power_w)
        std = variance**0.5

        if std == 0:
            is_anomaly = new_power_w != mean
        else:
            z_score = abs(new_power_w - mean) / std
            is_anomaly = z_score > self._z_threshold

        return AnomalyResult(is_anomaly, round(mean, 2), self.name)


class IsolationForestDetector(AnomalyDetector):
    """Detector 'con IA': Isolation Forest entrenado sobre el historial
    reciente del propio dispositivo.

    Se reentrena en cada evaluación con el historial disponible (es barato
    para el tamaño de datos de un solo dispositivo). No es el detector más
    sofisticado posible, pero es un modelo de ML real, no una regla
    disfrazada, y detecta patrones que un umbral fijo no captura (ej.
    combinaciones inusuales de nivel + variabilidad).
    """

    name = "isolation_forest"

    def __init__(self, min_history: int = 10, contamination: float = 0.05) -> None:
        self._min_history = min_history
        self._contamination = contamination

    def evaluate(self, history_power_w: list[float], new_power_w: float) -> AnomalyResult:
        import numpy as np
        from sklearn.ensemble import IsolationForest

        mean = (
            sum(history_power_w) / len(history_power_w) if history_power_w else new_power_w
        )

        if len(history_power_w) < self._min_history:
            return AnomalyResult(False, round(mean, 2), self.name)

        X_train = np.array(history_power_w).reshape(-1, 1)
        model = IsolationForest(
            n_estimators=100, contamination=self._contamination, random_state=42
        )
        model.fit(X_train)

        prediction = model.predict(np.array([[new_power_w]]))[0]  # -1 = anomalía, 1 = normal
        is_anomaly = bool(prediction == -1)

        return AnomalyResult(is_anomaly, round(mean, 2), self.name)


def get_detector(strategy: str) -> AnomalyDetector:
    """Factory: 'rule_based' (sin IA) o 'isolation_forest' (con IA)."""
    if strategy == "isolation_forest":
        return IsolationForestDetector()
    return RuleBasedDetector()
