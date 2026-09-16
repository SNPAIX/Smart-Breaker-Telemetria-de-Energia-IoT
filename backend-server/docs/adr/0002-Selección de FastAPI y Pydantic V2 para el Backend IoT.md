# 0002: Selección de FastAPI y Pydantic V2 para el Backend IoT

* **Estatus:** Aceptado
* **Fecha:** 1 de Septiembre del 2026

## Contexto:
El proyecto requiere procesar peticiones HTTP de telemetría provenientes de múltiples dispositivos ESP32-C3 en tiempo real y exponer endpoints seguros para un panel administrativo. Se necesita validación de tipos estricta, alta concurrencia asíncrona y documentación automática de contratos de API bajo un estándar profesional.

## Decisión:
Utilizar FastAPI acoplado con Pydantic V2 como el núcleo del framework backend, aprovechando la ejecución asincrónica y la validación de esquemas basada en Rust para los payloads de corriente, voltaje y potencia enviados por el PZEM-004T.

## Consecuencia:
* **Positiva:** Se garantiza un rendimiento sobresaliente, una validación robusta de datos en tiempo de ejecución y una documentación interactiva instantánea (Swagger UI).
* **Negativa / Reto:** Requiere un dominio estricto de la sintaxis moderna de tipado en Python (Mapped, ConfigDict) y dependencias actualizadas como python-multipart.