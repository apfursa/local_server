#include "eeprom.h"
 
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

// Сохранение любой строки в EEPROM
void saveStringToEEPROM(int startAddr, String data, int maxLen) {
    data.trim();
    // Пишем байты
    for (int i = 0; i < maxLen; ++i) {
        if (i < data.length()) {
            EEPROM.write(startAddr + i, data[i]);
        } else {
            EEPROM.write(startAddr + i, 0); // Забиваем нулями остаток
            break; // Экономим циклы
        }
    }
    EEPROM.commit();
}

// Чтение любой строки из EEPROM
String readStringFromEEPROM(int startAddr, int maxLen) {
    String data = "";
    for (int i = 0; i < maxLen; ++i) {
        char c = (char)EEPROM.read(startAddr + i);
        if (c == 0 || c == 255) break;
        data += c;
    }
    return data;
}

void saveIntToEEPROM(int addr, int value) {
    EEPROM.put(addr, value);
    EEPROM.commit();
}

int readIntFromEEPROM(int addr) {
    int value;
    EEPROM.get(addr, value);
    return value;
}