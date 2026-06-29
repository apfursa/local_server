#ifndef EEPROM_H
#define EEPROM_H
#include <Arduino.h>
#include <EEPROM.h>

void savePhoneToEEPROM(String phone);
void loadPhoneFromEEPROM();

#endif