#ifndef CONFIG_H
#define CONFIG_H

// --- Версия прошивки ---
// Увеличивайте при каждом обновлении и загружайте новый .bin на сервер
const int FIRMWARE_VERSION = 1;

// --- Идентификатор устройства ---
const int SENSOR_ID = 39;

// --- Имя точки доступа (если Wi-Fi не найден) ---
const char *nameAP = "SensorModule";

// --- Пин датчика DS18B20 ---
const int DS18B20_PIN = D4;

// --- MQTT / сервер ---
// const char *MQTT_BROKER = "192.168.1.217";
const int   MQTT_PORT   = 1883;

extern String serverIP;        // IP сервера (найденный через UDP)
extern bool isServerFound;     // найден ли сервер

// --- Интервал отправки данных (миллисекунды) ---
const unsigned long SEND_INTERVAL = 60000UL; // 60 секунд

// --- Интервал проверки OTA обновления (миллисекунды) ---
const unsigned long OTA_CHECK_INTERVAL = 600000UL; // 10 минут

#endif
