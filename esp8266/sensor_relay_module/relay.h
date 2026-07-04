#ifndef RELAY_H
#define RELAY_H

#include <Arduino.h>

// Инициализация реле
void relay_begin();

// Управление реле вручную
void relay_set(int relayNum, bool state); // relayNum: 1 или 2, state: true=вкл, false=выкл

// Автоматическое управление по уставкам из EEPROM
// Вызывать после получения новых данных с датчиков
void relay_autoControl(float temp, float hum);

// Получить текущее состояние реле (true=вкл, false=выкл)
bool relay_getState(int relayNum);

// Загрузить уставки из EEPROM
void relay_loadSettings();

// Сохранить уставки в EEPROM
void relay_saveSettings(
    float r1_min, float r1_max,  // уставки реле 1 (по температуре)
    float r2_min, float r2_max   // уставки реле 2 (по влажности)
);

#endif
