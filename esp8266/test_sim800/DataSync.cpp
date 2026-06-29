#include "DataSync.h"
#include "eeprom.h"
#include "config.h"

String serverPhone = "";

// Синхронизация номера
bool syncServerPhone(String serverPhone) {
  if (serverPhone.length() >= 10 && serverPhone != currentAdminPhone) {
      currentAdminPhone = serverPhone;
      saveStringToEEPROM(0, currentAdminPhone, 15);
  }

  // Логика тревоги — возвращаем флаг, чтобы main.ino принял решение
  return true; 
}