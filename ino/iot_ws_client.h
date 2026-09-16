// Canal WebSocket persistente hacia /api/v1/iot/ws — acelera la entrega
// de comandos a milisegundos en vez de esperar la próxima telemetría o el
// poll de respaldo cada 3s (iot_client.cpp, que sigue intacto y activo:
// este módulo nunca reemplaza esos caminos, solo se adelanta cuando puede
// conectarse). Corre en el mismo hilo que loop() — no crea ninguna tarea
// propia, así que no introduce ninguna condición de carrera nueva con
// pendingReading/relayState.
#pragma once

void iotWsClientBegin();
void iotWsClientLoop();
