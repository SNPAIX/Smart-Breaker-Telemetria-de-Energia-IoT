# 0005: Arquitectura de Corte de Carga y Seguridad por Fallo (Relé SLA-05VDC & ULN2003A)

* **Estatus:** Aceptado
* **Fecha:** 3 de Septiembre del 2026

## Contexto:
El sistema debe ser capaz de interrumpir físicamente la alimentación de corriente alterna (~127 VCA) de un electrodoméstico ante una orden del backend o una sobrecarga crítica, controlando la conmutación desde una señal digital de baja potencia del ESP32-C3.

## Decisión:
Utilizar un relé de potencia SLA-05VDC-SL-A (configurado con un límite operativo seguro de 15 A y contactos en modo Normalmente Abierto - NO), excitado a través de un circuito integrado driver ULN2003A para manejar la corriente de la bobina (~180 mA) de manera aislada del microcontrolador.

## Consecuencia:
* **Positiva:** Si el sistema electrónico pierde energía de forma imprevista, el relé se desenergiza por defecto y abre el circuito, garantizando que el electrodoméstico quede protegido (Fail-Safe).
* **Negativa / Reto:** El uso de un transistor Darlington (ULN2003A) genera una caída térmica y de tensión moderada, la cual deberá optimizarse en revisiones futuras de diseño con transistores MOSFET.