# 0014: API administrativa completa (`/api/v1/admin/*`)

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

El repo base solo tenía `POST /api/v1/admin/devices` (con el esquema viejo, retirado en la etapa 2) y `GET /dashboard/metrics`. La spec pide CRUD completo de usuarios/sitios/dispositivos/perfiles, reasignación, consulta de eventos y anomalías, métricas globales y agrupadas, y estado online/offline — todo reutilizando los servicios de la etapa 6, sin duplicar lógica de negocio.

## Decisión

1. Servicios nuevos, todos en `app/services/`, ninguno en el router: `users.py` (CRUD de usuario), `device_profiles.py` (CRUD de perfil, bloquea borrar uno en uso), `admin_metrics.py` (global/por-sitio/por-perfil/overview). `sites.py` y `devices.py` (etapa 6) se extendieron con las operaciones administrativas (`create_site`, `delete_site` con guarda de dispositivos asignados, `create_device` con emisión de credencial vía `issue_device_credential` de la etapa 3, `admin_reassign_device`, `list_events` generalizado con filtros opcionales).
2. **"Online" nunca es una columna**: `is_device_online(device)` compara `last_seen_at` contra `settings.device_online_threshold_seconds` (nuevo, default 300s) en el momento de la consulta — no hay un booleano que sincronizar.
3. **Sin puerta trasera de reactivación**: `/api/v1/admin/*` no expone ningún endpoint de `switch`/`reactivate` — esas operaciones viven únicamente en `/api/v1/app/*` (etapa 6). Un admin que necesite reactivar un dispositivo bloqueado debe hacerlo por la misma vía que un usuario dueño del sitio, con la misma trazabilidad (`Event(type="MANUAL_REACTIVATION")`).
4. **Alta de dispositivo devuelve el secreto una sola vez** (`DeviceCreateOut.secret`), igual que `issue_device_credential` — se verificó con el simulador de la etapa 4 que esa credencial funciona de verdad contra `/api/v1/iot/telemetry`, no solo que se guardó un hash con la forma correcta.
5. Borrados con guarda de integridad, no en cascada silenciosa: borrar un `Site` con dispositivos asignados, o un `DeviceProfile` en uso, responde 409 en vez de desvincular/reasignar solo.
6. `GET /admin/anomalies` es mínimo viable a propósito (lista `AnomalyAlert`, hoy siempre vacía) — la etapa 9 es la que puebla esa tabla.

## Consecuencias

* **Positivas:** cero duplicación de lógica de negocio entre `/api/v1/app` y `/api/v1/admin` — ambos routers son delgados sobre los mismos servicios, verificado al no haber tenido que reescribir ninguna consulta.
* **Negativas:** ninguna todavía — esta etapa cierra la superficie CRUD completa que la spec pedía desde la auditoría inicial.
