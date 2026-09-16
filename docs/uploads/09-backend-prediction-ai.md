# Etapa 9 — Predicción y detección de anomalías (IA)

- `Prediction` persistida y cacheada (24h) en vez de recalcular en cada consulta — sin scheduler nuevo.
- Detección de anomalías conectada a la ingesta de telemetría real, independiente del motor de corte (etapa 5).
- `/prediction` ahora refleja la fila persistida (`projected_kwh`, `projected_cost`, `method`, `generated_at`).
- Ambas estrategias (`rule_based`/`isolation_forest`) verificadas contra la API real.
- Verificado end-to-end: 80 tests, 96.34% cobertura, `ruff`/`mypy` limpios; margen de error de predicción <10% confirmado con dataset sintético.
