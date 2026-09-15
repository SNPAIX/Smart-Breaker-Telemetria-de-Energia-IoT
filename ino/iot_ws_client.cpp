#include "iot_ws_client.h"

#include <ArduinoJson.h>
#include <WebSocketsClient.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "device_storage.h"
#include "iot_client.h"
#include "provisioning.h"

namespace {

// Reintenta solo cada 5s — evita machacar al backend si las credenciales
// son inválidas o el servidor está caído, y le da tiempo de sobra a una
// reconexión de WiFi de por medio a resolverse primero.
constexpr unsigned long WS_RECONNECT_INTERVAL_MS = 5000;

// El intento de reconexión de esta librería es BLOQUEANTE (hasta 5s por
// intento, ver WEBSOCKETS_TCP_TIMEOUT en su código fuente) — corre en su
// propia tarea, nunca en el loop() principal, para que un intento colgado
// no frene también el poll HTTP de respaldo de iot_client.cpp (bug real
// encontrado 15-sep: comandos tardando hasta 30s porque loop() entero
// quedaba bloqueado esperando a esta librería reconectar).
constexpr uint32_t WS_TASK_STACK_SIZE = 6144;
constexpr UBaseType_t WS_TASK_PRIORITY = 1;

WebSocketsClient webSocket;
String configuredBaseUrl;

// Separa "http(s)://host[:puerto]" en sus partes — WebSocketsClient pide
// host y puerto por separado, no una URL completa como HTTPClient.
bool parseBaseUrl(const String& baseUrl, bool& useSsl, String& host, uint16_t& port)
{
    String rest = baseUrl;
    if (rest.startsWith("https://"))
    {
        useSsl = true;
        rest = rest.substring(8);
        port = 443;
    }
    else if (rest.startsWith("http://"))
    {
        useSsl = false;
        rest = rest.substring(7);
        port = 80;
    }
    else
    {
        return false;
    }

    // backend_url no debería traer un path (ver formulario de
    // aprovisionamiento), pero se recorta por las dudas para no mandarlo
    // como si fuera parte del host.
    int slashIndex = rest.indexOf('/');
    if (slashIndex >= 0)
    {
        rest = rest.substring(0, slashIndex);
    }

    int colonIndex = rest.lastIndexOf(':');
    if (colonIndex > 0)
    {
        String portStr = rest.substring(colonIndex + 1);
        long parsedPort = portStr.toInt();
        if (parsedPort <= 0 || parsedPort > 65535)
        {
            return false;
        }
        port = static_cast<uint16_t>(parsedPort);
        host = rest.substring(0, colonIndex);
    }
    else
    {
        host = rest;
    }

    return host.length() > 0;
}

void onWsEvent(WStype_t type, uint8_t* payload, size_t length)
{
    switch (type)
    {
        case WStype_CONNECTED:
            Serial.println("WS comandos: conectado — entrega en tiempo real activa.");
            break;

        case WStype_DISCONNECTED:
            // No es un error a gritar en el log: el poll de respaldo de
            // iot_client.cpp sigue entregando comandos igual mientras el
            // socket esta caido — y ahora que esta tarea es independiente,
            // ese poll ya no se frena mientras se reintenta la conexion.
            Serial.println("WS comandos: desconectado, reintentando en background (el poll de respaldo sigue activo).");
            break;

        case WStype_TEXT:
        {
            // Un mensaje malformado o de un tipo desconocido se ignora
            // sin más — nunca debe tirar el firmware por un dato que no
            // se pudo interpretar.
            JsonDocument doc;
            DeserializationError parseError = deserializeJson(doc, payload, length);
            if (parseError)
            {
                Serial.print("WS comandos: mensaje no se pudo parsear (");
                Serial.print(parseError.c_str());
                Serial.println("), se ignora.");
                return;
            }

            const char* messageType = doc["type"] | "";
            if (String(messageType) == "command" && !doc["command"].isNull())
            {
                applyPushedCommand(doc["command"].as<JsonObjectConst>());
            }
            break;
        }

        default:
            break;
    }
}

void wsTask(void*)
{
    for (;;)
    {
        if (isNetworkReady() && hasPublicId() && hasDeviceCredential())
        {
            String baseUrl = getBackendBaseUrl();
            if (baseUrl.length() > 0 && baseUrl != configuredBaseUrl)
            {
                bool useSsl = false;
                String host;
                uint16_t port = 0;
                if (parseBaseUrl(baseUrl, useSsl, host, port))
                {
                    // Mismo esquema "Device <public_id>:<secreto>" que ya
                    // usa cada request HTTP — nunca se imprime el secreto
                    // al log, igual criterio que el resto del firmware.
                    String auth = "Authorization: Device " + getPublicId() + ":" + getDeviceSecret();
                    webSocket.setExtraHeaders(auth.c_str());

                    if (useSsl)
                    {
                        // MVP: sin CA pineada, mismo nivel de confianza
                        // que ya usa startRequest() en iot_client.cpp
                        // para HTTPS (ver roadmap/PROGRESS.md, pendiente
                        // de etapa 15 con la CA local de Caddy).
                        webSocket.beginSSL(host.c_str(), port, "/api/v1/iot/ws");
                    }
                    else
                    {
                        webSocket.begin(host.c_str(), port, "/api/v1/iot/ws");
                    }
                    configuredBaseUrl = baseUrl;
                }
                else
                {
                    Serial.println("WS comandos: backend_url no se pudo interpretar, se omite este canal (el poll de respaldo sigue activo).");
                }
            }

            webSocket.loop();
        }

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

}  // namespace

void iotWsClientBegin()
{
    webSocket.onEvent(onWsEvent);
    webSocket.setReconnectInterval(WS_RECONNECT_INTERVAL_MS);
    xTaskCreate(wsTask, "iotWsTask", WS_TASK_STACK_SIZE, nullptr, WS_TASK_PRIORITY, nullptr);
}

void iotWsClientLoop()
{
    // Intencionalmente vacío: la conexión vive por completo en su propia
    // tarea (wsTask, creada en iotWsClientBegin()) para que un intento de
    // reconexión bloqueante nunca frene el loop() principal ni, con él,
    // el poll HTTP de respaldo. Se conserva la función (llamada desde
    // code.ino) para no tener que tocar ese enganche si el día de mañana
    // hace falta alguna sincronización puntual desde el loop principal.
}
