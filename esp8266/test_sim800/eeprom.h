#ifndef EEPROM_H
#define EEPROM_H

#include <Arduino.h>
#include <EEPROM.h>

void savePhoneToEEPROM(String phone);
void loadPhoneFromEEPROM();

void saveStringToEEPROM(int startAddr, String data, int maxLength);
String readStringFromEEPROM(int startAddr, int maxLength);

#endif