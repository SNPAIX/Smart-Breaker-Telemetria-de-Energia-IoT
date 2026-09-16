# Etapa 13 — Dashboard administrativo (React)

- Vite + React + TypeScript, tipos generados desde el OpenAPI real del backend (nunca a mano).
- React Query con polling en el detalle de dispositivo para reflejar bloqueos sin recargar.
- Login con JWT decodificado del lado del cliente (sin endpoint `/me` nuevo).
- **Brecha de backend descubierta y corregida en esta etapa**: no existía forma de agregar un usuario a un sitio — se agregó `POST/GET/DELETE /api/v1/admin/sites/{id}/members` con su test.
- Verificado: `npm run build` sin errores de TypeScript; flujo completo (login, sitios, dispositivos, sobrecarga real → bloqueo → rechazo de switch → reactivación → costo/predicción → overview admin) confirmado con un script contra el backend real reproduciendo cada llamada exacta del frontend.
- **Sin verificación visual en navegador real** — no hay herramienta de automatización de navegador en este entorno; queda pendiente explícito.
