# Plan de pruebas Hardware-in-the-Loop (HIL) — VoltGuard

Ver `roadmap/ORIGINAL-SPEC-HARDWARE-VALIDATION.md` (local, no versionado) para la estrategia completa de validación en dos niveles. Este documento es la lista concreta de qué se prueba, cómo, y qué requiere una acción física puntual.

## Regla general

- **PASS software**: todo lo que se puede verificar sin tocar el hardware físico — automatizado en `hardware_tests/`, corre contra el backend real (Docker Compose) reproduciendo el contrato HTTP exacto que habla el firmware.
- **PASS físico**: requiere el ESP32-C3 + PZEM-004T + relé reales, y en algunos casos una confirmación humana de una acción física concreta. Se registra por separado. Nunca se declara "hardware validado" con solo el PASS software.
- **Nunca** se automatiza ni se solicita una condición físicamente peligrosa (cortocircuito, sobrecarga real, superar ratings). Las condiciones críticas se prueban con umbrales bajos y/o telemetría simulada.

## Cobertura PASS software (automatizada, sin hardware)

Ejecutable con `hardware_tests/run_pass_software.py` — reutiliza el mismo contrato HTTP que hablará el firmware (`Authorization: Device <public_id>:<secret>`, `/api/v1/iot/*`), sin necesitar el ESP32 físico:

| # | Comportamiento | Cómo se automatiza |
|---|---|---|
| 1 | Autenticación de dispositivo (válida, inválida, revocada) | Requests HTTP reales contra el backend con credenciales correctas/incorrectas/revocadas |
| 2 | Llegada y persistencia de telemetría | `POST /api/v1/iot/telemetry` con el contrato exacto que arma `iot_client.cpp`, verificar la lectura en la base |
| 3 | `last_seen_at` | Verificar que se actualiza tras telemetría y tras heartbeat |
| 4 | Generación de eventos críticos | Enviar una lectura sobre el umbral del perfil, verificar `Event` + `Command` creados |
| 5 | Creación y entrega de comandos | Insertar un `Command` y confirmar que aparece en `GET /commands/pending` |
| 6 | ACK de comandos | `POST /commands/{id}/ack` y verificar `Device.actual_state` |
| 7 | Tiempos de reacción | Medir el tiempo entre el POST de telemetría y la aparición del comando de corte (misma métrica <500ms de la etapa 5) |

Estos siete puntos **ya están cubiertos por la suite de `backend-server/tests/` de las etapas 4 y 5** (`test_iot_api.py`, `test_rules_engine.py`) usando `simulator.DeviceSimulator`. `hardware_tests/run_pass_software.py` los vuelve a ejecutar como una corrida independiente y explícita "modo HIL software", pensada para lanzarse antes de una sesión de laboratorio como chequeo de que el backend está listo para recibir al dispositivo real.

## Cobertura PASS físico (requiere hardware)

Ejecutar con `hardware_tests/serial_monitor.py` (lee el log serie del ESP32-C3 real) en paralelo a una sesión manual. Cada fila indica si requiere una acción humana:

| # | Prueba | Acción del operador |
|---|---|---|
| 1 | Aprovisionamiento: AP → WiFi → STA | Ninguna automatizable desde aquí más que observar el log serie; **ACTION REQUIRED: conectar el ESP32-C3 a una red WiFi de prueba usando el portal en `VoltGuard-Setup-<id>` y confirmar cuando el log serie muestre IP asignada.** |
| 2 | Vínculo a cuenta (`/devices/claim`) | Ninguna física — se hace desde la app/API con el `public_id` mostrado |
| 3 | Telemetría real del PZEM llega al backend | Ninguna física si ya hay una carga de prueba conectada de antes; si no, **ACTION REQUIRED: conectar una carga segura (ej. un foco de baja potencia) al VoltGuard y confirmar cuando esté encendida.** |
| 4 | `switch` remoto cambia el relé físico | **ACTION REQUIRED: confirmar visual o audiblemente que el relé cambió de estado tras el comando, y que la carga de prueba se apagó/encendió en consecuencia.** |
| 5 | Corte crítico local sin red | Configurar un umbral artificialmente bajo en el perfil del dispositivo (ej. 0.5 A) con WiFi del ESP32 desconectado a propósito; **ACTION REQUIRED: confirmar que el relé se corta solo, sin haber backend disponible.** Nunca provocar una sobrecarga real — el umbral bajo alcanza para disparar la condición con la carga de prueba normal. |
| 6 | Reporte del corte local al reconectar | Ninguna física — reconectar el WiFi y observar en el backend que llegó el evento |

## Registro de resultados

Cada corrida debe anotar, por separado:

```
PASS software: <fecha> — <hash de commit> — <resultado de run_pass_software.py>
PASS físico:   <fecha> — <hardware usado> — <resultado fila por fila de la tabla de arriba>
```

Si en un momento dado no hay ventana de acceso físico, el PASS físico queda marcado **PENDIENTE** — no bloquea el resto del roadmap.

**Estado actual (14 de septiembre de 2026, cierre de la etapa 12 en esta sesión):**

- **PASS software**: `hardware_tests/run_pass_software.py` ejecutado contra el backend real (Docker Compose) — **10/10 verificaciones en verde** (login admin, alta de perfil/dispositivo, credencial inválida rechazada, telemetría aceptada, `last_seen_at` actualizado, evento crítico + orden de apagado generados, tiempo de reacción medido en 178.3ms — muy por debajo del límite de 500ms —, comando pendiente visible, ACK aceptado). Datos de prueba limpiados después de la corrida.
- El firmware (`ino/`) compiló limpio contra el toolchain real de Arduino/ESP32 (`arduino-cli`, core `esp32:esp32` 3.3.11, board `XIAO_ESP32C3`, librerías `MycilaPZEM` 8.0.5 + `ArduinoJson` 7.4.3) — **cero errores, cero warnings** incluso con `--warnings all`. Uso de flash: 89% (1,166,745 / 1,310,720 bytes).
- **PASS físico**: **PENDIENTE** — esta sesión no tuvo acceso al hardware físico (ESP32-C3 + PZEM-004T + relé). Se completa en la próxima sesión de laboratorio siguiendo la tabla de arriba.
