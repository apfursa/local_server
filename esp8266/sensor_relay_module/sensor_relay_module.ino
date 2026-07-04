#include "config.h"
#include "wifi_manager.h"
#include "udp.h"
#include "ota.h"
#include "mqtt_client.h"
#include "dht22.h"
#include "relay.h"
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <ESP8266WiFi.h>

// --- Глобальные переменные (объявлены здесь, extern в config.h) ---
String serverIP = "";
bool isServerFound = false;
const char *nameAP = "RelayModule";

// --- Состояния автомата ---
enum State {
    STATE_FIND_SERVER,    // Ищем сервер по UDP
    STATE_OTA_CHECK,      // Проверяем обновление прошивки
    STATE_REQUEST_DATA,   // Запрашиваем данные с DHT22
    STATE_WAIT_DATA,      // Ждём готовности DHT22 (~2 сек)
    STATE_RELAY_CONTROL,  // Управляем реле по уставкам
    STATE_SEND,           // Отправляем данные на сервер по MQTT
    STATE_GET_SETTINGS,   // Получаем уставки с сервера (HTTP GET)
    STATE_IDLE            // Ждём следующего интервала
};

State globalState = STATE_FIND_SERVER;
unsigned long idleStartTime       = 0;
unsigned long otaLastCheckTime    = 0;
unsigned long settingsLastTime    = 0;
float lastTemp = NAN;
float lastHum  = NAN;




// --- Получение уставок с сервера ---
void fetchSettings() {
    if (WiFi.status() != WL_CONNECTED || !isServerFound) return;

    WiFiClient client;
    HTTPClient http;

    // Уставки для температуры (реле 1)
    String url1 = "http://" + serverIP + "/api/settings/" + String(SENSOR_ID) + "?type=temp1";
    http.begin(client, url1);
    http.setTimeout(5000);
    int code = http.GET();

    float r1_min = NAN, r1_max = NAN, r2_min = NAN, r2_max = NAN;

    if (code == 200) {
        JsonDocument doc;
        if (!deserializeJson(doc, http.getString())) {
            String rm = doc["relay_min"].as<String>();
            String rx = doc["relay_max"].as<String>();
            if (rm != "null" && rm != "") r1_min = rm.toFloat();
            if (rx != "null" && rx != "") r1_max = rx.toFloat();
        }
    }
    http.end();

    // Уставки для влажности (реле 2)
    String url2 = "http://" + serverIP + "/api/settings/" + String(SENSOR_ID) + "?type=hum";
    http.begin(client, url2);
    http.setTimeout(5000);
    code = http.GET();

    if (code == 200) {
        JsonDocument doc;
        if (!deserializeJson(doc, http.getString())) {
            String rm = doc["relay_min"].as<String>();
            String rx = doc["relay_max"].as<String>();
            if (rm != "null" && rm != "") r2_min = rm.toFloat();
            if (rx != "null" && rx != "") r2_max = rx.toFloat();
        }
    }
    http.end();

    // Сохраняем в EEPROM только если изменились
    relay_saveSettings(r1_min, r1_max, r2_min, r2_max);
}

void setup() {
    Serial.begin(115200);
    Serial.println(">>> Запуск модуля реле + DHT22...");
    Serial.printf(">>> Версия прошивки: %d\n", FIRMWARE_VERSION);

    setupWiFi();
    udp.begin(8888);
    relay_begin();
    dht22_begin();
    mqtt_begin();

    Serial.println(">>> Система инициализирована");
}

void loop() {
    mqtt_handle();

    switch (globalState) {

        case STATE_FIND_SERVER:
            get_server_IP();
            if (isServerFound) {
                globalState = STATE_OTA_CHECK;
            }
            break;

        case STATE_OTA_CHECK:
            Serial.println("[LOOP] Проверка OTA...");
            ota_check_and_update();
            otaLastCheckTime = millis();
            globalState = STATE_REQUEST_DATA;
            break;

        case STATE_REQUEST_DATA:
            dht22_requestData();
            globalState = STATE_WAIT_DATA;
            break;

        case STATE_WAIT_DATA:
            if (dht22_isReady()) {
                lastTemp = dht22_getTemperature();
                lastHum  = dht22_getHumidity();
                globalState = STATE_RELAY_CONTROL;
            }
            break;

        case STATE_RELAY_CONTROL:
            relay_autoControl(lastTemp, lastHum);
            globalState = STATE_SEND;
            break;

        case STATE_SEND:
            if (!isnan(lastTemp) && !isnan(lastHum)) {
                mqtt_sendData(lastTemp, lastHum,
                              relay_getState(1), relay_getState(2));
            } else {
                Serial.println("[LOOP] Датчик недоступен, пропускаем отправку");
            }
            idleStartTime = millis();
            globalState = STATE_GET_SETTINGS;
            break;

        case STATE_GET_SETTINGS:
            // Получаем уставки раз в SETTINGS_INTERVAL
            if (millis() - settingsLastTime >= SETTINGS_INTERVAL) {
                Serial.println("[LOOP] Получение уставок с сервера...");
                fetchSettings();
                settingsLastTime = millis();
            }
            globalState = STATE_IDLE;
            break;

        case STATE_IDLE:
            if (millis() - otaLastCheckTime >= OTA_CHECK_INTERVAL) {
                globalState = STATE_OTA_CHECK;
                break;
            }
            if (millis() - idleStartTime >= SEND_INTERVAL) {
                globalState = STATE_REQUEST_DATA;
            }
            break;
    }
}
