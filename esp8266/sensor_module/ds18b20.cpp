#include "ds18b20.h"
#include "config.h"
#include <OneWire.h>
#include <DallasTemperature.h>

static OneWire oneWire(DS18B20_PIN);
static DallasTemperature sensors(&oneWire);
static unsigned long requestTime = 0;
static bool requestPending = false;

void ds18b20_begin() {
    sensors.begin();
    sensors.setWaitForConversion(false); // Неблокирующий режим
    Serial.println("[DS18B20] Инициализирован");
    Serial.printf("[DS18B20] Найдено датчиков: %d\n", sensors.getDeviceCount());
}

void ds18b20_requestTemperature() {
    sensors.requestTemperatures();
    requestTime = millis();
    requestPending = true;
}

bool ds18b20_isReady() {
    // DS18B20 при 12-битном разрешении требует 750мс на измерение
    return requestPending && (millis() - requestTime >= 750);
}

float ds18b20_getTemperature() {
    if (!requestPending) return -127.0;
    requestPending = false;
    float temp = sensors.getTempCByIndex(0);
    if (temp == DEVICE_DISCONNECTED_C) {
        Serial.println("[DS18B20] Датчик не найден!");
        return -127.0;
    }
    return temp;
}
