#include <Arduino.h>
#include <MycilaPZEM.h>

// ============================================================
// ETAPA 12 — CAPA DE RED (agregada; no reemplaza nada de lo de arriba)
// ============================================================
#include "device_storage.h"
#include "iot_client.h"
#include "provisioning.h"

// ============================================================
// CONFIGURACIÓN
// ============================================================

// Definir UART del PZEM
constexpr uint8_t PZEM_TX = D6;
constexpr uint8_t PZEM_RX = D7;

// Utilizar la dirección configurada previamente
constexpr uint8_t PZEM_ADDRESS = 0xF8;

// Definir control del relevador
constexpr uint8_t RELAY_CTRL = D2;

// Crear instancia del PZEM
Mycila::PZEM pzem;


// ============================================================
// VARIABLES DE CONTROL
// ============================================================

// Guardar el estado actual del relevador
bool relayState = false;

// Guardar el instante del último cambio
unsigned long lastRelayChange = 0;

// Definir intervalo de prueba
constexpr unsigned long RELAY_INTERVAL = 10000;


// ============================================================
// CONTROL DEL RELÉ
// ============================================================

void setRelay(bool state)
{
    relayState = state;

    if (state)
    {
        // Activar el transistor para llevar T90 IN a LOW
        digitalWrite(RELAY_CTRL, HIGH);

        Serial.println();
        Serial.println("====================================");
        Serial.println("RELE ON - CARGA ENERGIZADA");
        Serial.println("====================================");
    }
    else
    {
        // Desactivar el transistor
        // El pull-up lleva T90 IN a 5 V
        digitalWrite(RELAY_CTRL, LOW);

        Serial.println();
        Serial.println("====================================");
        Serial.println("RELE OFF - CARGA DESCONECTADA");
        Serial.println("====================================");
    }
}


// ============================================================
// SETUP
// ============================================================

void setup()
{
    // Configurar el relevador inicialmente apagado
    pinMode(RELAY_CTRL, OUTPUT);
    digitalWrite(RELAY_CTRL, LOW);

    Serial.begin(115200);

    delay(1500);

    Serial.println();
    Serial.println("====================================");
    Serial.println(" ETAPA 6.3");
    Serial.println(" PZEM + CONTROL DEL RELE");
    Serial.println("====================================");

    // Procesar eventos enviados por el PZEM
    pzem.setCallback(
        [](const Mycila::PZEM::EventType event,
           const Mycila::PZEM::Data& data)
        {
            if (event == Mycila::PZEM::EventType::EVT_READ)
            {
                Serial.println();
                Serial.println("----- MEDICION PZEM -----");

                Serial.print("Rele: ");
                Serial.println(relayState ? "ON" : "OFF");

                Serial.print("Voltaje: ");
                Serial.print(data.voltage, 1);
                Serial.println(" V");

                Serial.print("Corriente: ");
                Serial.print(data.current, 3);
                Serial.println(" A");

                Serial.print("Potencia: ");
                Serial.print(data.activePower, 1);
                Serial.println(" W");

                Serial.print("Frecuencia: ");
                Serial.print(data.frequency, 1);
                Serial.println(" Hz");

                Serial.print("Factor de potencia: ");
                Serial.println(data.powerFactor, 2);

                Serial.print("Energia acumulada: ");
                Serial.print(data.activeEnergy);
                Serial.println(" Wh");

                Serial.println("-------------------------");

                // Etapa 12: corte critico local + reporte al backend.
                // Se engancha aqui, no reemplaza nada de lo de arriba.
                onPzemReading(
                    data.voltage, data.current, data.activePower,
                    data.frequency, data.powerFactor, data.activeEnergy
                );
            }
            else if (event == Mycila::PZEM::EventType::EVT_READ_ERROR)
            {
                Serial.println("ERROR: respuesta incorrecta del PZEM");
            }
            else if (event == Mycila::PZEM::EventType::EVT_READ_TIMEOUT)
            {
                Serial.println("ERROR: el PZEM no responde");
            }
        }
    );

    // Inicializar comunicación UART con el PZEM
    pzem.begin(
        Serial1,
        PZEM_RX,
        PZEM_TX,
        PZEM_ADDRESS,
        true
    );

    // Mantener inicialmente la carga apagada
    setRelay(false);

    lastRelayChange = millis();

    // ============================================================
    // ETAPA 12 — inicialización de la capa de red (agregada)
    // ============================================================
    deviceStorageBegin();
    provisioningBegin();
    iotClientBegin();
}


// ============================================================
// LOOP
// ============================================================

void loop()
{
    // Etapa 12: reemplaza el bloque de demostracion (alternar el rele cada
    // 10s) por la orquestacion real de aprovisionamiento/red. La lectura
    // del PZEM y el corte critico local NO dependen de este loop — ya
    // corrieron de forma sincrona dentro del callback (ver arriba).
    provisioningLoop();
    iotClientLoop();

    // Evitar bloquear completamente el loop (tambien alimenta el watchdog)
    delay(10);
}