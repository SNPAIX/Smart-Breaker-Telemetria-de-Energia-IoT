# 0007: Distribución Física de la PCB (Separación de Alta y Baja Tensión)

* **Estatus:** Aceptado
* **Fecha:** 9 de Septiembre del 2026

## Contexto:
La coexistencia de voltajes de corriente alterna de red (~127 VCA) y señales digitales sensibles de baja tensión (3.3V/5V) en una misma tarjeta de circuito impreso (PCB) representa un riesgo de acoplamiento de ruido electromagnético (EMI) y descargas eléctricas.

## Decisión:
Diseñar la PCB bajo una estricta segmentación geométrica y física dividida en dos regiones claramente delimitadas: una zona de alta tensión (entradas de CA, fusibles, MOV, contactos del relé, terminales de red del PZEM y entrada de la fuente IRM) y una zona de baja tensión (ESP32-C3, regulador AMS1117 con capacitores de desacoplamiento de 10 µF/100 nF, driver ULN2003A y circuitería UART).

## Consecuencia:
* **Positiva:** Se minimiza drásticamente la interferencia electromagnética sobre las mediciones analógicas del PZEM y se garantiza una distancia de aislamiento (creepage/clearance) segura para evitar arcos eléctricos.
* **Negativa / Reto:** Condiciona el ruteo de las pistas y obliga a mantener una barrera física de separación libre de trazas en el diseño del circuito impreso.