# 0012: Motor de reglas conectado a telemetría, sin reactivación automática

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

`app/services/cutoff_rules.py::evaluate_cutoff` ya existía y era correcto (evaluación síncrona, sin red ni broker, para cumplir la métrica de <500ms), pero solo cubre sobrecorriente. El simulador de la etapa 4 ya incluía escenarios `overvoltage`/`undervoltage` esperando una regla que todavía no existía. Además, la spec exige que, tras un evento crítico, el dispositivo no se reactive automáticamente — solo una orden explícita (etapa 6) puede hacerlo.

## Decisión

1. `app/services/voltage_rules.py::evaluate_voltage` — regla hermana de `evaluate_cutoff`, misma forma (dataclass de decisión, función pura, evaluación síncrona), pero **no fusionada** en la misma función: son dos condiciones independientes. `DeviceProfile` gana `min_voltage_v`/`max_voltage_v` (nullable — perfil sin límites configurados no dispara la regla, igual que `max_current_a=None` en la existente).
2. `evaluate_and_act` (stub de la etapa 4, ahora real) en `app/api/iot/router.py`: evalúa ambas reglas contra la lectura recién persistida; si alguna dispara, crea un `Event` (`CRITICAL_OVERLOAD` / `CRITICAL_OVERVOLTAGE` / `CRITICAL_UNDERVOLTAGE`) y un `Command(SET_RELAY_OFF, PENDING)` en la misma transacción síncrona, y pone `Device.desired_state="OFF"`.
3. **`Device.is_locked_out`** (nuevo campo): se activa junto con el evento crítico y nunca se desactiva desde ningún flujo automático — ni telemetría normal, ni heartbeat. Mientras esté en `True`, `evaluate_and_act` no vuelve a generar evento/comando por lecturas repetidas en la misma condición (evita spamear `Event`/`Command` en cada ciclo de telemetría mientras la condición peligrosa persiste). Solo el endpoint de reactivación explícita de la etapa 6 podrá limpiarlo.
4. **Latencia embebida en la respuesta**: en vez de esperar al siguiente `GET /commands/pending`, `POST /telemetry` devuelve el `Command` directo en su respuesta (`TelemetryAck.command`, campo que la etapa 4 ya había dejado listo) — así el dispositivo puede aplicar el corte sin un ciclo de polling adicional. El comando también queda en la cola (`PENDING`) por si el dispositivo no llega a procesar esa respuesta.
5. Medición real de la métrica: `evaluate_and_act` recibe el timestamp de recepción de la etapa (`receive_telemetry`) y loggea `reaction_ms` (estructurado, JSON) al crear el `Command`. Un test (`test_reaction_time_is_under_500ms`) captura ese log real vía `caplog` y confirma `<500ms` con datos de una corrida real, no una estimación.
6. Verificación adicional contra el stack real (no solo `TestClient`): se creó un dispositivo con perfil real en la base del contenedor y se envió una lectura de sobrecarga real por `curl` desde el host — la respuesta HTTP incluyó el comando de apagado en la misma llamada.

## Consecuencias

* **Positivas:** el mecanismo de bloqueo (`is_locked_out`) queda listo como la invariante que la etapa 6 debe respetar (rechazar `/switch` a ON, solo `/reactivate` lo limpia) sin que esta etapa tuviera que construir esos endpoints.
* **Negativas:** ningún endpoint puede todavía limpiar `is_locked_out` — un dispositivo bloqueado en esta etapa queda bloqueado hasta que la etapa 6 exista. Es el comportamiento correcto (no reactivación automática), solo documentado aquí para que no se confunda con un bug durante el desarrollo de etapas intermedias.
