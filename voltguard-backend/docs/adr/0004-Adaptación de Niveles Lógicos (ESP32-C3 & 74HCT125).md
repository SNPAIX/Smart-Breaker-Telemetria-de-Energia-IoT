# 0004: Adaptación de Niveles Lógicos (ESP32-C3 & 74HCT125)

* **Estatus:** Aceptado
* **Fecha:** 3 de Septiembre del 2026

## Contexto:
El microcontrolador principal (ESP32-C3) opera con lógica interna de 3.3 V, mientras que la interfaz de comunicación UART del módulo de instrumentación PZEM-004T V3.0 opera de forma nativa a 5 V. Conectar ambos componentes directamente pondría en riesgo los puertos GPIO del microcontrolador.

## Decisión:
Implementar un circuito de adaptación bidireccional asimétrico: utilizar un búfer lógico 74HCT125 alimentado a 5 V para adecuar la señal de transmisión (TX) del ESP32 hacia el PZEM, y un divisor resistivo (10 kΩ / 20 kΩ) para reducir de forma segura la señal de salida del PZEM (5 V a ~3.3 V) hacia el pin RX del microcontrolador.

## Consecuencia:
* **Positiva:** Se protege la integridad del ESP32-C3 de sobretensiones lógicas sin degradar la velocidad ni la fiabilidad de la comunicación serial UART.
* **Negativa / Reto:** Incrementa ligeramente la complejidad del circuito impreso al requerir componentes pasivos discretos y un circuito integrado adicional en la zona de baja tensión.