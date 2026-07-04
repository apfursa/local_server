#include "dht22.h"
#include "config.h"
#include <DHT.h>

static DHT dht(DHT_PIN, DHT22);
static unsigned long requestTime = 0;
static bool requestPending = false;
static float lastTemp = NAN;
static float lastHum  = NAN;

void dht22_begin() {
    dht.begin();
    Serial.println("[DHT22] Инициализирован");
}

void dht22_requestData() {
    requestTime = millis();
    requestPending = true;
}

bool dht22_isReady() {
    // DHT22 требует минимум 2 секунды между измерениями
    return requestPending && (millis() - requestTime >= 2000);
}

float dht22_getTemperature() {
    if (!requestPending) return NAN;
    lastTemp = dht.readTemperature();
    lastHum  = dht.readHumidity();
    requestPending = false;

    if (isnan(lastTemp)) {
        Serial.println("[DHT22] Ошибка чтения температуры!");
    } else {
        Serial.printf("[DHT22] Температура: %.1f°C, Влажность: %.1f%%\n", lastTemp, lastHum);
    }
    return lastTemp;
}

float dht22_getHumidity() {
    return lastHum;
}
