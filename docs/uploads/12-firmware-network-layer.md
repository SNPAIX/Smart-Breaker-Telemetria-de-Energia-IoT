# Etapa 12 — Firmware: capa de red + HIL

- Capa de red agregada a `ino/code.ino` sin tocar pines, `setRelay()`, el parseo del PZEM ni la inicialización UART — solo 3 puntos de enganche aditivos.
- Aprovisionamiento vía portal cautivo (AP + WiFi), identidad/credencial del dispositivo entregadas por el backend (no autogeneradas), corte crítico local desacoplado de la red (evalúa y corta antes de cualquier llamada HTTP).
- `docs/claude/HIL_TEST_PLAN.md` + `hardware_tests/run_pass_software.py` (+ `serial_monitor.py` para cuando haya hardware).
- **PASS software real**: firmware compilado limpio (arduino-cli + ESP32 core real, cero warnings) y 10/10 verificaciones en verde corriendo contra el backend real en Docker (auth, telemetría, evento crítico, reacción 178ms, comando, ACK).
- **PASS físico**: pendiente, documentado explícitamente — sin acceso a hardware en esta sesión.
