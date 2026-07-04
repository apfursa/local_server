#ifndef CONFIG_H
#define CONFIG_H

// --- Версия прошивки ---
const int FIRMWARE_VERSION = 2;

// --- Идентификатор устройства ---
const int SENSOR_ID = 50;

// --- Имя точки доступа (если Wi-Fi не найден) ---
extern const char *nameAP;

// --- Пин датчика DHT22 ---
const int DHT_PIN = D4;

// --- Пины реле ---
const int RELAY1_PIN = D1;
const int RELAY2_PIN = D2;

// --- Логика управления реле ---
// true  = реле срабатывает от LOW (большинство модулей реле)
// false = реле срабатывает от HIGH
const bool RELAY_ACTIVE_LOW = true;

// --- MQTT / сервер ---
extern String serverIP;
extern bool isServerFound;
const int MQTT_PORT = 1883;

// --- Интервал отправки данных (миллисекунды) ---
const unsigned long SEND_INTERVAL = 60000UL; // 60 секунд

// --- Интервал получения уставок с сервера (миллисекунды) ---
const unsigned long SETTINGS_INTERVAL = 60000UL; // 60 секунд

// --- Интервал проверки OTA (миллисекунды) ---
const unsigned long OTA_CHECK_INTERVAL = 600000UL; // 10 минут

#endif
