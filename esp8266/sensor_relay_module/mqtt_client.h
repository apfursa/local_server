#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <Arduino.h>

void mqtt_begin();
void mqtt_handle();
void mqtt_sendData(float temp, float hum, bool relay1, bool relay2);

#endif
