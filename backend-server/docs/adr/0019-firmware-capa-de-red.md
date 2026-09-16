# 0019: Capa de red sobre el firmware validado + validación en dos niveles

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

`ino/code.ino` estaba validado experimentalmente (PZEM-004T + relé sobre un Seeed XIAO ESP32-C3) pero sin ninguna capa de red — no hablaba con el backend. La spec exige agregarla sin tocar pines, `PZEM_ADDRESS`, `setRelay()`, el parseo del PZEM ni la inicialización UART, y sin depender de tener el hardware físico presente para validar el trabajo (ver `roadmap/ORIGINAL-SPEC-HARDWARE-VALIDATION.md`).

## Decisión

1. Todo lo nuevo vive en archivos separados (`device_storage.*`, `provisioning.*`, `iot_client.*`, `local_safety.*`, `hardware_bridge.h`) que se enganchan a `code.ino` en exactamente tres puntos, todos aditivos: los `#include` al inicio, una llamada a `onPzemReading(...)` al final del bloque `EVT_READ` del callback existente (después de los `Serial.print` que ya estaban, sin tocarlos), y el reemplazo explícito del bloque de demostración en `setup()`/`loop()` que la propia etapa autoriza a reemplazar. Ninguna línea de medición/control ya validada se modificó.
2. **Identidad y credencial del dispositivo no se autogeneran**: `public_id` y el secreto los emite el backend al dar de alta el dispositivo (`POST /api/v1/admin/devices`, etapa 7) — el firmware los recibe por el mismo portal de aprovisionamiento que la clave WiFi (como la clave de un router, entregados con el equipo). `device_storage.cpp` sí deriva un `public_id` *sugerido* de la MAC solo para prellenar el formulario; nunca es el que se usa si el instalador captura otro.
3. **Corte crítico local desacoplado de la red por diseño, no por promesa**: `onPzemReading()` evalúa `evaluateLocalCriticalCutoff()` (síncrono, sin I/O) y aplica `setRelay()` **antes** de siquiera considerar si hay red — el envío de telemetría al backend con esa misma lectura (que ya refleja el nuevo `relay_state` tras el corte) ocurre después, desde el `loop()` principal, nunca desde dentro del callback del PZEM. Esto evita que una llamada HTTP lenta o colgada retrase el corte de seguridad, y evita hacer I/O de red desde un contexto de callback cuyo stack/tarea no está garantizado.
4. **NTP**: se agregó sincronización de hora (`configTime`) porque sin ella `time(nullptr)` no refleja la hora real y el `timestamp` de cada lectura de telemetría llegaría mal al backend, rompiendo el bucketing por día de las etapas 8/9. Se sincroniza de forma perezosa la primera vez que hay red disponible.
5. **Verificación real, no solo revisión de código**: se instaló `arduino-cli` con el core `esp32:esp32` 3.3.11, la librería `MycilaPZEM` 8.0.5 (la misma que ya usaba el `.ino` original) y `ArduinoJson` 7.4.3, y se compiló contra el board real `XIAO_ESP32C3` — compiló limpio, cero warnings incluso con `--warnings all`. `hardware_tests/run_pass_software.py` se corrió de verdad contra el backend en Docker Compose (no se limitó a describir el plan): 10/10 verificaciones en verde, incluyendo el tiempo de reacción medido (178.3ms, dentro del límite de 500ms de la propuesta).
6. **PASS físico queda pendiente**, documentado explícitamente en `docs/claude/HIL_TEST_PLAN.md` con la tabla de acciones físicas exactas para cuando haya una sesión de laboratorio — no se afirma en ningún lado que el hardware fue validado, solo el software.

## Consecuencias

* **Positivas:** hay evidencia real (compilación limpia + corrida HTTP real) de que el firmware nuevo es sintácticamente correcto y de que el contrato que habla contra el backend funciona de punta a punta, sin haber tocado una sola vez el ESP32-C3 físico.
* **Negativas:** el uso de flash llegó a 89% (1.17MB de 1.31MB) — principalmente por el soporte TLS de `WiFiClientSecure`. Si una iteración futura necesita más espacio, ese es el primer candidato a revisar (ej. condicionar la compilación de HTTPS a un flag si el backend de destino solo usa HTTP en desarrollo).
