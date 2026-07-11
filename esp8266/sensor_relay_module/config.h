#ifndef CONFIG_H
#define CONFIG_H

// --- Версия прошивки ---
extern const int FIRMWARE_VERSION;

// --- Идентификатор устройства esp8266---
extern const int SENSOR_ID;
extern const int MODUL_ID;

// --- Имя точки доступа (если Wi-Fi не найден) ---
extern const char *nameAP;

// --- Пин датчика DHT22 ---
extern const int DHT_PIN;

// --- Пины реле ---
extern const int RELAY1_PIN;
extern const int RELAY2_PIN;

// --- Логика управления реле ---
extern const bool RELAY_ACTIVE_LOW;

// --- MQTT / сервер ---
extern String serverIP;
extern bool isServerFound;
// extern const int MQTT_PORT;

// --- Интервал отправки данных (миллисекунды) ---
extern const unsigned long SEND_INTERVAL; // 60 секунд

// --- Интервал получения уставок с сервера (миллисекунды) ---
extern const unsigned long SETTINGS_INTERVAL; // 60 секунд

// --- Интервал проверки OTA (миллисекунды) ---
extern const unsigned long OTA_CHECK_INTERVAL; // 10 минут

#endif
