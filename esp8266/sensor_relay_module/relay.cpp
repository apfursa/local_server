#include "relay.h"
#include "config.h"
#include <EEPROM.h>

// EEPROM адреса для хранения уставок
#define EEPROM_R1_MIN 0   // float = 4 байта
#define EEPROM_R1_MAX 4
#define EEPROM_R2_MIN 8
#define EEPROM_R2_MAX 12
#define EEPROM_SIZE   16

static bool relay1State = false;
static bool relay2State = false;

// Уставки реле (загружаются из EEPROM)
static float r1_min = NAN; // реле 1 включается если temp < r1_min
static float r1_max = NAN; // реле 1 выключается если temp > r1_max
static float r2_min = NAN; // реле 2 включается если hum < r2_min
static float r2_max = NAN; // реле 2 выключается если hum > r2_max

// Вспомогательная функция — реальный уровень сигнала для реле
static int _activeLevel()  { return RELAY_ACTIVE_LOW ? LOW  : HIGH; }
static int _inactiveLevel(){ return RELAY_ACTIVE_LOW ? HIGH : LOW;  }

void relay_begin() {
    EEPROM.begin(EEPROM_SIZE);
    pinMode(RELAY1_PIN, OUTPUT);
    pinMode(RELAY2_PIN, OUTPUT);

    // При старте реле выключены
    digitalWrite(RELAY1_PIN, _inactiveLevel());
    digitalWrite(RELAY2_PIN, _inactiveLevel());
    relay1State = false;
    relay2State = false;

    relay_loadSettings();
    Serial.println("[RELAY] Инициализированы");
}

void relay_set(int relayNum, bool state) {
    int pin   = (relayNum == 1) ? RELAY1_PIN : RELAY2_PIN;
    int level = state ? _activeLevel() : _inactiveLevel();
    digitalWrite(pin, level);

    if (relayNum == 1) relay1State = state;
    else               relay2State = state;

    Serial.printf("[RELAY] Реле %d → %s\n", relayNum, state ? "ВКЛ" : "ВЫКЛ");
}

void relay_autoControl(float temp, float hum) {
    // Реле 1 управляется по температуре
    if (!isnan(temp) && !isnan(r1_min) && !isnan(r1_max)) {
        if (!relay1State && temp < r1_min) {
            relay_set(1, true);   // включить если ниже минимума
        } else if (relay1State && temp > r1_max) {
            relay_set(1, false);  // выключить если выше максимума
        }
    }

    // Реле 2 управляется по влажности
    if (!isnan(hum) && !isnan(r2_min) && !isnan(r2_max)) {
        if (!relay2State && hum < r2_min) {
            relay_set(2, true);
        } else if (relay2State && hum > r2_max) {
            relay_set(2, false);
        }
    }
}

bool relay_getState(int relayNum) {
    return (relayNum == 1) ? relay1State : relay2State;
}

void relay_loadSettings() {
    EEPROM.get(EEPROM_R1_MIN, r1_min);
    EEPROM.get(EEPROM_R1_MAX, r1_max);
    EEPROM.get(EEPROM_R2_MIN, r2_min);
    EEPROM.get(EEPROM_R2_MAX, r2_max);

    // Проверка на мусор в EEPROM (первый запуск)
    if (isnan(r1_min)) r1_min = NAN;
    if (isnan(r1_max)) r1_max = NAN;
    if (isnan(r2_min)) r2_min = NAN;
    if (isnan(r2_max)) r2_max = NAN;

    Serial.printf("[RELAY] Уставки из EEPROM: R1[%.1f..%.1f] R2[%.1f..%.1f]\n",
                  r1_min, r1_max, r2_min, r2_max);
}

void relay_saveSettings(float new_r1_min, float new_r1_max,
                        float new_r2_min, float new_r2_max) {
    bool changed = false;

    if (new_r1_min != r1_min) { r1_min = new_r1_min; EEPROM.put(EEPROM_R1_MIN, r1_min); changed = true; }
    if (new_r1_max != r1_max) { r1_max = new_r1_max; EEPROM.put(EEPROM_R1_MAX, r1_max); changed = true; }
    if (new_r2_min != r2_min) { r2_min = new_r2_min; EEPROM.put(EEPROM_R2_MIN, r2_min); changed = true; }
    if (new_r2_max != r2_max) { r2_max = new_r2_max; EEPROM.put(EEPROM_R2_MAX, r2_max); changed = true; }

    if (changed) {
        EEPROM.commit();
        Serial.printf("[RELAY] Уставки сохранены: R1[%.1f..%.1f] R2[%.1f..%.1f]\n",
                      r1_min, r1_max, r2_min, r2_max);
    } else {
        Serial.println("[RELAY] Уставки не изменились, EEPROM не перезаписываем");
    }
}
