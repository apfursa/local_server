#include "mqtt_client.h"
#include "config.h"
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

static WiFiClient wifiClient;
static PubSubClient mqttClient(wifiClient);

static void reconnect() {
    int attempts = 0;
    while (!mqttClient.connected() && attempts < 5) {
        attempts++;
        Serial.printf("[MQTT] Подключение к %s:%d (попытка %d)...\n",
                      serverIP, MQTT_PORT, attempts);

        String clientId = "ESP8266-" + String(SENSOR_ID);
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("[MQTT] Подключено!");
        } else {
            Serial.printf("[MQTT] Ошибка: %d, повтор через 3 сек...\n",
                          mqttClient.state());
            delay(3000);
        }
    }
}

void mqtt_begin() {
    mqttClient.setServer(serverIP, MQTT_PORT);
    Serial.println("[MQTT] Инициализирован");
}

void mqtt_handle() {
    if (!mqttClient.connected()) {
        reconnect();
    }
    mqttClient.loop();
}

void mqtt_sendTemperature(float temp) {
    if (!mqttClient.connected()) {
        Serial.println("[MQTT] Нет соединения, отправка невозможна");
        return;
    }

    // Формируем топик: sensors/39
    String topic = "sensors/" + String(SENSOR_ID);

    // Формируем payload: {"temp1": 23.5}
    String payload = "{\"temp1\":" + String(temp, 1) + "}";

    bool ok = mqttClient.publish(topic.c_str(), payload.c_str());
    if (ok) {
        Serial.printf("[MQTT] Отправлено на %s: %s\n",
                      topic.c_str(), payload.c_str());
    } else {
        Serial.println("[MQTT] Ошибка отправки!");
    }
}
