# ino/ — Firmware ESP32-C3

Contiene `code.ino`, el firmware **ya validado experimentalmente**: control del relé y lectura del medidor PZEM-004T vía UART (librería `MycilaPZEM`).

## Reglas invariables (no negociables)

- **No modificar** ningún pin (`PZEM_TX`, `PZEM_RX`, `PZEM_ADDRESS`, `RELAY_CTRL`).
- **No modificar** la lógica de medición del PZEM ni la función `setRelay()` ya probada.
- **No modificar** decisiones eléctricas (niveles lógicos, dirección Modbus, etc.).
- Todo lo nuevo (WiFi, aprovisionamiento, cliente HTTP, cola de comandos, corte crítico local) se agrega **alrededor** de lo existente, nunca reemplazando el bucle de medición/control ya validado.

Ver [`roadmap/stages/12-firmware-network-layer.md`](../roadmap/stages/12-firmware-network-layer.md) para el detalle de qué se agrega y cómo probarlo end-to-end contra `backend-server/`.
