# 0010: Autorización por sitio y autenticación de dispositivo

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

La spec exige que un usuario solo acceda a recursos de sitios donde tenga membresía, y que cada dispositivo tenga credenciales propias, distintas del JWT de usuario (brecha de seguridad real del repo base: `POST /api/v1/telemetry/readings` no tenía ninguna autenticación — ver `roadmap/01-gap-analysis.md`). El esquema v2 (etapa 2) ya tiene `SiteMember` y `DeviceCredential`; faltaba el mecanismo de verificación.

## Decisión

1. `get_current_site_member(site_id, current_user, db)` en `app/core/dependencies.py`: dependencia que resuelve la membresía del usuario autenticado en `site_id` (403 si no existe). Pensada para inyectarse en rutas `/api/v1/app/{site_id}/...` de la etapa 6 — FastAPI resuelve `site_id` como parámetro de ruta también dentro de una dependencia.
2. `get_current_device(authorization, db)`: autenticación de dispositivo vía header `Authorization: Device <public_id>:<secret>`, verificando el secreto contra `DeviceCredential.secret_hash` con el mismo hashing bcrypt que usuarios (`verify_password`, reutilizada tal cual — un secreto de dispositivo es, en esencia, una contraseña, no hay razón para duplicar el mecanismo). Rechaza (401) credencial revocada, dispositivo inexistente, dispositivo sin credencial emitida, o encabezado malformado.
3. `app/services/device_auth.py::issue_device_credential(device)`: genera el secreto (`secrets.token_urlsafe(32)`), persiste solo su hash, devuelve el secreto en texto plano una única vez. Es un servicio real (no un script de prueba) porque las etapas 4 y 7 lo van a llamar tal cual desde sus endpoints de alta de dispositivo — construirlo ahora evita reimplementarlo después.
4. No se construye todavía el flujo de aprovisionamiento completo (AP → WiFi → vínculo a cuenta) ni el endpoint público de alta de dispositivo — eso es la etapa 4/7. Esta etapa solo deja listo el mecanismo de verificación que esos flujos van a usar.

## Consecuencias

* **Positivas:** la autenticación de dispositivo queda desacoplada de la de usuario desde el diseño (ciclos de vida y revocación independientes), sin esperar a que exista un endpoint público que la dispare — se pudo probar de punta a punta con un dispositivo creado directamente en la base de datos de pruebas.
* **Negativas:** ninguna ruta real usa `get_current_device`/`get_current_site_member` todavía (se prueban llamando las funciones directamente, no vía HTTP) — quedan sin ejercitar por un router real hasta las etapas 4 y 6.
