// Cliente HTTP hacia /api/v1/iot/* (etapa 12) — telemetría, heartbeat,
// comandos pendientes y ACK. Nunca se llama directo desde el callback del
// PZEM: onPzemReading() solo evalúa el corte local (inmediato, sin red) y
// guarda la lectura para que iotClientLoop() la envíe en el siguiente
// ciclo del loop() principal — así una llamada HTTP lenta o colgada nunca
// retrasa el corte de seguridad ni corre en el contexto del callback.
#pragma once

void iotClientBegin();
void iotClientLoop();

void onPzemReading(float voltage, float current, float activePower,
                    float frequency, float powerFactor, float activeEnergyWh);
