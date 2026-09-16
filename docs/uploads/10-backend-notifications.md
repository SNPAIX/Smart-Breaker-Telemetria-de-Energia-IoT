# Etapa 10 — Notificaciones

- `Event`/`AnomalyAlert` ahora generan `Notification` real, vía `BackgroundTasks` (no bloquea la respuesta HTTP).
- Canal `in_app` habilitado por defecto, `push` deshabilitado por defecto (opt-in).
- Sin proveedor push real (FCM/Expo) todavía: `PushSender`/`NoopPushSender` documentados, listos para conectar uno real sin tocar el resto del sistema.
- Verificado end-to-end: 82 tests, 96.09% cobertura, `ruff`/`mypy` limpios; dos usuarios reales confirman in-app siempre + push solo si está habilitado, y un usuario con in-app deshabilitado no recibe nada.
