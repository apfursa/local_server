#include "config.h"
#include "wifi_manager.h"
#include "ds18b20.h"
#include "mqtt_client.h"
#include "ota.h"

// Состояния главного автомата
enum State {
    STATE_FIND_SERVER,
    STATE_OTA_CHECK,     // Проверить наличие обновления
    STATE_REQUEST_TEMP,  // Запросить измерение у датчика
    STATE_WAIT_TEMP,     // Ждать готовности результата (~750мс)
    STATE_SEND,          // Отправить данные на сервер
    STATE_IDLE           // Ждать следующего интервала отправки
};

State globalState = STATE_FIND_SERVER; 
unsigned long idleStartTime = 0;
unsigned long otaLastCheckTime = 0;
float lastTemperature = -127.0;

void setup() {
    Serial.begin(115200);
    Serial.println(">>> Запуск модуля датчика...");
    Serial.printf(">>> Версия прошивки: %d\n", FIRMWARE_VERSION);

    setupWiFi();
    mqtt_begin();
    ds18b20_begin();

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
            Serial.println("[LOOP] Проверка OTA обновления...");
            ota_check_and_update(); // если обновление есть — ESP перезагрузится сама
            otaLastCheckTime = millis();
            globalState = STATE_REQUEST_TEMP;
            break;

        case STATE_REQUEST_TEMP:
            Serial.println("[LOOP] Запрос температуры...");
            ds18b20_requestTemperature();
            globalState = STATE_WAIT_TEMP;
            break;

        case STATE_WAIT_TEMP:
            if (ds18b20_isReady()) {
                lastTemperature = ds18b20_getTemperature();
                Serial.printf("[LOOP] Температура: %.1f°C\n", lastTemperature);
                globalState = STATE_SEND;
            }
            break;

        case STATE_SEND:
            if (lastTemperature != -127.0) {
                mqtt_sendTemperature(lastTemperature);
            } else {
                Serial.println("[LOOP] Датчик недоступен, пропускаем отправку");
            }
            idleStartTime = millis();
            globalState = STATE_IDLE;
            break;

        case STATE_IDLE:
            if (millis() - otaLastCheckTime >= OTA_CHECK_INTERVAL) {
                globalState = STATE_OTA_CHECK;
                break;
            }
            if (millis() - idleStartTime >= SEND_INTERVAL) {
                globalState = STATE_REQUEST_TEMP;
            }
            break;
    }
}
