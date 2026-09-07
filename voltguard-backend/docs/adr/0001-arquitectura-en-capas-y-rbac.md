# 0001. Arquitectura en Capas y Control de Acceso (RBAC) para VoltGuard

* **Estatus:** Aceptado
* **Fecha:** 2026-09-06

## Contexto
El sistema VoltGuard requiere gestionar telemetría de energía en tiempo real, corte proactivo de corriente (Smart Breaker) y visibilidad de consumo tanto para el usuario residencial como para administradores de grupos/edificios.

## Decisión
Se adopta una **Arquitectura en Capas desacoplada con DIP (Dependency Inversion Principle)** dividida en dos contextos de uso principales:
1. **API Operativa (`EndUser` / IoT Edge):** Enfocada en la ingesta de lecturas desde el microcontrolador (`POST /telemetry/readings`), control de relé y notificaciones directas.
2. **API de Administración (`Admin` / `Manager`):** Enfocada en el Dashboard agrupado (`GET /admin/dashboard/metrics`), CRUD de usuarios y asignación de dispositivos por grupos.

## Consecuencias
* **Positivas:** Separación clara de responsabilidades, seguridad aislada por roles (JWT), y facilidad para realizar pruebas aisladas con Pytest.
* **Negativas:** Mayor cantidad de código base (*boilerplate*) al requerir esquemas de Pydantic V2 específicos para cada rol y vista.