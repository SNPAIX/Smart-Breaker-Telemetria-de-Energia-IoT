# front/ — Dashboard administrativo

React + Vite + TypeScript. Consume exclusivamente `backend-server` vía `/api/v1/app/...` (usuario) y `/api/v1/admin/...` (administración). No contiene lógica de negocio ni acceso directo a PostgreSQL o al ESP32.

## Desarrollo

```bash
npm install
cp .env.example .env.local   # ajustar VITE_API_BASE_URL si el backend no está en localhost:8000
npm run dev
```

## Tipos generados desde el backend

Los tipos de `src/api/schema.ts` se generan directamente del OpenAPI real del backend — nunca se escriben a mano:

```bash
npm run generate:types   # requiere el backend corriendo en VITE_API_BASE_URL
```

Nota: FastAPI namespaca los nombres de schema que colisionan entre módulos (ej. `UserOut` existe tanto en `app.schemas.auth` como en `app.schemas.admin_api`), por lo que algunos tipos en `src/api/types.ts` referencian la forma `app__schemas__<modulo>__<Nombre>`.

## Estructura

- `src/api/` — cliente HTTP (`client.ts`), tipos generados (`schema.ts`) y hooks de React Query (`hooks.ts`).
- `src/auth/` — contexto de sesión (JWT decodificado del lado del cliente, sin endpoint `/me`) y rutas protegidas.
- `src/pages/` — vistas de usuario final; `src/pages/admin/` — vistas administrativas.

## Build

```bash
npm run build   # tsc -b && vite build
```
