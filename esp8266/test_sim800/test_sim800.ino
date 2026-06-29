#include <SoftwareSerial.h>
#include <ArduinoJson.h>

#include "config.h"
#include "wifi_manager.h"
#include "eeprom.h"
#include "http_client.h"
#include "udp.h"
#include "gsm.h"
#include "DataSync.h"

// Глобальные объекты
// SoftwareSerial simSerial(D1, D2);
// ESP8266WebServer HTTP(80);
// String serverHost = "192.168.1.204";
String serverHost = "";
// const int serverPort = 80; 
const char *nameAP = "Zvonilka";                      // SSID точки доступа, если esp8266 не подключилась по wifi к роутеру
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
// int ringCounter = 0;                                   // Счетчик входящих гудков (RING) от админа
String currentAdminPhone = "";  
bool isServerFound = false;                            // найден ли сервер
unsigned long lastDiscoveryTime = 0;
bool isCalling = false;                                // Переменная состояния модема
unsigned long callStartTime = millis();
bool needBackendCheck = false;                         // Флаг: нужно проверить бэкенд и отправить статус
// Константы
const int RX_PIN = D1;
const int TX_PIN = D2;
const int BAUD_RATE = 9600;
enum State { 
  GET_IP_SERVER, 
  GET_DATA_FROM_SERVER, 
  SYNC_PHONE_NUMBER, 
  LOGIC, 
  READ_SMS, 
  DO_SOMETHING_NEW, 
  STATE_IDLE
  };  // Состояния системы
State globalState = GET_IP_SERVER;
int alarm = 0;

// Состояния для автомата обработки звонка
enum CallState { CALL_IDLE, CALL_DETECTED };
CallState callState = CALL_IDLE;
// int ringCount = 0;
// unsigned long ringLastTime = 0;
// unsigned long muteUntilAll = 0; // Время окончания режима тишины

// Объявляем структуру здесь, чтобы она была видна всему проекту

void setup() {
  delay(1000);
  Serial.begin(115200);
  gsm_begin(9600);
  EEPROM.begin(512);
  // loadPhoneFromEEPROM();
  setupWiFi();
  udp.begin(8888);
  Serial.println("System Initialized");
}

void loop() {
  gsm_handle();  // 1. Асинхронная обработка GSM (всегда первая!)

  // 2. Остальная логика системы
  switch(globalState) {
    case GET_IP_SERVER:
      Serial.println("[LOOP] GET_IP_SERVER");
      get_server_IP(); 
      if (isServerFound) globalState = GET_DATA_FROM_SERVER;
      break;

    case GET_DATA_FROM_SERVER:
      yield();
      Serial.println("[LOOP] GET_DATA_FROM_SERVER");
      Serial.printf("[HTTP] httpState = %d\n", httpState);
      if (httpState == HTTP_IDLE) { 
        Serial.println("[HTTP] Запускаем запрос...");
        startGetRequest("/api/alarm/call_check");
      } else if (httpState == HTTP_WAITING) {
        Serial.println("[HTTP] Ждём ответ..."); 
        handleHttp();
      } else if (httpState == HTTP_DONE) {
        Serial.println("[HTTP] Ответ получен!");
        Serial.print("[HTTP] Тело ответа: ");
        Serial.println(httpResponse); 
          // Используй JsonDocument без размера для ArduinoJson 7.x
          JsonDocument doc; 
          DeserializationError error = deserializeJson(doc, httpResponse);
          
          if (!error) {
              alarm = doc["alarm"];
              serverPhone = doc["phone"].as<String>();
              globalState = SYNC_PHONE_NUMBER;
          } else {
            Serial.print("[JSON] Ошибка парсинга: ");
            Serial.println(error.c_str()); 
              globalState = STATE_IDLE; 
          }
          httpResponse = ""; 
          httpState = HTTP_IDLE;
      } else if (httpState == HTTP_ERROR) {
        Serial.println("[HTTP] ОШИБКА запроса!");
          globalState = STATE_IDLE;
      }
      
      break;

    case SYNC_PHONE_NUMBER:
      Serial.println("[LOOP] SYNC_PHONE_NUMBER");
      if (syncServerPhone(serverPhone)){
        globalState = LOGIC;
      } else {
        globalState = STATE_IDLE;
      }
      break;

    case LOGIC:
      Serial.println("[LOOP] LOGIC");          
      Serial.printf("[LOGIC] alarm = %d\n", alarm);

      if (initStep != INIT_DONE) {  // ← добавьте эту проверку
        Serial.println("[LOGIC] Ждём GSM...");
        break;
      }
      // ← добавьте проверку тишины
    if (millis() < muteUntilAll) {
        Serial.println("[LOGIC] Режим тишины, пропускаем звонок");
        callStartTime = millis();
        globalState = READ_SMS;
        break;
    }
      if (alarm > 0){
        yield();        // ← добавьте
        ESP.wdtFeed();  // ← и это — явный сброс watchdog
        gsm_call(currentAdminPhone);
        callStartTime = millis();
        globalState = READ_SMS;
      } else {
        callStartTime = millis();
        globalState = READ_SMS;
      }
      break;

    case READ_SMS:
      // Ждём 2 минуты, потом снова проверяем сервер
      if (millis() - callStartTime > 120000UL) {
          Serial.println("[LOOP] 2 минуты прошло, проверяем сервер...");
          isCalling = false;  // ← звонок завершён
          globalState = GET_DATA_FROM_SERVER;
      }
      break;

    case DO_SOMETHING_NEW:
      Serial.println(lastSmsContent);
      globalState = GET_DATA_FROM_SERVER;
      break;

    case STATE_IDLE:
      break;
  }
}
