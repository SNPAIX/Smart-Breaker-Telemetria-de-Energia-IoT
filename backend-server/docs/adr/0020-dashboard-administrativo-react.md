# 0020: Dashboard administrativo (React + Vite + TypeScript)

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

Primera pieza de frontend del proyecto — no existía nada en `front/` más que un `README.md`. La spec exige un dashboard funcional (no una maqueta) que consuma el backend real, con manejo real de estados de error/carga y del bloqueo por `CRITICAL_OVERLOAD`.

## Decisión

1. **Tipos generados desde el OpenAPI real** (`openapi-typescript` contra `http://localhost:8000/openapi.json`, `npm run generate:types`) en vez de escritos a mano — nunca se duplican las formas que ya definen los schemas Pydantic. Esto expuso una colisión de nombres real en el backend (`UserOut` existe en `app.schemas.auth` y en `app.schemas.admin_api`; `DeviceStateOut` en `app.schemas.app_api` y en `app.schemas.iot`) — FastAPI los namespaca automáticamente (`app__schemas__<modulo>__<Nombre>`) en el OpenAPI, así que `front/src/api/types.ts` referencia la forma correcta explícitamente. Es un rough edge de nomenclatura en el backend, no un bug — documentado aquí para quien lo quiera limpiar después (renombrar una de las dos clases en cada par).
2. **React Query** para todo el estado de servidor (sin Redux ni store global) — el detalle de dispositivo usa `refetchInterval` (polling cada 5s) para que un bloqueo por evento crítico se refleje en la UI sin que el usuario recargue, tal como pide el criterio de cierre.
3. **JWT decodificado del lado del cliente** (`src/auth/jwt.ts`) para saber el rol del usuario autenticado — no existe un endpoint `/me` en el backend, y agregar uno solo para esto habría sido innecesario: el rol ya viaja en el propio token (`create_access_token(subject, role)`, etapa 3).
4. **Brecha de backend descubierta y corregida durante la integración**: no existía ningún endpoint para agregar un usuario a un sitio (`SiteMember` solo se creaba manualmente en los tests desde la etapa 2). Sin esto, el flujo real de onboarding (admin crea sitio → agrega usuario → usuario ve su sitio) era imposible de ejecutar de punta a punta. Se agregó `POST/GET/DELETE /api/v1/admin/sites/{id}/members` (`app/services/sites.py::add_site_member/list_site_members/remove_site_member`), con su propio test (`test_admin_can_add_and_remove_site_members`).
5. **Verificación sin navegador, explícita**: este entorno no tiene una herramienta de automatización de navegador disponible, así que no se hizo una verificación visual real. En su lugar, se corrió un script Node que reproduce exactamente cada llamada de `src/api/hooks.ts` (login, sitios, dispositivos, sobrecarga real vía el simulador HTTP, bloqueo reflejado, `switch` rechazado con 409, reactivación, costo, predicción, overview admin) contra el backend real — confirma que el contrato completo funciona, pero **no reemplaza una prueba visual real en un navegador**, que queda pendiente.

## Consecuencias

* **Positivas:** el dashboard consume datos 100% reales desde el primer commit — no hay una sola respuesta simulada o hardcodeada en el código de la UI. La brecha de `SiteMember` se descubrió y cerró antes de que llegara a producción, precisamente por intentar ejercitar el flujo completo en vez de probar endpoints aislados.
* **Negativas:** sin verificación visual real en un navegador — un defecto de renderizado, CSS roto, o un flujo de clics que no funcione (aunque los datos sean correctos) no se habría detectado. Queda como pendiente explícito para quien tenga acceso a un navegador o herramienta de automatización.
