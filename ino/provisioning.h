// Aprovisionamiento WiFi: estado "recién sacado de caja" (etapa 12).
//
// Sin credenciales guardadas -> levanta un punto de acceso local con un
// portal cautivo mínimo donde el instalador ingresa el SSID/clave de la
// red y, opcionalmente, la URL del backend. Con credenciales guardadas ->
// se conecta directo en modo estación (STA), con reconexión automática.
//
// Una vez en STA, el mismo portal (ahora en la IP de la LAN) muestra el
// public_id del dispositivo para que el usuario lo use al vincularlo a una
// cuenta desde la app (POST /api/v1/app/devices/claim, etapa 6) — el
// firmware no necesita saber nada más del vínculo.
#pragma once

void provisioningBegin();
void provisioningLoop();
bool isNetworkReady();
