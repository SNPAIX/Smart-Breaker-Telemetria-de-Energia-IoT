# 0015: Tarifas persistentes y costo real prorrateado por día

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

`/api/v1/app/devices/{id}/cost` (etapa 6) calculaba una proyección mensual usando `DEFAULT_TARIFF_MXN_PER_KWH` como constante — funcional pero explícitamente marcado como pendiente ("la etapa 8 la persiste con Tariff real"). La spec pide `Tariff` como entidad real, con histórico (no sobrescribir al cambiar de precio), y que el costo de un período con cambio de tarifa a mitad de camino refleje el prorrateo real, no un solo precio aplicado a todo.

## Decisión

1. `app/services/tariffs.py`: `create_tariff` cierra (`valid_to`) la tarifa abierta anterior del sitio en vez de sobrescribirla — el histórico completo queda consultable (`list_tariffs`). `get_active_tariff(site_id, at)` resuelve qué tarifa regía en una fecha concreta.
2. **Se reinterpretó `/cost` como costo real del período analizado, no una proyección** — la proyección a futuro (`/prediction`) ya cubría ese caso y no necesita tarifa exacta por día, solo la tendencia de consumo. Mezclar ambas cosas en un solo endpoint (como hacía la etapa 6 provisionalmente) confundía "cuánto gasté" con "cuánto voy a gastar". `DeviceCostOut` cambió de forma (`projected_monthly_*` → `total_kwh`/`total_cost`/`used_default_tariff`) — cambio de contrato esperado, ya anunciado en la nota que dejó la etapa 6.
3. `app/services/costs.py::compute_cost_breakdown`: reutiliza `compute_daily_consumption` (etapa 6/8, ahora devuelve `(fecha, Wh)` en vez de solo `Wh` — necesario para saber qué tarifa aplicar cada día) y para cada día busca la tarifa vigente ESE día, no la de hoy. Si el sitio no tiene ninguna tarifa configurada, cae en `DEFAULT_TARIFF_MXN_PER_KWH` y lo marca (`used_default_tariff=True`) en vez de fallar.
4. CRUD de `Tariff` expuesto solo en `/api/v1/admin/sites/{id}/tariffs` (no en `/api/v1/app`) — configurar el precio de la energía es una decisión administrativa/de facturación, no algo que un dueño de sitio ajuste desde la app de usuario final en este MVP.
5. Verificado con un caso concreto no ambiguo: tarifa A (2.0/kWh) vigente hasta el día -1, tarifa B (3.0/kWh) desde el día -1; consumo de 1 kWh el día -2 y 2 kWh el día -1 → costo esperado 2.0 + 6.0 = 8.0, **no** 9.0 (que sería aplicar 3.0 a los 3 kWh totales) — el test compara explícitamente contra ese resultado "sin prorrateo" para confirmar que la diferencia es real.

## Consecuencias

* **Positivas:** el costo mostrado a un usuario ahora es contable de verdad (aguanta una auditoría: "¿por qué me cobraron esto?" tiene una respuesta por día y por tarifa vigente), no una aproximación.
* **Negativas:** `DeviceCostOut` rompe su forma anterior — cualquier cliente que ya integró contra la respuesta de la etapa 6 debe actualizarse. Como no hay frontend todavía (etapas 13/14 pendientes), no hay consumidores reales afectados.
