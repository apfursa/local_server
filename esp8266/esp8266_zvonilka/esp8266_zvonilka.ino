#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <DNSServer.h>
#include <WiFiManager.h>                        
#include <ESP8266SSDP.h>
#include <SoftwareSerial.h> 
#include <EEPROM.h>        
#include <ArduinoJson.h>   

SoftwareSerial simSerial(D1, D2); 
ESP8266WebServer HTTP(80);                                     

const char *serverHost = "192.168.1.205"; 
const int serverPort = 80;                
int sensorId = 34; 
const char *nameAP = "BorisPhone_34"; 

WiFiManager wifiManager;

// Глобальная переменная, где хранится текущий доверенный номер
String currentAdminPhone = ""; 

// --- ФУНКЦИИ РАБОТЫ С EEPROM ---
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

void HTTP_init(void) {
  HTTP.on("/index.html", HTTP_GET, []() { HTTP.send(200, "text/plain", "Звонилка"); });
  HTTP.on("/description.xml", HTTP_GET, []() { SSDP.schema(HTTP.client()); });
  HTTP.begin();
}

void SSDP_init(void) {
  SSDP.setSchemaURL("description.xml");
  SSDP.setHTTPPort(80);
  SSDP.setName("Звонилка");
  SSDP.begin();
}

void makeGSMCall(String phoneNumber) {
  phoneNumber.trim(); 
  if (phoneNumber.length() < 10) {
    Serial.println("[GSM] Ошибка: Неверный номер для звонка!");
    return;
  }
  while(simSerial.available()) { simSerial.read(); }
  simSerial.print("ATD");
  simSerial.print(phoneNumber);
  simSerial.println(";");
}

void sendSMSReply(String replyText) {
  Serial.print("📤 Отправляем ответное SMS: ");
  Serial.println(replyText);

  if (currentAdminPhone.length() < 10) {
    Serial.println("[GSM] Ошибка: Нет номера администратора для отправки СМС!");
    return;
  }

  while(simSerial.available()) { simSerial.read(); }
  
  simSerial.print("AT+CMGS=\"");
  simSerial.print(currentAdminPhone);
  simSerial.println("\""); 
  
  if (waitForResponse(">")) {
    simSerial.print(replyText);
    delay(100);
    simSerial.write(26); 
    waitForResponse("OK", 4000); 
  }
}

void sendSmsToBackend(String text) {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;
  
  text.replace(" ", "%20"); 
  String url = "http://" + String(serverHost) + "/api/alarm/sms_command?text=" + text;

  Serial.print("Передаем SMS на сервер: "); Serial.println(url);

  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      String serverReply = http.getString();
      serverReply.trim();
      if (serverReply.length() > 0) {
        sendSMSReply(serverReply);
      }
    }
    http.end();
  }
}

void checkAlarmsAndCall()
{
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;
  String url = "http://" + String(serverHost) + "/api/alarm/call_check";

  Serial.println("[БЭКЕНД] Проверка статуса аварий...");

  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      String jsonReply = http.getString();
      
      StaticJsonDocument<200> doc;
      DeserializationError error = deserializeJson(doc, jsonReply);
      
      if (!error) {
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
          Serial.print("\n🚨 КРИТИЧЕСКАЯ АВАРИЯ! Звоним админу: ");
          Serial.println(currentAdminPhone);
          makeGSMCall(currentAdminPhone);
        } else {
          Serial.println("[СТАТУС] Аварий нет, всё спокойно.");
        }
      } else {
        Serial.println("Ошибка парсинга JSON от сервера");
      }
    } else {
      Serial.printf("[ОШИБКА] Сервер ответил кодом: %d\n", httpCode);
    }
    http.end();
  }
}

void setup()
{
  Serial.begin(115200);
  simSerial.begin(9600); 
  
  EEPROM.begin(16); 
  delay(500);
  Serial.println("\n--- ЗАПУСК ЗВОНИЛКИ С ДИАГНОСТИКОЙ SIM800L ---");

  loadPhoneFromEEPROM();

  wifiManager.setConfigPortalTimeout(120); 
  if (!wifiManager.autoConnect(nameAP)) {
    Serial.println("Не удалось подключиться, перезагрузка...");
    delay(3000);
    ESP.restart();
  }
  
  Serial.println("Wi-Fi Успешно подключен!");
  HTTP_init();
  SSDP_init();

  Serial.println("\n>>> Проверка связи (AT)...");
  simSerial.println("AT");
  waitForResponse("OK");

  Serial.println("\n>>> Переводим в ТЕКСТОВЫЙ режим SMS...");
  simSerial.println("AT+CMGF=1");
  waitForResponse("OK");

  Serial.println("\n>>> Настраиваем прямую выдачу SMS в UART...");
  simSerial.println("AT+CNMI=2,2,0,0,0");
  waitForResponse("OK");

  Serial.println("\n>>> Модем готов к работе. Переходим в loop().\n");
  
  // Сразу делаем первую проверку при старте системы
  checkAlarmsAndCall();
}

void loop()
{
  HTTP.handleClient();

  // --- ОБРАБОТКА ВХОДЯЩИХ СМС С ЖЕСТКИМ ФИЛЬТРОМ НОМЕРА ---
  static String smsBuffer = ""; 

  while (simSerial.available()) {
    char c = simSerial.read();
    Serial.print(c); 

    if (c != '\r' && c != '\n') {
      smsBuffer += c;
    } 
    else if (c == '\n') { 
      smsBuffer.trim();
      
      if (smsBuffer.length() > 0) {
        if (smsBuffer.startsWith("+CMT:")) {
          
          int firstQuote = smsBuffer.indexOf('"');
          int secondQuote = smsBuffer.indexOf('"', firstQuote + 1);
          String senderPhone = "";
          if (firstQuote != -1 && secondQuote != -1) {
            senderPhone = smsBuffer.substring(firstQuote + 1, secondQuote);
          }
          senderPhone.trim();

          // Ожидаем текст сообщения (Таймаут уменьшен до 500мс для стабильности SoftwareSerial)
          unsigned long startWait = millis();
          String smsText = "";
          while (smsText.length() == 0 && (millis() - startWait < 500)) {
            if (simSerial.available()) {
              smsText = simSerial.readStringUntil('\n');
              smsText.trim();
            }
            yield(); 
          }

          // КРИТИЧЕСКИЙ ФИЛЬТР: Сравниваем с номером из памяти
          if (currentAdminPhone.length() < 10 || senderPhone != currentAdminPhone) {
            Serial.printf("\n[БЛОКИРОВКА] СМС от номера (%s) проигнорировано! Доверенный: %s\n", 
                          senderPhone.c_str(), currentAdminPhone.c_str());
            smsBuffer = "";
            continue; 
          }

          Serial.print("\n🚨🚨🚨 АВТОРИЗОВАННОЕ СМС СООБЩЕНИЕ 🚨🚨🚨");
          Serial.print("\n[ТЕКСТ]: "); Serial.println(smsText);
          Serial.println("🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨\n");

          sendSmsToBackend(smsText);
        }
      }
      smsBuffer = ""; 
    }
  }

  if (Serial.available()) {
    char c = Serial.read();
    simSerial.print(c);
  }

  // Проверка аварий строго каждые 2 минуты (исправлено условие)
  static unsigned long lastCheckTime = 0;
  if (lastCheckTime == 0) lastCheckTime = millis(); // Инициализация при первом проходе loop
  
  if (millis() - lastCheckTime >= 120000) {
    lastCheckTime = millis();
    checkAlarmsAndCall();
  }
}