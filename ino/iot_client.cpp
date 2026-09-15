#include "iot_client.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <time.h>

#include "device_storage.h"
#include "hardware_bridge.h"
#include "local_safety.h"
#include "provisioning.h"

namespace {

constexpr unsigned long HEARTBEAT_INTERVAL_MS = 30000;
// Bajado de 10s a 3s (14-sep, HIL real): con el PZEM leyendo seguido, la
// telemetria ya viaja casi continua y ahora entrega tambien cualquier
// comando pendiente (ver receive_telemetry en el backend) — este poll
// solo es la red de respaldo para cuando no hay lecturas del PZEM
// (ej. sensor desconectado), asi que 3s sigue siendo poco trafico.
constexpr unsigned long COMMAND_POLL_INTERVAL_MS = 3000;
// 1 de enero de 2020 en epoch — si el reloj del ESP32 reporta menos que
// esto, todavía no se sincronizó por NTP.
constexpr time_t MIN_PLAUSIBLE_EPOCH = 1577836800;

unsigned long localSequence = 0;
unsigned long lastHeartbeatOrTelemetryAt = 0;
unsigned long lastCommandPollAt = 0;
bool timeSynced = false;

struct PendingReading
{
    bool pending = false;
    float voltage = 0;
    float current = 0;
    float activePower = 0;
    float frequency = 0;
    float powerFactor = 0;
    float activeEnergyWh = 0;
};

PendingReading pendingReading;

String authorizationHeader()
{
    return "Device " + getPublicId() + ":" + getDeviceSecret();
}

void syncTimeIfNeeded()
{
    if (timeSynced || time(nullptr) >= MIN_PLAUSIBLE_EPOCH)
    {
        timeSynced = true;
        return;
    }
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

bool startRequest(HTTPClient& http, const String& path)
{
    String base = getBackendBaseUrl();
    if (base.length() == 0)
    {
        Serial.println("ERROR red: backend_url esta vacio (no se guardo en el aprovisionamiento).");
        return false;
    }

    String url = base + path;
    bool began;
    if (url.startsWith("https://"))
    {
        static WiFiClientSecure secureClient;
        // MVP: sin CA pineada — ver docs/claude/HIL_TEST_PLAN.md y la
        // etapa 15 (reverse proxy/TLS) para el endurecimiento de producción.
        secureClient.setInsecure();
        began = http.begin(secureClient, url);
    }
    else
    {
        began = http.begin(url);
    }
    if (!began)
    {
        Serial.print("ERROR red: no se pudo iniciar el request a ");
        Serial.println(url);
    }
    return began;
}

void applyCommand(JsonObjectConst command)
{
    long commandId = command["id"].as<long>();
    String type = command["type"].as<String>();

    setRelay(type == "SET_RELAY_ON");

    HTTPClient http;
    if (!startRequest(http, "/api/v1/iot/commands/" + String(commandId) + "/ack"))
    {
        return;
    }
    http.addHeader("Authorization", authorizationHeader());
    http.addHeader("Content-Type", "application/json");

    JsonDocument ackBody;
    ackBody["actual_state"] = relayState ? "ON" : "OFF";
    String serialized;
    serializeJson(ackBody, serialized);

    http.POST(serialized);
    http.end();
}

void pollPendingCommands()
{
    HTTPClient http;
    if (!startRequest(http, "/api/v1/iot/commands/pending"))
    {
        return;
    }
    http.addHeader("Authorization", authorizationHeader());

    int statusCode = http.GET();
    if (statusCode == 200)
    {
        JsonDocument doc;
        if (!deserializeJson(doc, http.getString()))
        {
            for (JsonObjectConst command : doc.as<JsonArrayConst>())
            {
                applyCommand(command);
            }
        }
    }
    http.end();
}

void sendHeartbeat()
{
    HTTPClient http;
    if (!startRequest(http, "/api/v1/iot/heartbeat"))
    {
        return;
    }
    http.addHeader("Authorization", authorizationHeader());
    int statusCode = http.POST("");
    Serial.print("Heartbeat enviado, respuesta HTTP: ");
    Serial.println(statusCode);
    http.end();
}

void sendPendingTelemetry()
{
    localSequence++;

    HTTPClient http;
    if (!startRequest(http, "/api/v1/iot/telemetry"))
    {
        return;
    }
    http.addHeader("Authorization", authorizationHeader());
    http.addHeader("Content-Type", "application/json");

    JsonDocument body;
    body["sequence"] = localSequence;
    // Pydantic acepta un epoch Unix directamente; si el NTP todavia no
    // sincronizo, se manda igual (best-effort) para no perder la lectura.
    body["timestamp"] = (uint32_t)time(nullptr);
    body["voltage_v"] = pendingReading.voltage;
    body["current_a"] = pendingReading.current;
    body["power_w"] = pendingReading.activePower;
    // El PZEM reporta energia en Wh; el contrato de telemetria usa kWh.
    body["energy_kwh"] = pendingReading.activeEnergyWh / 1000.0f;
    body["frequency_hz"] = pendingReading.frequency;
    body["power_factor"] = pendingReading.powerFactor;
    body["relay_state"] = relayState ? "ON" : "OFF";

    String serialized;
    serializeJson(body, serialized);

    int statusCode = http.POST(serialized);
    if (statusCode == 200)
    {
        JsonDocument responseDoc;
        if (!deserializeJson(responseDoc, http.getString()) && !responseDoc["command"].isNull())
        {
            applyCommand(responseDoc["command"].as<JsonObjectConst>());
        }
    }
    http.end();

    pendingReading.pending = false;
    lastHeartbeatOrTelemetryAt = millis();
}

}  // namespace

void iotClientBegin()
{
    localSequence = 0;
}

void iotClientLoop()
{
    if (!isNetworkReady() || !hasPublicId() || !hasDeviceCredential())
    {
        return;
    }

    syncTimeIfNeeded();

    if (pendingReading.pending)
    {
        sendPendingTelemetry();
    }

    unsigned long now = millis();

    if (now - lastCommandPollAt >= COMMAND_POLL_INTERVAL_MS)
    {
        lastCommandPollAt = now;
        pollPendingCommands();
    }

    if (now - lastHeartbeatOrTelemetryAt >= HEARTBEAT_INTERVAL_MS)
    {
        sendHeartbeat();
        lastHeartbeatOrTelemetryAt = now;
    }
}

void onPzemReading(float voltage, float current, float activePower,
                    float frequency, float powerFactor, float activeEnergyWh)
{
    // 1. Corte critico LOCAL, inmediato, sin depender de red — nunca se
    // retrasa por el envio de telemetria de abajo.
    bool cutoffTriggered = evaluateLocalCriticalCutoff(current);
    if (cutoffTriggered)
    {
        Serial.println("CORTE CRITICO LOCAL aplicado (independiente del backend).");
    }

    // 2. Guardar la lectura (incluye el estado del rele YA actualizado por
    // el corte local, si aplico) para que iotClientLoop() la reporte en el
    // siguiente ciclo — nunca se hace la llamada HTTP desde este callback.
    pendingReading.voltage = voltage;
    pendingReading.current = current;
    pendingReading.activePower = activePower;
    pendingReading.frequency = frequency;
    pendingReading.powerFactor = powerFactor;
    pendingReading.activeEnergyWh = activeEnergyWh;
    pendingReading.pending = true;
}
