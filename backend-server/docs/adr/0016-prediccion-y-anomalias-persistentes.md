# 0016: Predicción persistida y detección de anomalías conectada al modelo v2

* **Estatus:** Aceptado
* **Fecha:** 14 de septiembre de 2026

## Contexto

`app/services/cost_projection.py` y `app/services/anomaly_detector.py` ya existían, eran correctos y no dependían del ORM (funciones puras sobre listas de floats) — la etapa 9 solo tenía que conectarlos al modelo v2 y persistir sus resultados en `Prediction`/`AnomalyAlert`, sin tocar el algoritmo.

## Decisión

1. `app/services/predictions.py::get_or_generate_prediction`: perezoso y cacheado (reutiliza una `Prediction` de las últimas 24h si existe, en vez de recalcular) — evita montar un scheduler/worker separado, como pide explícitamente la spec para no sobre-diseñar el MVP.
2. `app/services/anomaly_alerts.py::evaluate_and_record_anomaly`: se llama desde `app/api/iot/router.py::receive_telemetry` justo después de persistir la lectura, en paralelo (no en lugar) del motor de reglas de corte — una anomalía nunca corta la energía por sí sola, son mecanismos independientes con historiales de código separados desde la etapa 5.
3. **`/api/v1/app/devices/{id}/prediction` cambió de forma**: en vez de recalcular `trend_wh_per_day`/`is_trending_up` al vuelo (etapa 6/8), ahora refleja directamente una fila persistida de `Prediction` (`horizon`, `projected_kwh`, `projected_cost`, `method`, `generated_at`). Se descartaron los campos de tendencia porque `Prediction` (definida desde la etapa 2) no los modela — guardar solo lo que la entidad define, en vez de inventar columnas nuevas para no perder esos campos, mantiene el esquema fiel a lo ya decidido.
4. **Omisión corregida de la etapa 2**: `Device` no tenía relationship a `Prediction` (a diferencia de `telemetry_readings`/`commands`/`events`/`anomaly_alerts`, que sí tenían `cascade="all, delete-orphan"`) — se detectó porque borrar un dispositivo con predicciones generadas fallaba con `IntegrityError`. Cambio de solo Python/ORM, no requiere migración (la FK ya existía).
5. Verificación de la métrica de la propuesta (margen de error <10%): con consumo diario constante conocido (2 kWh/día durante 5 días), la proyección mensual debe acercarse a 60 kWh — se comprobó con datos reales generados por el simulador de dispositivo, no solo la fórmula en aislamiento (que ya tenía sus propios tests desde el repo base).
6. `ANOMALY_DETECTOR=isolation_forest` se probó con un historial de 30 lecturas con variación pequeña — con solo 10 lecturas casi idénticas (el primer intento), `IsolationForest` no lograba aislar ni un valor 25× fuera de rango (limitación real del algoritmo con muestras 1D muy pequeñas y de varianza casi nula, no un bug de la integración) — quedó documentado en el propio test como razón del tamaño de muestra elegido.

## Consecuencias

* **Positivas:** ambas estrategias de detección quedan verificadas end-to-end contra la API real, no solo contra la función aislada; `/admin/anomalies` (etapa 7) pasa de estar siempre vacío a mostrar datos reales.
* **Negativas:** el consumidor de `/prediction` que existiera (ninguno todavía, sin frontend) tendría que adaptarse al cambio de forma de la respuesta.
