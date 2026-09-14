# 0013: API de usuario final (`/api/v1/app/*`)

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

Era la brecha funcional más grande del repo base: no existía ningún endpoint de usuario final (ver `roadmap/01-gap-analysis.md`). La spec exige que un usuario solo vea/controle sitios y dispositivos donde tenga membresía, y que `/api/v1/app` y `/api/v1/admin` (etapa 7) compartan servicios sin duplicar lógica de negocio.

## Decisión

1. `app/services/sites.py` y `app/services/devices.py`: toda la lógica de negocio de esta superficie vive ahí, no en el router — la etapa 7 los reutiliza tal cual, solo cambia la autorización (admin vs. dueño del sitio).
2. `get_authorized_device` (nueva dependencia en `app/core/dependencies.py`): resuelve un `Device` por `device_id` y confirma membresía del usuario en `device.site_id`, respondiendo **404 tanto si el dispositivo no existe como si no está autorizado** — decisión consciente para no revelarle a un usuario sin acceso si un `device_id` ajeno existe.
3. `switch_device`/`reactivate_device` en `app/services/devices.py` implementan la regla de la etapa 5: `switch` a `ON` con `Device.is_locked_out=True` responde 409; solo `reactivate_device` limpia el bloqueo, deja un `Event(type="MANUAL_REACTIVATION", payload={"reactivated_by_user_id": ...})` para trazabilidad, y emite `Command(SET_RELAY_ON)`.
4. `/devices/claim`: como `site_id` viaja en el body (no hay `{site_id}` en el path), no se pudo reusar `get_current_site_member` — la membresía se valida en línea dentro del handler. `claim_device` rechaza (409) reclamar un dispositivo ya vinculado.
5. **Métricas/costo/predicción minimalistas a propósito** (etapas 8/9 sin construir todavía): `/metrics` devuelve la última lectura + conteo de días con datos; `/cost` y `/prediction` reutilizan `project_monthly_cost` (ya existente y correcto, ver ADR previas) calculado al vuelo con `DEFAULT_TARIFF_MXN_PER_KWH`, documentado en la propia respuesta (`note`) como pendiente de persistirse con `Tariff`/`Prediction` reales. `/notifications` y `PATCH /notifications/preferences` sí quedan completamente funcionales (upsert real de `NotificationPreference`) aunque hoy no exista ningún flujo que genere notificaciones (eso es la etapa 10) — no dependen de que ese flujo exista para ser útiles y probables.
6. Se corrigió una omisión de la etapa 2: `User.notifications` y `User.notification_preferences` no tenían `cascade="all, delete-orphan"` (a diferencia de `User.site_memberships`, que sí) — se detectó al escribir el test de preferencias, que fallaba con `IntegrityError` al limpiar el usuario de prueba. Cambio de solo Python/ORM, no requiere migración.

## Consecuencias

* **Positivas:** aislamiento entre usuarios verificado con dos cuentas reales, cada una con su propio sitio y dispositivo — una nunca ve nada de la otra (403 a nivel de sitio, 404 a nivel de dispositivo).
* **Negativas:** `/metrics`, `/cost` y `/prediction` van a cambiar de forma cuando lleguen las etapas 8 y 9 (de "calculado al vuelo" a "persistido") — es un cambio esperado, no una regresión.
