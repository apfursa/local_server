#include "ota.h"
#include "config.h"
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266httpUpdate.h>
#include <ArduinoJson.h>

bool ota_check_and_update() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[OTA] Wi-Fi не подключен, пропускаем проверку");
        return false;
    }

    // Формируем URL и тело запроса
    String url = "http://";
    url += serverIP; // используем тот же IP что и для MQTT
    url += "/api/ota/check";

    String body = "{\"sensor_id\":" + String(SENSOR_ID) +
                  ",\"version\":" + String(FIRMWARE_VERSION) + "}";

    Serial.printf("[OTA] Проверка обновления: sensor_id=%d, version=%d\n",
                  SENSOR_ID, FIRMWARE_VERSION);

    WiFiClient client;
    HTTPClient http;
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);

    int code = http.POST(body);

    if (code != 200) {
        Serial.printf("[OTA] Ошибка запроса: %d\n", code);
        http.end();
        return false;
    }

    String response = http.getString();
    http.end();

    Serial.printf("[OTA] Ответ сервера: %s\n", response.c_str());

    // Парсим JSON ответ
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, response);
    if (error) {
        Serial.println("[OTA] Ошибка парсинга ответа");
        return false;
    }

    bool needUpdate = doc["update"].as<bool>();
    if (!needUpdate) {
        Serial.println("[OTA] Прошивка актуальна, обновление не требуется");
        return false;
    }

    // Есть обновление — скачиваем и прошиваем
    String firmwareUrl = doc["url"].as<String>();
    int newVersion = doc["version"].as<int>();

    Serial.printf("[OTA] Доступна новая версия v%d, скачиваем: %s\n",
                  newVersion, firmwareUrl.c_str());

    WiFiClient updateClient;
    ESPhttpUpdate.setLedPin(LED_BUILTIN, LOW); // мигаем встроенным светодиодом при обновлении
    ESPhttpUpdate.rebootOnUpdate(true);         // перезагружаемся автоматически после обновления

    t_httpUpdate_return ret = ESPhttpUpdate.update(updateClient, firmwareUrl);

    switch (ret) {
        case HTTP_UPDATE_FAILED:
            Serial.printf("[OTA] Ошибка обновления: %s\n",
                          ESPhttpUpdate.getLastErrorString().c_str());
            return false;

        case HTTP_UPDATE_NO_UPDATES:
            Serial.println("[OTA] Сервер говорит нет обновлений (неожиданно)");
            return false;

        case HTTP_UPDATE_OK:
            Serial.println("[OTA] Обновление успешно! Перезагрузка...");
            return true; // ESP перезагрузится сама через rebootOnUpdate
    }

    return false;
}
