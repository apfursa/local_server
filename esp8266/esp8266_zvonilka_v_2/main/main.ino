#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include <DNSServer.h>
#include <WiFiManager.h>   
#include <SoftwareSerial.h> 
#include <EEPROM.h>        
#include <ArduinoJson.h>   

SoftwareSerial simSerial(D1, D2); 
ESP8266WebServer HTTP(80);                                     

const char *serverHost = "192.168.1.204"; 
const int serverPort = 80; 
const char *nameAP = "Zvonilka"; 

WiFiManager wifiManager;

// Глобальная переменная, где хранится текущий доверенный номер
String currentAdminPhone = ""; 

// --- Контроль стабильности связи ---
unsigned long wifiDisconnectStartTime = 0;             // Время, когда пропал Wi-Fi (0 - связь есть)
const unsigned long MAX_WIFI_DISCONNECT_TIME = 300000; // 5 минут без Wi-Fi в миллисекундах
unsigned long lastWifiLogTime = 0;                     // Таймер для вывода минутного отсчета в порт

int serverErrorCounter = 0;                            // Счетчик ошибок сервера подряд
const int MAX_SERVER_ERRORS = 3;                       // Максимум ошибок до звонка

// --- Контроль наличия 220В ---
const int powerPin = D5;                               // Пин датчика сети 220В (HIGH - свет есть, LOW - пропал)
unsigned long powerLossStartTime = 0;                  // Время, когда пропало 220В (0 - свет есть)
const unsigned long MAX_POWER_LOSS_TIME = 120000;      // 2 минуты до тревоги и между звонками
unsigned long lastPowerLogTime = 0;                    // Таймер для секундного отсчета в порт
bool powerAlarmTriggered = false;                      // Флаг: был ли уже звонок по аварии питания

int ringCounter = 0;                                   // Счетчик входящих гудков (RING) от админа

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
  HTTP.begin();
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
  Serial.print("📤 Отправляем ответное СМС (Транслит): ");
  Serial.println(replyText);

  if (currentAdminPhone.length() < 10) {
    Serial.println("[GSM] Ошибка: Нет номера администратора для отправки СМС!");
    return;
  }

  while(simSerial.available()) { simSerial.read(); }
  
  // Принудительно ставим обычный английский/ASCII режим
  simSerial.println("AT+CSCS=\"GSM\"");
  waitForResponse("OK", 1000);

  // Отправляем номер телефона как обычно
  simSerial.print("AT+CMGS=\"");
  simSerial.print(currentAdminPhone);
  simSerial.println("\""); 
  
  if (waitForResponse(">")) {
    simSerial.print(replyText);
    delay(100);
    simSerial.write(26); // Ctrl+Z
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
          Serial.print("\n🚨 КРИТИЧЕСКАЯ АВАРИЯ! Звоним админу: ");
          Serial.println(currentAdminPhone);
          makeGSMCall(currentAdminPhone);
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
    Serial.println("\n🚨 [АВАРИЯ СВЯЗИ] Сервер недоступен 3 раза подряд! Звоним админу...");
    makeGSMCall(currentAdminPhone);
    
    // Сдвигаем на 1 шаг назад, чтобы через 2 минуты (в следующем цикле) 
    // счетчик снова стал равен 3 и опять пошел звонок, если сервер не ожил.
    serverErrorCounter = MAX_SERVER_ERRORS - 1; 
  }
}

void setup()
{
  Serial.begin(115200);
  simSerial.begin(9600); 

  pinMode(powerPin, INPUT); // Контроль 220В
  
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
  // SSDP_init();

  Serial.println("\n>>> Проверка связи (AT)...");
  simSerial.println("AT");
  waitForResponse("OK");

  Serial.println("\n>>> Переводим в ТЕКСТОВЫЙ режим SMS...");
  simSerial.println("AT+CMGF=1");
  waitForResponse("OK");

  Serial.println("\n>>> Настраиваем прямую выдачу SMS в UART...");
  simSerial.println("AT+CNMI=2,2,0,0,0");
  waitForResponse("OK");

  Serial.println("\n>>> Включаем определитель номера (CLIP)...");
  simSerial.println("AT+CLIP=1");
  waitForResponse("OK");

  Serial.println("\n>>> Модем готов к работе. Переходим в loop().\n");
  
  // Сразу делаем первую проверку при старте системы
  checkAlarmsAndCall();
}

void loop()
{
  HTTP.handleClient();

  // --- АВТОНОМНЫЙ КОНТРОЛЬ ПИТАНИЯ 220В ---
  if (digitalRead(powerPin) == HIGH) {
    // Свет есть — сбрасываем таймеры аварии
    if (powerLossStartTime != 0) {
      Serial.println("\n[ПИТАНИЕ] Питание 220В восстановилось! Сброс таймера тревоги.");
      powerLossStartTime = 0;
      lastPowerLogTime = 0;
    }
  } else {
    // Свет пропал! Фиксируем время падения, если таймер еще не запущен
    if (powerLossStartTime == 0) {
      Serial.println("\n[⚠️ ПИТАНИЕ] Внимание! Пропало напряжение 220В! Запуск 2-минутного таймера...");
      powerLossStartTime = millis();
      lastPowerLogTime = millis();
    }

    // Вывод в порт каждые 10 секунд (10000 мс) оставшегося времени до звонка
    if (millis() - lastPowerLogTime >= 10000) {
      lastPowerLogTime = millis();
      long msPassed = millis() - powerLossStartTime;
      long secondsLeft = (MAX_POWER_LOSS_TIME - msPassed) / 1000;
      
      if (secondsLeft > 0) {
        Serial.printf("[⚠️ ПИТАНИЕ] Света нет. До звонка осталось: %ld сек...\n", secondsLeft);
      }
    }

    // Если питания нет непрерывно дольше 2 минут (120000 мс)
    if (millis() - powerLossStartTime >= MAX_POWER_LOSS_TIME) {
      Serial.println("\n🚨 [АВАРИЯ ПИТАНИЯ] Электричество отсутствует! Звоним админу...");
      makeGSMCall(currentAdminPhone);
      
      // Просто и элегантно сбрасываем таймер в текущую точку времени. 
      // Следующий круг проверок начнется с нуля и займет ровно 2 минуты!
      powerLossStartTime = millis(); 
      lastPowerLogTime = millis();
    }
  }

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

        // --- ОБРАБОТКА ВХОДЯЩЕГО ЗВЕНКА (СБРОС ПОСЛЕ 2-ГО ГУДКА) ---
        else if (smsBuffer.startsWith("+CLIP:")) {
          int firstQuote = smsBuffer.indexOf('"');
          int secondQuote = smsBuffer.indexOf('"', firstQuote + 1);
          String callerPhone = "";
          
          if (firstQuote != -1 && secondQuote != -1) {
            callerPhone = smsBuffer.substring(firstQuote + 1, secondQuote);
          }
          callerPhone.trim();

          // Если звонит чужой номер — сбрасываем БЕЗЗАСТЕНЧИВО и сразу
          if (currentAdminPhone.length() >= 10 && callerPhone != currentAdminPhone) {
            Serial.printf("\n[БЛОКИРОВКА] Звонок от чужого номера (%s) сброшен сразу.\n", callerPhone.c_str());
            simSerial.println("ATH");
          } else if (callerPhone == currentAdminPhone) {
            Serial.println("\n📞 [ВХОДЯЩИЙ ВЫЗОВ] Звонит админ. Начинаем отсчет гудков...");
            if (ringCounter == 0) ringCounter = 1; // Первый RING уже точно был или вот-вот прилетит
          }
        }
        
        // Модем при каждом гудке присылает отдельную строку "RING"
        else if (smsBuffer.equals("RING")) {
          // Если это звонит админ (счетчик уже запущен)
          if (ringCounter > 0) {
            ringCounter++;
            Serial.printf("[GSM] Гудок: %d\n", ringCounter);
            
            // // Если зафиксировали 2-й гудок (или больше, для надежности)
            // if (ringCounter >= 2) {
            //   Serial.println("🚨 2-й гудок получен! Сбрасываем и отправляем СМС...");
            //   simSerial.println("ATH"); // Сброс вызова
              
            //   sendSMSReply("Сообщение от звонилки. Всё работает!"); 
            //   ringCounter = 0; // Сброс счетчика для будущих звонков
            // }

            // Если зафиксировали 2-й гудок (или больше, для надежности)

            
            if (ringCounter >= 2) {
              Serial.println("🚨 2-й гудок получен! Сбрасываем и собираем статус...");
              simSerial.println("ATH"); // Сброс вызова
              delay(500); // Даем модему секунду очистить линию

              String smsText = "";

              // 1. Проверяем локальное питание 220В на ESP
              // Допустим, LOW означает, что свет пропал и сидим на аккуме звонилки
              if (digitalRead(powerPin) == LOW) {
                smsText = "220V - TREVOGA!!!\nWiFi - OK.\nBackend - OK.\nSensors - OK.\n\n(Dlya otmeny shli: 220 [chasy])";
              } 
              // 2. Проверяем, жив ли Wi-Fi роутер
              else if (WiFi.status() != WL_CONNECTED) {
                smsText = "220V - OK.\nWiFi - TREVOGA!!!\n\n(Dlya otmeny shli: W [chasy])";
              } 
              // 3. Если с железом всё ок, стучимся к бэкенду
              else {
                WiFiClient client;
                HTTPClient http;
                
                // Стучимся на твой новый call_check
                http.begin(client, "http://192.168.1.205/api/alarm/call_check");
                http.setTimeout(5000); // <-- ЖДЕМ ОТВЕТА ДО 5 СЕКУНД, НЕ ПАНИКУЕМ РАНЬШЕ ВРЕМЕНИ 
                int httpCode = http.GET();

                if (httpCode == 200) {
                  String payload = http.getString();
                  
                  // Парсим JSON от Flask
                  DynamicJsonDocument doc(1024);
                  DeserializationError error = deserializeJson(doc, payload);

                  if (!error) {
                    int alarmRow = doc["alarm"]; // Получаем число (0 если ок, или номер строки)

                    if (alarmRow == 0) {
                      smsText = "220V - OK.\nWiFi - OK.\nBackend - OK.\nSensors - OK.";
                    } else {
                      // Если вернулся номер строки, пишем его в СМС
                      smsText = "220V - OK.\nWiFi - OK.\nBackend - OK.\nSensors - TREVOGA!!! (Stroka=" + String(alarmRow) + ")\n\n(Dlya otmeny shli: " + String(alarmRow) + " [chasy])";
                    }
                  } else {
                    smsText = "220V - OK.\nWiFi - OK.\nBackend - OK.\nSensors - JSON ERROR";
                  }
                } else {
                  // Сервер выдал 500, 404 или вообще не ответил (упал скрипт Flask)
                  smsText = "220V - OK.\nWiFi - OK.\nBackend - TREVOGA!!!\n\n(Dlya otmeny shli: S [chasy])";
                }
                http.end();
              }

              // Отправляем итоговый транслит-отчет
              sendSMSReply(smsText);
              
              ringCounter = 0; // Сброс счетчика гудков
            }


          }
        }

        else if (smsBuffer.equals("NO CARRIER")) {
          Serial.println("[GSM] Вызов прекращен (NO CARRIER). Сброс счетчика гудков.");
          ringCounter = 0;
        }

      }
      smsBuffer = ""; 
    }
  }

  if (Serial.available()) {
    char c = Serial.read();
    simSerial.print(c);
  }

  // --- АВТОНОМНЫЙ КОНТРОЛЬ WI-FI ---
  if (WiFi.status() == WL_CONNECTED) {
    if (wifiDisconnectStartTime != 0) {
      Serial.println("\n[СВЯЗЬ] Wi-Fi восстановился! Сброс таймера отсутствия сети.");
      wifiDisconnectStartTime = 0;
      lastWifiLogTime = 0;
    }
  } else {
    if (wifiDisconnectStartTime == 0) {
      Serial.println("\n[⚠️ СВЯЗЬ] Wi-Fi пропал! Запуск 5-минутного таймера тревоги...");
      wifiDisconnectStartTime = millis();
      lastWifiLogTime = millis();
    } 
    
    // Вывод в порт каждую минуту (60000 мс) при отсутствии связи
    if (millis() - lastWifiLogTime >= 60000) {
      lastWifiLogTime = millis();
      int minutesPassed = (millis() - wifiDisconnectStartTime) / 60000;
      int minutesLeft = 5 - minutesPassed;
      if (minutesLeft > 0) {
        Serial.printf("[⚠️ СВЯЗЬ] Wi-Fi отсутствует уже %d мин. (До звонка осталось: %d мин.)\n", minutesPassed, minutesLeft);
      }
    }

    // Если Wi-Fi лежит непрерывно дольше лимита (5 минут)
    if (millis() - wifiDisconnectStartTime >= MAX_WIFI_DISCONNECT_TIME) {
      Serial.println("\n🚨 [АВАРИЯ СВЯЗИ] Wi-Fi отсутствует более 5 минут! Звоним админу...");
      makeGSMCall(currentAdminPhone);
      wifiDisconnectStartTime = millis(); // Сдвигаем таймер, чтобы повторить через 5 минут
      lastWifiLogTime = millis();
    }
  }

  // --- ТАЙМЕР ОПРОСА БЭКЕНДА (Раз в 2 минуты) ---
  static unsigned long lastCheckTime = 0;
  if (lastCheckTime == 0) lastCheckTime = millis(); 
  
  if (millis() - lastCheckTime >= 120000) {
    lastCheckTime = millis();
    checkAlarmsAndCall(); 
  }
}