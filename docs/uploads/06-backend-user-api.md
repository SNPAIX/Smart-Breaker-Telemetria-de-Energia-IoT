# Etapa 6 — API de usuario final (/api/v1/app)

- Sitios/dispositivos/telemetría/eventos scoped a membresía real (`get_authorized_device`: 404 uniforme si no existe o no es tuyo).
- `switch`/`reactivate` respetan el bloqueo de la etapa 5 (409 hasta reactivación explícita, con evento `MANUAL_REACTIVATION`).
- `claim` de dispositivo sin sitio, rechaza doble reclamo (409).
- `/metrics`, `/cost`, `/prediction`: mínimo viable real hoy (reutilizan `project_monthly_cost` ya existente); se formalizan en etapas 8/9.
- `/notifications` + preferencias: funcional de una vez, no depende de la etapa 10.
- Verificado end-to-end: 67 tests, 99.5% cobertura, `ruff`/`mypy` limpios, aislamiento entre dos usuarios reales confirmado.
