# 0008: Settings centralizado y reorganización de routers en api/{iot,app,admin}

* **Estatus:** Aceptado
* **Fecha:** 13 de septiembre de 2026

## Contexto

VoltGuard v2 exige tres superficies de API claramente separadas (`/api/v1/iot`, `/api/v1/app`, `/api/v1/admin`), con servicios compartidos entre `app` y `admin` para no duplicar lógica de negocio. El repo base organizaba las rutas en `app/routers/` (`auth.py`, `admin.py`, `operative.py`) sin esa separación explícita: `operative.py` mezclaba el endpoint de ingesta de telemetría (conceptualmente IoT) con rutas de solo-administrador (umbral de seguridad, eventos, alertas, proyección de costo). Además, la configuración se leía con `os.getenv(...)` disperso en `core/security.py`, `db.py`, `core/logging_config.py` y `routers/operative.py`, sin un punto único de verdad ni valores por defecto documentados en un solo lugar.

## Decisión

1. Se introduce `app/config.py::Settings` (pydantic-settings `BaseSettings`) como único punto de lectura de variables de entorno (`DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ENVIRONMENT`, `LOG_LEVEL`, `ANOMALY_DETECTOR`). Los módulos que antes llamaban `os.getenv` ahora importan `settings`.
2. `app/routers/` se retira. Su contenido se reubica según a qué superficie pertenece conceptualmente, sin cambiar comportamiento ni rutas HTTP en este paso:
   - `routers/auth.py` → `app/api/auth.py` (sin cambios de contenido).
   - `routers/operative.py::router` (ingesta de telemetría, `/api/v1/telemetry/readings`) → `app/api/iot/router.py`. Sigue sin autenticación de dispositivo por ahora — eso lo resuelve la etapa 4 del roadmap, que reemplaza este endpoint por la superficie `/api/v1/iot/*` real.
   - `routers/operative.py::devices_router` (umbral de seguridad, eventos, alertas, proyección de costo — protegidas con `get_current_admin`) → `app/api/admin/devices_intelligence.py`, junto al `admin.py` original (`app/api/admin/router.py`), ya que ambas ya eran, de facto, superficie administrativa.
   - `app/api/app/` se crea vacío a propósito: hoy no existe ningún endpoint de usuario final en el repo base (ver `roadmap/01-gap-analysis.md`); se llena en la etapa 6.

## Consecuencias

* **Positivas:** un solo lugar para ver/cambiar configuración; la estructura de carpetas ya refleja la separación de superficies que pide la spec, antes de que cada una tenga contenido propio; ningún test existente tuvo que cambiar (todos importan `app.main:app` o módulos de `app.core`/`app.models`, no `app.routers` directamente).
* **Negativas:** `app/api/admin/devices_intelligence.py` importa `_get_device_or_404` desde `app/api/iot/router.py` para no duplicar ese helper — es un acoplamiento pequeño entre dos superficies que se debe revisar en la etapa 7 (API administrativa completa), cuando probablemente ese helper se mueva a un servicio compartido (`app/services/devices.py`).
