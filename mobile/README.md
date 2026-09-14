# mobile/ — Aplicación móvil de usuario final

Capacitor empaquetando la UI web de `front/` (React + Vite + TypeScript) para Android/iOS, más un plugin nativo de asistente de voz-a-comando on-device. Decisión cerrada — ver el detalle y el motivo en la etapa correspondiente.

La app **no** se comunica directamente con PostgreSQL ni con el ESP32. Toda operación pasa por `backend-server` vía `/api/v1/app/...`.
