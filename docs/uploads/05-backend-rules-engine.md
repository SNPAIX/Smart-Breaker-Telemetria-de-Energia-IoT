# Etapa 5 — Motor de reglas y eventos críticos

- `evaluate_voltage` (nueva, hermana de `evaluate_cutoff`): sobre/bajo voltaje contra `DeviceProfile.min_voltage_v`/`max_voltage_v`.
- Sobrecarga o voltaje fuera de rango → `Event` crítico + `Command(SET_RELAY_OFF)` embebido en la respuesta de `/telemetry` (latencia mínima) y en la cola.
- `Device.is_locked_out`: se activa con el evento, nunca se limpia automáticamente — solo la etapa 6 (reactivación explícita) podrá hacerlo.
- Métrica de reacción <500ms medida con log real (`reaction_ms`), no estimada.
- Verificado end-to-end: 62 tests, 99.66% cobertura, `ruff`/`mypy` limpios, y una sobrecarga real por red confirmando el corte inmediato.
