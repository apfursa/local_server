#ifndef DHT22_H
#define DHT22_H

#include <Arduino.h>

void dht22_begin();
void dht22_requestData();
bool dht22_isReady();
float dht22_getTemperature();
float dht22_getHumidity();

#endif
