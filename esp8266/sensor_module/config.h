#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// --- Версия прошивки ---
// Увеличивайте при каждом обновлении и загружайте новый .bin на сервер
extern const int FIRMWARE_VERSION;

// --- Идентификатор устройства ---
extern const int SENSOR_ID;

// --- Имя точки доступа (если Wi-Fi не найден) ---
extern const char *nameAP;

// --- Пин датчика DS18B20 ---
extern const int DS18B20_PIN;

// --- MQTT / сервер ---
// const char *MQTT_BROKER = "192.168.1.217";
// const int MQTT_PORT = 1883;

extern String serverIP;        // IP сервера (найденный через UDP)
extern bool isServerFound;     // найден ли сервер

// --- Интервал отправки данных (миллисекунды) ---
extern const unsigned long SEND_INTERVAL; // 60 секунд

// --- Интервал проверки OTA обновления (миллисекунды) ---
extern const unsigned long OTA_CHECK_INTERVAL; // 10 минут

#endif
