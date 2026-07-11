#include "config.h"
#include "wifi_manager.h"
#include "udp.h"
#include "ota.h"
#include "http_client.h"
#include "dht22.h"
#include "relay.h"
// #include <ESP8266HTTPClient.h> // для fetchSettings()
#include <ESP8266WiFi.h>
#include <ArduinoJson.h>

// --- Глобальные переменные ---
const char *nameAP = "SensorRelayModule";
String serverIP    = "";
bool isServerFound = false;

// --- Идентификатор устройства esp8266---
const int SENSOR_ID = 106;

const int MODUL_ID = SENSOR_ID;

// --- Версия прошивки ---
const int FIRMWARE_VERSION = 2;

// --- Пин датчика DHT22 ---
const int DHT_PIN = D4;

// --- Пины реле ---
const int RELAY1_PIN = D1;
const int RELAY2_PIN = D2;

// --- Логика управления реле ---
// true  = реле срабатывает от LOW (большинство модулей реле)
// false = реле срабатывает от HIGH
const bool RELAY_ACTIVE_LOW = true;

// --- Интервал отправки данных (миллисекунды) ---
const unsigned long SEND_INTERVAL = 60000UL; // 60 секунд

// --- Интервал получения уставок с сервера (миллисекунды) ---
const unsigned long SETTINGS_INTERVAL = 60000UL; // 60 секунд

// --- Интервал проверки OTA (миллисекунды) ---
const unsigned long OTA_CHECK_INTERVAL = 600000UL; // 10 минут

// --- Структура реле ---
struct RelayState {
    String pin;
    int    state;
    int    pin_num;
};

// Чтобы добавить третье реле — добавьте строку {"D5", 0, D5}
RelayState relays[] = {
    {"D1", 0, RELAY1_PIN},
    {"D2", 0, RELAY2_PIN}
};
const int RELAY_COUNT = sizeof(relays) / sizeof(relays[0]);

// --- Состояния автомата ---
enum State {
    STATE_FIND_SERVER,
    STATE_OTA_CHECK,
    STATE_REQUEST_DATA,   // Запрос данных с DHT22
    STATE_WAIT_DATA,      // Ожидание DHT22
    // STATE_RELAY_CONTROL,  // Локальное управление реле по уставкам EEPROM
    STATE_SEND,           // Отправка данных на сервер
    STATE_CHECK_RELAYS,   // Опрос сервера для каждого реле
    // STATE_GET_SETTINGS,   // Получение уставок с сервера
    STATE_IDLE
};

State globalState        = STATE_FIND_SERVER;
unsigned long idleStart  = 0;
unsigned long otaLastCheck   = 0;
// unsigned long settingsLastTime = 0;
float lastTemp = NAN;
float lastHum  = NAN;
int currentRelayIndex    = 0;

// --- Управление реле ---
void setRelay(int index, int state) {
    int level = (RELAY_ACTIVE_LOW) ? (state ? LOW : HIGH)
                                   : (state ? HIGH : LOW);
    digitalWrite(relays[index].pin_num, level);
    relays[index].state = state;
    Serial.printf("[RELAY] %s → %s\n",
                  relays[index].pin.c_str(), state ? "ВКЛ" : "ВЫКЛ");
}

// --- Получение уставок с сервера ---
// void fetchSettings() {
//     if (WiFi.status() != WL_CONNECTED || !isServerFound) return;

//     WiFiClient client;
//     HTTPClient http;

//     float r1_min = NAN, r1_max = NAN, r2_min = NAN, r2_max = NAN;

//     // Уставки для температуры (реле 1)
//     String url1 = "http://" + serverIP + "/api/settings/" + String(SENSOR_ID) + "?type=temp1";
//     http.begin(client, url1);
//     http.setTimeout(5000);
//     if (http.GET() == 200) {
//         JsonDocument doc;
//         if (!deserializeJson(doc, http.getString())) {
//             String rm = doc["relay_min"].as<String>();
//             String rx = doc["relay_max"].as<String>();
//             if (rm != "null" && rm != "") r1_min = rm.toFloat();
//             if (rx != "null" && rx != "") r1_max = rx.toFloat();
//         }
//     }
//     http.end();

//     // Уставки для влажности (реле 2)
//     String url2 = "http://" + serverIP + "/api/settings/" + String(SENSOR_ID) + "?type=hum";
//     http.begin(client, url2);
//     http.setTimeout(5000);
//     if (http.GET() == 200) {
//         JsonDocument doc;
//         if (!deserializeJson(doc, http.getString())) {
//             String rm = doc["relay_min"].as<String>();
//             String rx = doc["relay_max"].as<String>();
//             if (rm != "null" && rm != "") r2_min = rm.toFloat();
//             if (rx != "null" && rx != "") r2_max = rx.toFloat();
//         }
//     }
//     http.end();

//     relay_saveSettings(r1_min, r1_max, r2_min, r2_max);
// }

void setup() {
    Serial.begin(115200);
    Serial.println(">>> Запуск модуля датчик+реле...");
    Serial.printf(">>> Версия прошивки: %d\n", FIRMWARE_VERSION);

    // Инициализация пинов реле
    for (int i = 0; i < RELAY_COUNT; i++) {
        pinMode(relays[i].pin_num, OUTPUT);
        setRelay(i, 0);
    }

    setupWiFi();
    udp.begin(8888);
    http_begin();
    relay_begin();
    dht22_begin();

    Serial.println(">>> Система инициализирована");
}

void loop() {
    http_handle();

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
            otaLastCheck = millis();
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
                globalState = STATE_SEND;  // ← было STATE_RELAY_CONTROL
            }
            break;

        // case STATE_RELAY_CONTROL:
        //     // Локальное управление реле по уставкам из EEPROM
        //     relay_autoControl(lastTemp, lastHum);
        //     // Синхронизируем локальное состояние в массив relays[]
        //     relays[0].state = relay_getState(1) ? 1 : 0;
        //     relays[1].state = relay_getState(2) ? 1 : 0;
        //     globalState = STATE_SEND;
        //     break;

        case STATE_SEND:
            if (!isnan(lastTemp) && !isnan(lastHum)) {
                http_sendSensorRelayData(
                    lastTemp, lastHum,
                    relays[0].state, relays[1].state
                );
            } else {
                Serial.println("[LOOP] Датчик недоступен, пропускаем отправку");
            }
            currentRelayIndex = 0;
            globalState = STATE_CHECK_RELAYS;
            break;

        case STATE_CHECK_RELAYS:
            // Опрашиваем реле по одному — сервер может скорректировать состояние
            if (currentRelayIndex < RELAY_COUNT) {
                int new_state = http_sendRelayData(
                    relays[currentRelayIndex].pin,
                    relays[currentRelayIndex].state
                );
                if (new_state >= 0 && new_state != relays[currentRelayIndex].state) {
                    setRelay(currentRelayIndex, new_state);
                }
                currentRelayIndex++;
            } else {
                idleStart = millis();        // ← добавьте
                globalState = STATE_IDLE;   // ← было STATE_GET_SETTINGS
            }
            break;

        // case STATE_GET_SETTINGS:
        //     if (millis() - settingsLastTime >= SETTINGS_INTERVAL) {
        //         Serial.println("[LOOP] Получение уставок с сервера...");
        //         fetchSettings();
        //         settingsLastTime = millis();
        //     }
        //     idleStart = millis();
        //     globalState = STATE_IDLE;
        //     break;

        case STATE_IDLE:
            if (millis() - otaLastCheck >= OTA_CHECK_INTERVAL) {
                globalState = STATE_OTA_CHECK;
                break;
            }
            if (millis() - idleStart >= SEND_INTERVAL) {
                globalState = STATE_REQUEST_DATA;
            }
            break;
    }
}
