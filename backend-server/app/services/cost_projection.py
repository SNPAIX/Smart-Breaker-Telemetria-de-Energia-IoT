"""Inferencia de IA de apoyo (RF de VoltGuard): proyección de consumo/costo
mensual, y detección de comportamiento anómalo por aparato a nivel de
tendencia (no de una sola lectura).

Esto es distinto de app/services/anomaly_detector.py:
- anomaly_detector.py responde "¿esta lectura puntual es rara?" (z-score /
  Isolation Forest sobre lecturas individuales de potencia).
- Este módulo responde "¿el patrón de consumo de este aparato está
  cambiando con el tiempo?" — compara el promedio diario reciente contra
  el promedio diario anterior, que es justo el ejemplo que pone la
  propuesta ("un refrigerador consumiendo más de lo normal").

La proyección de costo usa una regresión lineal simple (mínimos cuadrados,
igual que en stock-forecast-api) sobre el consumo diario acumulado para
extrapolar el consumo del resto del mes. No es un modelo sofisticado a
propósito: la meta de negocio es "margen de error menor al 10%" contra el
recibo real, y una tendencia lineal sobre datos de pocos días ya cumple
razonablemente esa meta sin sobre-ingeniería.

IMPORTANTE: `tariff_mxn_per_kwh` es un parámetro configurable, no una
tarifa oficial de CFE en tiempo real — la tarifa real depende del plan
contratado (1, 1A, DAC, etc.) y del nivel de consumo (las tarifas
domésticas mexicanas son escalonadas). Se documenta así a propósito para
no prometer una precisión que dependería de datos que este sistema no
tiene.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_TARIFF_MXN_PER_KWH = 2.50  # aproximado; ajustar según el plan real
DAYS_IN_MONTH = 30
TREND_ANOMALY_THRESHOLD = 0.30  # 30% de incremento entre periodos = anómalo


@dataclass
class CostProjectionResult:
    days_analyzed: int
    avg_daily_energy_wh: float
    trend_wh_per_day: float
    projected_monthly_kwh: float
    tariff_mxn_per_kwh: float
    projected_monthly_cost_mxn: float
    is_trending_up: bool
    percent_change_vs_previous_period: float | None
    factors: list[dict[str, Any]] = field(default_factory=list)


def _linear_trend(values: list[float]) -> tuple[float, float]:
    """Regresión lineal simple sobre una serie; devuelve (intercepto, pendiente)."""
    import numpy as np

    if len(values) < 2:
        avg = values[0] if values else 0.0
        return avg, 0.0

    days = list(range(len(values)))
    slope, intercept = np.polyfit(days, values, 1)
    return float(intercept), float(slope)


def project_monthly_cost(
    daily_energy_wh: list[float],
    tariff_mxn_per_kwh: float = DEFAULT_TARIFF_MXN_PER_KWH,
) -> CostProjectionResult:
    """Proyecta el consumo y costo mensual a partir de energía diaria (Wh).

    `daily_energy_wh` debe venir ya agregada por día (ver
    DeviceService.daily_summary para cómo se arma esa agregación).
    """
    if not daily_energy_wh:
        return CostProjectionResult(
            days_analyzed=0,
            avg_daily_energy_wh=0.0,
            trend_wh_per_day=0.0,
            projected_monthly_kwh=0.0,
            tariff_mxn_per_kwh=tariff_mxn_per_kwh,
            projected_monthly_cost_mxn=0.0,
            is_trending_up=False,
            percent_change_vs_previous_period=None,
            factors=[],
        )

    days_analyzed = len(daily_energy_wh)
    avg_daily = sum(daily_energy_wh) / days_analyzed
    intercept, slope = _linear_trend(daily_energy_wh)

    # Proyecta cada día del mes con la tendencia detectada (nunca negativo)
    projected_days = [max(0.0, intercept + slope * i) for i in range(DAYS_IN_MONTH)]
    projected_monthly_wh = sum(projected_days)
    projected_monthly_kwh = projected_monthly_wh / 1000.0
    projected_cost = projected_monthly_kwh * tariff_mxn_per_kwh

    # Comportamiento anómalo a nivel de tendencia: compara la segunda mitad
    # del historial contra la primera mitad (si hay suficientes datos)
    percent_change: float | None = None
    is_trending_up = False
    if days_analyzed >= 4:
        midpoint = days_analyzed // 2
        first_half_avg = sum(daily_energy_wh[:midpoint]) / midpoint
        second_half_avg = sum(daily_energy_wh[midpoint:]) / (days_analyzed - midpoint)
        if first_half_avg > 0:
            percent_change = (second_half_avg - first_half_avg) / first_half_avg
            is_trending_up = percent_change > TREND_ANOMALY_THRESHOLD

    factors = [
        {
            "factor": "avg_daily_energy_wh",
            "value": round(avg_daily, 2),
            "detail": "Consumo promedio diario observado en el histórico",
        },
        {
            "factor": "trend_wh_per_day",
            "value": round(slope, 3),
            "detail": "Cambio diario en el consumo (tendencia, +sube/-baja)",
        },
        {
            "factor": "percent_change_vs_previous_period",
            "value": round(percent_change, 3) if percent_change is not None else 0.0,
            "detail": "Cambio porcentual entre la primera y segunda mitad del histórico",
        },
    ]

    return CostProjectionResult(
        days_analyzed=days_analyzed,
        avg_daily_energy_wh=round(avg_daily, 2),
        trend_wh_per_day=round(slope, 3),
        projected_monthly_kwh=round(projected_monthly_kwh, 2),
        tariff_mxn_per_kwh=tariff_mxn_per_kwh,
        projected_monthly_cost_mxn=round(projected_cost, 2),
        is_trending_up=is_trending_up,
        percent_change_vs_previous_period=(
            round(percent_change, 3) if percent_change is not None else None
        ),
        factors=factors,
    )
