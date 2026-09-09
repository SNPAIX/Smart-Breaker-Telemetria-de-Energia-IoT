# 0003: Persistencia de Datos con SQLAlchemy 2.x, Alembic y PostgreSQL

* **Estatus:** Aceptado
* **Fecha:** 3 de Septiembre del 2026

## Contexto:
Se requiere almacenar de forma estructurada e histórica los registros de telemetría (voltaje, corriente, potencia, frecuencia, factor de potencia y energía acumulada) junto con la gestión relacional de usuarios con roles y dispositivos IoT.

## Decisión:
Adoptar PostgreSQL 15 como base de datos relacional desplegada en contenedores Docker, gestionada mediante la sintaxis moderna de SQLAlchemy 2.x con tipado estricto y control de migraciones automatizado con Alembic.

## Consecuencia:
* **Positiva:** Integridad referencial sólida, consultas analíticas eficientes para futuras proyecciones de costos y un control de versiones de esquema impecable en entornos de producción
* **Negativa / Reto:** Cualquier cambio en los modelos de entidades ORM exige una planeación rigurosa de las migraciones para evitar bloqueos en el contenedor de base de datos.