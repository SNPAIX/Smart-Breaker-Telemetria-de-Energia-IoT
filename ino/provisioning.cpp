#include "provisioning.h"

#include <DNSServer.h>
#include <WebServer.h>
#include <WiFi.h>

#include "device_storage.h"

namespace {

enum class Mode
{
    UNINITIALIZED,
    ACCESS_POINT,
    STATION,
};

Mode currentMode = Mode::UNINITIALIZED;

WebServer server(80);
DNSServer dnsServer;
constexpr uint8_t DNS_PORT = 53;

unsigned long lastReconnectAttempt = 0;
constexpr unsigned long RECONNECT_INTERVAL_MS = 15000;

String apSsid()
{
    return "VoltGuard-Setup-" + suggestedPublicId();
}

void handleRoot()
{
    String html =
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>VoltGuard - Configuracion</title></head><body>"
        "<h1>VoltGuard</h1>";

    if (currentMode == Mode::ACCESS_POINT)
    {
        html +=
            "<p>Configura la red WiFi y la identidad del dispositivo. "
            "El identificador y el secreto vienen con el equipo (entregados "
            "al darlo de alta en la plataforma) — no los inventes.</p>"
            "<form method='POST' action='/save'>"
            "SSID: <input name='ssid'><br>"
            "Clave WiFi: <input name='password' type='password'><br>"
            "URL del backend (ej. https://miservidor.com): <input name='backend_url'><br>"
            "Identificador del dispositivo (public_id): "
            "<input name='public_id' value='" + suggestedPublicId() + "'><br>"
            "Secreto del dispositivo: <input name='device_secret' type='password'><br>"
            "<button type='submit'>Guardar y conectar</button>"
            "</form>";
    }
    else
    {
        html +=
            "<p>Dispositivo conectado.</p>"
            "<p>Identificador configurado: <b>" + getPublicId() + "</b></p>"
            "<p>Usa ese identificador en la app para vincular este dispositivo a tu cuenta.</p>";
    }

    html += "</body></html>";
    server.send(200, "text/html", html);
}

void handleSave()
{
    if (!server.hasArg("ssid") || server.arg("ssid").length() == 0)
    {
        server.send(400, "text/plain", "Falta el SSID.");
        return;
    }
    if (!server.hasArg("public_id") || server.arg("public_id").length() == 0
        || !server.hasArg("device_secret") || server.arg("device_secret").length() == 0)
    {
        server.send(400, "text/plain", "Falta el identificador o el secreto del dispositivo.");
        return;
    }

    saveWifiCredentials(server.arg("ssid"), server.arg("password"));
    savePublicId(server.arg("public_id"));
    saveDeviceCredential(server.arg("device_secret"));
    if (server.hasArg("backend_url") && server.arg("backend_url").length() > 0)
    {
        saveBackendBaseUrl(server.arg("backend_url"));
    }

    server.send(200, "text/html", "<html><body>Guardado. Reiniciando...</body></html>");
    delay(500);
    ESP.restart();
}

void startAccessPoint()
{
    currentMode = Mode::ACCESS_POINT;

    WiFi.mode(WIFI_AP);
    WiFi.softAP(apSsid().c_str());

    dnsServer.start(DNS_PORT, "*", WiFi.softAPIP());

    server.onNotFound(handleRoot);  // portal cautivo: cualquier ruta cae al formulario
    server.on("/", handleRoot);
    server.on("/save", HTTP_POST, handleSave);
    server.begin();

    Serial.println();
    Serial.println("====================================");
    Serial.print("Portal de aprovisionamiento activo: ");
    Serial.println(apSsid());
    Serial.println("====================================");
}

void startStation()
{
    currentMode = Mode::STATION;

    WiFi.mode(WIFI_STA);
    WiFi.begin(getWifiSsid().c_str(), getWifiPassword().c_str());

    server.on("/", handleRoot);
    server.begin();
}

}  // namespace

void provisioningBegin()
{
    if (hasWifiCredentials())
    {
        startStation();
    }
    else
    {
        startAccessPoint();
    }
}

void provisioningLoop()
{
    if (currentMode == Mode::ACCESS_POINT)
    {
        dnsServer.processNextRequest();
        server.handleClient();
        return;
    }

    server.handleClient();

    if (WiFi.status() != WL_CONNECTED)
    {
        unsigned long now = millis();
        if (now - lastReconnectAttempt >= RECONNECT_INTERVAL_MS)
        {
            lastReconnectAttempt = now;
            WiFi.disconnect();
            WiFi.begin(getWifiSsid().c_str(), getWifiPassword().c_str());
        }
    }
}

bool isNetworkReady()
{
    return currentMode == Mode::STATION && WiFi.status() == WL_CONNECTED;
}
