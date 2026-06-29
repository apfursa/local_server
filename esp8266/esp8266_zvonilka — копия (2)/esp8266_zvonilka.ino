#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266HTTPClient.h>
#include <WiFiManager.h>
#include <SoftwareSerial.h>
#include <EEPROM.h>
#include <ArduinoJson.h>

SoftwareSerial simSerial(D1, D2);
const char *serverHost = "192.168.1.205";
const char *nameAP = "BorisPhone_34";

String currentAdminPhone = "";
unsigned long muteUntilAll = 0; // Время окончания режима тишины

// --- Контроль ---
unsigned long wifiDisconnectStartTime = 0;
unsigned long powerLossStartTime = 0; // время начала потери питания

int serverErrorCounter = 0;                            // Счетчик ошибок сервера подряд
const int MAX_SERVER_ERRORS = 3;                       // Максимум ошибок до звонка

bool waitForResponse(const char* expected, unsigned long timeoutMs = 2000) {
  unsigned long start = millis();
  String buffer = "";
  while (millis() - start < timeoutMs) {
    while (simSerial.available()) {
      char c = simSerial.read();
      Serial.print(c); 
      buffer += c;
      if (buffer.indexOf(expected) != -1) return true;
    }
    yield();
  }
  return false;
}

void makeGSMCall() {
  if (currentAdminPhone.length() < 10) return;
  simSerial.print("ATD"); simSerial.print(currentAdminPhone); simSerial.println(";");
}

void savePhoneToEEPROM(String phone) {
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
    Serial.print("[Номер администратора успешно получен из EEPROM: ");
    Serial.println(currentAdminPhone);
  } else {
    currentAdminPhone = ""; // Гарантируем пустоту, если там мусор
    Serial.println("Память EEPROM пуста или содержит некорректный номер администратора.");
  }
} 

void checkAlarmsAndCall() {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;
  String url = "http://" + String(serverHost) + "/api/alarm/call_check";

  Serial.println("[БЭКЕНД] Проверка статуса аварий...");

  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {

      String payload = http.getString();
      Serial.print("[ОТВЕТ СЕРВЕРА]: ");
      Serial.println(payload);
      
      StaticJsonDocument<200> doc;
      DeserializationError error = deserializeJson(doc, payload);
      
      if (!error) {
        // УСПЕХ: Сервер ответил и JSON корректен. Обнуляем счетчик ошибок.
        serverErrorCounter = 0; 

        String serverPhone = doc["phone"].as<String>();
        int alarmActive = doc["alarm"].as<int>();

        // 1. Проверяем и обновляем номер в EEPROM
        if (serverPhone.length() >= 10 && serverPhone != currentAdminPhone) {
          Serial.printf("[СИНХРОНИЗАЦИЯ] Новый номер с сервера: %s\n", serverPhone.c_str());
          currentAdminPhone = serverPhone;
          savePhoneToEEPROM(currentAdminPhone);
        }

        // 2. Если есть авария — звоним
        if (alarmActive == 1) {
          if (millis() < muteUntilAll) {
            Serial.println("Авария датчика! НО звонок подавлен тишиной.");
          } else {
            Serial.print("Авария датчика! Звоню админу: ");
            Serial.println(currentAdminPhone);
            makeGSMCall();
          }
        } else {
          Serial.println("[СТАТУС] Аварий нет, всё спокойно.");
        }
      } else {
        Serial.println("Ошибка парсинга JSON от сервера");
        serverErrorCounter++;
        Serial.printf("[СВЯЗЬ] Некорректный ответ сервера. Попытка %d из %d\n", serverErrorCounter, MAX_SERVER_ERRORS);
      }
    } else {
      Serial.printf("[ОШИБКА] Сервер ответил кодом: %d\n", httpCode);
      serverErrorCounter++;
      Serial.printf("[СВЯЗЬ] Сбой ответа сервера. Попытка %d из %d\n", serverErrorCounter, MAX_SERVER_ERRORS);
    }
    http.end();
  } else {
    Serial.println("[ОШИБКА] Не удалось запустить HTTP-сессию");
    serverErrorCounter++;
    Serial.printf("[СВЯЗЬ] Нет подключения к серверу. Попытка %d из %d\n", serverErrorCounter, MAX_SERVER_ERRORS);
  }

  // --- ПРОВЕРКА КРИТИЧЕСКОГО СЛИШКОМ БОЛЬШОГО КОЛИЧЕСТВА ОШИБОК СЕРВЕРА ---
  if (serverErrorCounter >= MAX_SERVER_ERRORS) {
    if (millis() < muteUntilAll) Serial.println("Сервер недоступен 3 раза подряд! НО звонок подавлен.");
    else {
      Serial.print("Сервер недоступен 3 раза подряд! Звоню админу: ");
      Serial.println(currentAdminPhone);
      makeGSMCall();
    }
    
    // Сдвигаем на 1 шаг назад, чтобы через 2 минуты (в следующем цикле) 
    // счетчик снова стал равен 3 и опять пошел звонок, если сервер не ожил.
    serverErrorCounter = MAX_SERVER_ERRORS - 1; 
  }
}

// void checkAlarmsAndCall() {  
//   if (WiFi.status() != WL_CONNECTED) return;
//   WiFiClient client;
//   HTTPClient http;

//   String url = "http://" + String(serverHost) + "/api/alarm/call_check";
//   if (http.begin(client, url)) {
//     int httpCode = http.GET();
//     if (httpCode == HTTP_CODE_OK) {
//       String payload = http.getString();
//       Serial.print("[ОТВЕТ СЕРВЕРА]: ");
//       Serial.println(payload);
//       StaticJsonDocument < 200 > doc;
//       deserializeJson(doc, payload);
//       int alarmActive = doc["alarm"].as<int>();
//       if (alarmActive > 0) {
//         if (millis() < muteUntilAll) {
//           Serial.println("Авария датчика! НО звонок подавлен тишиной.");
//         } else {
//           Serial.print("Авария датчика! Звоню админу: ");
//           Serial.println(currentAdminPhone);
//           makeGSMCall();
//         }
//       }
//       // УСПЕХ: Сервер ответил и JSON корректен. Обнуляем счетчик ошибок.
//       serverErrorCounter = 0;
//       String serverPhone = doc["phone"].as<String>();

//       // 1. Проверяем и обновляем номер в EEPROM
//         if (serverPhone.length() >= 10 && serverPhone != currentAdminPhone) {
//           Serial.printf("Новый номер с сервера: %s\n", serverPhone.c_str());
//           currentAdminPhone = serverPhone;
//           savePhoneToEEPROM(currentAdminPhone);
//         }

//     } else serverErrorCounter++;
//     http.end();
//   }

//   if (serverErrorCounter >= 3) {
//     if (millis() < muteUntilAll) Serial.println("[МУТ] Сервер лежит! Звонок подавлен.");
//     else {
//       Serial.println("Сервер лежит! Звоню!");
//       makeGSMCall();
//     }
//     serverErrorCounter = 2; // Повтор через 2 минуты
//   }
// }

void setup() {
  Serial.begin(115200);
  simSerial.begin(9600);
  EEPROM.begin(16);
  delay(500);
  loadPhoneFromEEPROM();
  WiFiManager wifiManager;
  wifiManager.autoConnect(nameAP);

  Serial.println("\n>>> Проверка связи (AT)...");
  simSerial.println("AT");
  waitForResponse("OK");
  
  // simSerial.println("AT+CMGF=1"); delay(500);
  // simSerial.println("AT+CNMI=2,2,0,0,0"); delay(500);

  Serial.println("\n>>> Включаем определитель номера (CLIP)...");
  simSerial.println("AT+CLIP=1");
  waitForResponse("OK");
  simSerial.println("AT+CLIP=1"); 
  delay(500);

  // Сразу делаем первую проверку при старте системы
  checkAlarmsAndCall();
}

void loop() {
  // 1. Питание
  if (digitalRead(D5) == 0) {
    if (powerLossStartTime == 0) {
      powerLossStartTime = millis();
    }
    if (millis() - powerLossStartTime > 120000) {
      if (millis() >= muteUntilAll) {
        Serial.println("Питание нет более 2-х минут. Звоню!");
        makeGSMCall();
      }
      powerLossStartTime = millis(); 
    }
  } else powerLossStartTime = 0;

  // 2. Wi-Fi
  if (WiFi.status() != WL_CONNECTED) {
    if (wifiDisconnectStartTime == 0) wifiDisconnectStartTime = millis();
    if (millis() - wifiDisconnectStartTime > 300000) {
      if (millis() >= muteUntilAll) {
        Serial.println("WiFi нет более 5-ти минут. Звоню!");
        makeGSMCall();
      }
      wifiDisconnectStartTime = millis();
    }
  } else wifiDisconnectStartTime = 0;

  // 3. Сервер (раз в 2 мин)
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 120000) { 
    lastCheck = millis(); 
    checkAlarmsAndCall(); 
  }

  // 4. Обработка звонка-глушилки
  static int ringCount = 0;
  while (simSerial.available()) {
    String line = simSerial.readStringUntil('\n');
    if (line.indexOf("RING") != -1) {
      ringCount++;
      if (ringCount >= 2) {
        simSerial.println("ATH");
        muteUntilAll = millis() + 3600000UL; // Час тишины
        ringCount = 0;
        Serial.println(">>> Активирован режим тишины на 1 час!");
      }
    }
    if (line.indexOf("NO CARRIER") != -1) ringCount = 0;
  }
}