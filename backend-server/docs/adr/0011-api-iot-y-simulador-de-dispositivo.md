# 0011: API IoT (`/api/v1/iot/*`) y simulador de dispositivo

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

El repo base no tenía ninguna superficie IoT autenticada (ver ADR 0009 y `roadmap/01-gap-analysis.md`). La spec pide telemetría, heartbeat, entrega de comandos pendientes y ACK con reporte de `actual_state`, todo detrás de la autenticación de dispositivo de la etapa 3. Además, `roadmap/ORIGINAL-SPEC-HARDWARE-VALIDATION.md` exige un simulador de dispositivo de primera clase, no un script desechable, porque el hardware físico puede no estar disponible durante el resto del desarrollo.

## Decisión

1. `app/api/iot/router.py` implementa `POST /telemetry`, `POST /heartbeat`, `GET /commands/pending`, `POST /commands/{id}/ack`, todos detrás de `get_current_device` (etapa 3).
2. **Idempotencia de `sequence`**: un `sequence` ya visto responde 200 `status="duplicate"` sin duplicar el registro (no es un error). Un `sequence` menor al último visto se persiste igual (no se descarta información real) pero se marca `is_out_of_order=true` en la respuesta y se loggea, para que las agregaciones de la etapa 8 puedan filtrarlo si hace falta.
3. `ack_command` persiste el `actual_state` que reporta el dispositivo **tal cual**, sin compararlo ni "corregirlo" contra `desired_state` — la discrepancia entre lo pedido y lo real es información legítima (ver `Device.desired_state` vs `actual_state` en la spec), no un bug a esconder.
4. El punto de integración del motor de reglas (`evaluate_and_act`) queda como stub que no hace nada — la etapa 5 lo conecta. El contrato de respuesta de `/telemetry` ya incluye un campo `command` opcional para que, cuando la etapa 5 lo llene, el dispositivo pueda recibir la orden de corte en la misma respuesta (latencia mínima) sin romper el schema.
5. El aprovisionamiento (dispositivo sin `site_id` → vínculo a una cuenta) se resuelve del lado de `/api/v1/app/devices/claim` en la etapa 6, iniciado por el usuario — no hay ningún endpoint de "reclamo" en `/api/v1/iot/*`, solo un comentario de referencia cruzada en el router.
6. **Simulador de dispositivo** (`backend-server/simulator/`, no bajo `tests/`, para que la etapa 12 lo pueda reutilizar desde su arnés de Hardware-in-the-Loop): `DeviceSimulator` acepta cualquier cliente HTTP compatible con la interfaz de httpx (`get`/`post` con `json=`/`headers=`), de forma que el mismo código sirve tanto para `fastapi.testclient.TestClient` (suite de pytest, rápida y determinista) como para `httpx.Client` contra un servidor real. `simulator/scenarios.py` implementa los escenarios de `ORIGINAL-SPEC-HARDWARE-VALIDATION.md` que ya tienen sentido en esta etapa (normal, duplicate sequence, out-of-order, invalid credentials, malformed telemetry, relay command failure); overload/overvoltage/undervoltage quedan con el transporte listo para que la etapa 5 agregue sus propias aserciones sobre el resultado. "Missing ACK" y "offline" no requieren función propia — son la ausencia de una llamada, no algo que el simulador deba modelar.
7. Verificación end-to-end contra el stack real (no solo `TestClient`): se creó un dispositivo real en la base del contenedor y se ejercitó `/telemetry` y `/heartbeat` con `curl` desde el host, confirmando además que un secreto incorrecto responde 401 por la red real.

## Consecuencias

* **Positivas:** el simulador queda como infraestructura reutilizable real (etapas 5, 6, 11, 12), no código desechable; el contrato de telemetría queda estable desde ahora aunque su lógica de negocio (reglas de corte) llegue después.
* **Negativas:** todavía no existe ningún endpoint para dar de alta un dispositivo con sus credenciales fuera de un script/test manual — eso es explícitamente la etapa 7 (o 4/7 según se decidió en la etapa 3).
