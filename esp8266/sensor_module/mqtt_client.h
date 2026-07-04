#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <Arduino.h>

// Инициализация MQTT
void mqtt_begin();

// Поддержание соединения (вызывать в loop())
void mqtt_handle();

// Отправка температуры на сервер
void mqtt_sendTemperature(float temp);

#endif
