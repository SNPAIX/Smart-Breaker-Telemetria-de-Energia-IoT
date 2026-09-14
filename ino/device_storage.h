// Persistencia en NVS (Preferences) de todo lo que el dispositivo necesita
// recordar entre reinicios: credenciales WiFi, URL del backend, identidad
// y credencial propias del dispositivo (etapa 3/7), y el umbral de corte
// crítico sincronizado desde el servidor (etapa 5) — este último es lo que
// permite el corte local sin depender de que haya red en ese momento.
#pragma once

#include <Arduino.h>

// Umbral de fábrica: seguro por defecto si el dispositivo nunca llegó a
// sincronizar un perfil real con el backend.
constexpr float FACTORY_DEFAULT_MAX_CURRENT_A = 10.0f;

void deviceStorageBegin();

bool hasWifiCredentials();
String getWifiSsid();
String getWifiPassword();
void saveWifiCredentials(const String& ssid, const String& password);
void clearWifiCredentials();

String getBackendBaseUrl();
void saveBackendBaseUrl(const String& url);

// `public_id` y secreto los emite el backend al dar de alta el dispositivo
// (POST /api/v1/admin/devices, etapa 7) — no el firmware. Llegan al
// dispositivo por el mismo portal de aprovisionamiento (ver
// provisioning.cpp), igual que la clave WiFi: se le entregan al instalador
// junto con el equipo (ej. impresos en una etiqueta), no se autogeneran.
bool hasPublicId();
String getPublicId();
void savePublicId(const String& publicId);

// Identificador sugerido (derivado de la MAC) para prellenar el formulario
// de aprovisionamiento — no es el que se usa si el instalador captura otro.
String suggestedPublicId();

bool hasDeviceCredential();
String getDeviceSecret();
void saveDeviceCredential(const String& secret);

float getLocalMaxCurrentA();
void saveLocalMaxCurrentA(float amps);
