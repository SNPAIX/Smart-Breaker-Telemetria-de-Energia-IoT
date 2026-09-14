# 0017: Notificaciones in-app y adaptador de push

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

Ni `Event` ni `AnomalyAlert` generaban ninguna `Notification` — las tablas existían desde la etapa 2 pero nada las poblaba. La spec exige respetar `NotificationPreference` por canal y no bloquear la respuesta HTTP del flujo que origina la notificación.

## Decisión

1. `app/services/notifications.py` es el **único** responsable de convertir `Event`/`AnomalyAlert` en `Notification` — el motor de reglas (etapa 5) y el detector de anomalías (etapa 9) siguen sin saber que las notificaciones existen, evitando la duplicación de lógica que pide explícitamente el roadmap.
2. Se ejecuta como `BackgroundTasks` de FastAPI, disparado desde `POST /api/v1/iot/telemetry` (tras un evento crítico o una anomalía) y desde `POST /api/v1/app/devices/{id}/reactivate` (evento `MANUAL_REACTIVATION`) — nunca bloquea la respuesta que debe cumplir la métrica de <500ms. Abre su propia sesión de base de datos (`SessionLocal()` nueva) porque la sesión de la request ya se cerró para cuando la tarea de fondo corre.
3. **Sin credenciales de un proveedor push real** (FCM/Expo/APNs) — caso explícito de "falta una credencial externa real" en las reglas del roadmap. Se implementó la interfaz completa `PushSender` (`app/services/push.py`) con un adaptador `NoopPushSender` que registra el intento en el log estructurado; conectar un proveedor real es agregar una clase nueva con la misma interfaz y cambiar `get_push_sender()`, sin tocar el resto del sistema.
4. Canal `in_app` habilitado por defecto si el usuario no tiene preferencia explícita; canal `push` deshabilitado por defecto (opt-in, no opt-out) — evita spamear push sin consentimiento explícito.
5. `PATCH /api/v1/app/notifications/preferences` (ya existía desde la etapa 6) no necesitó cambios — ya soportaba habilitar/deshabilitar por canal arbitrario. No se agregó granularidad por tipo de evento: el roadmap lo dejaba opcional ("si es razonable sin sobre-diseñar") y un canal alcanza para el MVP.

## Consecuencias

* **Positivas:** verificado con dos `SiteMember` reales — ambos reciben la notificación in-app de un `CRITICAL_OVERLOAD`, pero el envío push (capturado con un `PushSender` de prueba, no parseando logs) solo ocurre para quien lo habilitó explícitamente. Un usuario con `in_app` deshabilitado no genera ninguna fila `Notification`.
* **Negativas:** hasta que se conecte un proveedor push real, cualquier notificación "push" solo queda registrada en el log — no llega a ningún dispositivo físico. Documentado explícitamente en `push.py`, no oculto.
