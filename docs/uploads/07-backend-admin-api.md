# Etapa 7 — API administrativa (/api/v1/admin)

- CRUD completo: usuarios, sitios, dispositivos (con emisión de credencial), perfiles.
- Reasignación de dispositivos entre sitios, métricas globales/por-sitio/por-perfil/overview.
- "Online" calculado al vuelo contra `device_online_threshold_seconds`, nunca una columna.
- Sin endpoint de switch/reactivate en admin — esa operación vive solo en `/api/v1/app` (etapa 6), con su misma trazabilidad.
- Borrados con guarda de integridad (409 si el sitio/perfil sigue en uso).
- Verificado end-to-end: 75 tests, 96.07% cobertura, `ruff`/`mypy` limpios; credencial emitida por admin probada de verdad contra `/api/v1/iot/telemetry`.
