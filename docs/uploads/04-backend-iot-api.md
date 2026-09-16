# Etapa 4 — API IoT + simulador de dispositivo

- `POST /api/v1/iot/{telemetry,heartbeat}`, `GET /commands/pending`, `POST /commands/{id}/ack` — todo detrás de auth de dispositivo.
- `sequence` idempotente (duplicado no se re-inserta) y fuera-de-orden se persiste marcado, no se descarta.
- `actual_state` reportado se guarda tal cual, sin "corregirlo" contra `desired_state`.
- Simulador de dispositivo reutilizable (`simulator/`), mismo código sirve contra `TestClient` o un servidor real.
- Verificado end-to-end: 56 tests, 99.63% cobertura, `ruff`/`mypy` limpios, y una pasada real por red (curl) contra el stack en Docker.
