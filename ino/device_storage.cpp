#include "device_storage.h"

#include <Preferences.h>
#include <WiFi.h>

namespace {

constexpr char NVS_NAMESPACE[] = "voltguard";
constexpr char KEY_WIFI_SSID[] = "wifi_ssid";
constexpr char KEY_WIFI_PASS[] = "wifi_pass";
constexpr char KEY_BACKEND_URL[] = "backend_url";
constexpr char KEY_PUBLIC_ID[] = "public_id";
constexpr char KEY_DEVICE_SECRET[] = "dev_secret";
constexpr char KEY_MAX_CURRENT_A[] = "max_current_a";

// Sin URL configurada de fábrica: el instalador la ingresa durante el
// aprovisionamiento (portal cautivo) junto con las credenciales WiFi.
constexpr char DEFAULT_BACKEND_URL[] = "";

Preferences preferences;

}  // namespace

void deviceStorageBegin()
{
    preferences.begin(NVS_NAMESPACE, false);
}

bool hasWifiCredentials()
{
    return preferences.isKey(KEY_WIFI_SSID) && preferences.getString(KEY_WIFI_SSID).length() > 0;
}

String getWifiSsid()
{
    return preferences.getString(KEY_WIFI_SSID, "");
}

String getWifiPassword()
{
    return preferences.getString(KEY_WIFI_PASS, "");
}

void saveWifiCredentials(const String& ssid, const String& password)
{
    preferences.putString(KEY_WIFI_SSID, ssid);
    preferences.putString(KEY_WIFI_PASS, password);
}

void clearWifiCredentials()
{
    preferences.remove(KEY_WIFI_SSID);
    preferences.remove(KEY_WIFI_PASS);
}

String getBackendBaseUrl()
{
    return preferences.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL);
}

void saveBackendBaseUrl(const String& url)
{
    preferences.putString(KEY_BACKEND_URL, url);
}

bool hasPublicId()
{
    return preferences.isKey(KEY_PUBLIC_ID) && preferences.getString(KEY_PUBLIC_ID).length() > 0;
}

String getPublicId()
{
    return preferences.getString(KEY_PUBLIC_ID, "");
}

void savePublicId(const String& publicId)
{
    preferences.putString(KEY_PUBLIC_ID, publicId);
}

String suggestedPublicId()
{
    // Solo para prellenar el formulario de aprovisionamiento — el
    // public_id real lo asigna el backend al dar de alta el dispositivo
    // (etapa 7), que puede o no coincidir con esta sugerencia.
    uint8_t mac[6];
    WiFi.macAddress(mac);

    char generated[20];
    snprintf(
        generated, sizeof(generated), "VG-%02X%02X%02X%02X%02X%02X",
        mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]
    );
    return String(generated);
}

bool hasDeviceCredential()
{
    return preferences.isKey(KEY_DEVICE_SECRET) && preferences.getString(KEY_DEVICE_SECRET).length() > 0;
}

String getDeviceSecret()
{
    return preferences.getString(KEY_DEVICE_SECRET, "");
}

void saveDeviceCredential(const String& secret)
{
    preferences.putString(KEY_DEVICE_SECRET, secret);
}

float getLocalMaxCurrentA()
{
    return preferences.getFloat(KEY_MAX_CURRENT_A, FACTORY_DEFAULT_MAX_CURRENT_A);
}

void saveLocalMaxCurrentA(float amps)
{
    preferences.putFloat(KEY_MAX_CURRENT_A, amps);
}
