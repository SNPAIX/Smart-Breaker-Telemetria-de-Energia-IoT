# 0006: Esquema de Aislamiento Eléctrico y Protecciones por Etapas

* **Estatus:** Aceptado
* **Fecha:** 3 de Septiembre del 2026

## Contexto:
Un dispositivo IoT conectado directamente a la red eléctrica domiciliaria se encuentra expuesto a perturbaciones transitorias, picos de conmutación inductiva de motores y riesgos de cortocircuito severo que podrían dañar tanto la electrónica como al usuario.

## Decisión:
Implementar un esquema de protección escalonado que incluye:
* Una fuente de alimentación AC/DC aislada Mean Well IRM-05-5 para transformar 127 VCA a 5 VDC de manera independiente.
* Doble protección por fusibles retardados (T15A para la línea principal de potencia y T1A exclusivo para la rama de la fuente electrónica).
* Un varistor (MOV) colocado entre fase y neutro para la supresión de picos transitorios de voltaje.
* Una línea física de Tierra (PE) completamente independiente y exenta de interrupción por software.

## Consecuencia:
* **Positiva:** Alta robustez ante fallos de la red eléctrica comercial y cumplimiento de normativas de seguridad industrial e instrumental.
* **Negativa / Reto:** Ocupa mayor espacio físico dentro de la envolvente del dispositivo y exige una selección muy precisa de los portafusibles para disipar correctamente el calor.