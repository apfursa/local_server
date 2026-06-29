#include "eeprom.h"
#include <EEPROM.h>
#include "config.h"

void savePhoneToEEPROM(String phone) {
  phone.trim();
  String savedPhone = "";
  for (int i = 0; i < 15; ++i) {
    char c = EEPROM.read(i);
    if (c == 0 || c == 255) break;
    savedPhone += c;
  }
  
  if (savedPhone == phone) {
    Serial.println("[EEPROM] Номер не изменился. Запись пропущена.");
    return;
  }

  Serial.println("[EEPROM] Обнаружен новый номер! Записываем в память...");
  for (int i = 0; i < 15; ++i) {
    if (i < phone.length()) {
      EEPROM.write(i, phone[i]);
    } else {
      EEPROM.write(i, 0); 
    }
  }
  EEPROM.commit(); 
  Serial.println("[EEPROM] Номер успешно обновлен.");
}

void loadPhoneFromEEPROM() {
  String savedPhone = "";
  for (int i = 0; i < 15; ++i) {
    char c = EEPROM.read(i);
    if (c == 0 || c == 255) break; 
    savedPhone += c;
  }
  savedPhone.trim();
  
  if (savedPhone.length() >= 10 && savedPhone.startsWith("+")) {
    currentAdminPhone = savedPhone;
    Serial.print("[EEPROM] Номер администратора успешно загружен: ");
    Serial.println(currentAdminPhone);
  } else {
    currentAdminPhone = ""; // Гарантируем пустоту, если там мусор
    Serial.println("[EEPROM] Память пуста или содержит некорректный номер.");
  }
}