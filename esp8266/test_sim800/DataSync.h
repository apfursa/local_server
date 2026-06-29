#ifndef DATA_SYNC_H
#define DATA_SYNC_H

#include <Arduino.h>

extern String serverPhone;

// Функция возвращает true, если синхронизация прошла успешно
bool syncServerPhone(String serverPhone);

#endif