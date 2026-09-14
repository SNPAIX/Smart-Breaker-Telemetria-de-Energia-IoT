# Etapa 2 — Modelo de datos v2

- Nuevo esquema: `Site`, `SiteMember`, `DeviceProfile`, `DeviceCredential`, `Device` (rediseñado: `public_id` separado de la PK interna, `desired_state`/`actual_state`), `TelemetryReading`, `Command`, `Event`, `AnomalyAlert`, `Notification`, `NotificationPreference`, `Tariff`, `Prediction`.
- Migración `DROP`/`CREATE` limpia (sin datos que preservar), probada `upgrade` → `downgrade` → `upgrade` contra Postgres real.
- Endpoints/tests atados al esquema viejo (telemetría, registro de dispositivo) se retiran temporalmente; se reconstruyen en las etapas 4/5/6/7. Los servicios de reglas/anomalías/costo no se tocan.
- Verificado end-to-end: 39 tests, 99.55% cobertura, `ruff`/`mypy` limpios, `/health` y `/docs` OK.
