# front/ — Dashboard administrativo

React + Vite + TypeScript. Se construye a partir de la etapa [`roadmap/stages/13-frontend-admin-dashboard.md`](../roadmap/stages/13-frontend-admin-dashboard.md).

Consume exclusivamente `backend-server` vía `/api/v1/app/...` (usuario) y `/api/v1/admin/...` (administración). No debe contener lógica de negocio ni acceso directo a PostgreSQL o al ESP32.
