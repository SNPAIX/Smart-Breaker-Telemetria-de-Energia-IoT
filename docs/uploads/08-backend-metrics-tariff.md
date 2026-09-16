# Etapa 8 — Métricas, tarifas y costo

- `Tariff` persistente por sitio con histórico real (crear una nueva cierra la anterior, nunca se sobrescribe).
- `/cost` reinterpretado como costo real del período (no proyección) — cada día se cobra con la tarifa vigente ESE día.
- Proyección a futuro (kWh/tendencia) se queda en `/prediction`, sin mezclarse con el costo real.
- CRUD de tarifas solo en admin (`/api/v1/admin/sites/{id}/tariffs`).
- Verificado end-to-end: 77 tests, 96.15% cobertura, `ruff`/`mypy` limpios, caso de prorrateo con dos tarifas confirmado numéricamente (8.0 vs. 9.0 si no prorrateara).
