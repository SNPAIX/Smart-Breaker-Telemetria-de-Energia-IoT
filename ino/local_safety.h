// Corte crítico LOCAL (nivel local de la filosofía de seguridad de dos
// niveles): funciona aunque no haya WiFi ni backend disponible. El umbral
// se lee de NVS (sincronizado desde el servidor cuando hay conectividad,
// con un default de fábrica seguro si nunca se sincronizó — ver
// device_storage.h).
#pragma once

// Evalúa la corriente contra el umbral local y corta de inmediato
// (setRelay(false)) si se excede. Devuelve true si cortó en esta llamada.
// No hace ninguna llamada de red — eso es responsabilidad de quien la
// invoca (ver iot_client.cpp), que reporta el evento best-effort después.
bool evaluateLocalCriticalCutoff(float currentA);
