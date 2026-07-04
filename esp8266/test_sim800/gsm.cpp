#include "gsm.h"
#include <SoftwareSerial.h>

// --- Настройки ---
static SoftwareSerial gsmSerial(D1, D2);
static String buffer = ""; 
static String collectedText = "";

// --- Глобальные переменные ---
bool gsm_ringDetected = false;
String lastSmsContent = "";
int ringCount = 0;
unsigned long ringLastTime = 0;
unsigned long muteUntilAll = 0;
unsigned long lastCommandTime = 0;
String lastSmsFrom = "";
bool newSmsReceived = false;

// --- Состояния ---
enum State { IDLE, WAITING_FOR_AT, WAITING_FOR_CREG, SMS_READING };
State gsm_state = IDLE;

GsmInitStep initStep = INIT_IDLE;
unsigned long stepStartTime = 0;

// --- Функции ---

void flushSerial() {
    while(gsmSerial.available()) gsmSerial.read();
}

void gsm_begin(long baud) {
    gsmSerial.begin(baud);
    Serial.println(">>> Запуск GSM инициализации...");
    initStep = INIT_IDLE;  // ← не INIT_CHECK_AT, чтобы gsm_handle не мешал
    delay(1000);
    gsmSerial.println("AT+CREG?");
    delay(500);
    gsm_handle();
    gsmSerial.println("AT+CMGF=1");
    delay(500);
    gsm_handle();
    gsmSerial.println("AT+CNMI=2,2,0,0,0");
    delay(500);
    gsm_handle();
    gsmSerial.println("AT+CLIP=1");
    delay(500);
    gsm_handle();
    initStep = INIT_DONE;  // ← сразу помечаем как готово
    Serial.println(">>> GSM готов к работе!");
    stepStartTime = millis();
}

void handleGsmInitLine(String line) {
    switch (initStep) {
        case INIT_WAIT_AT:
            if (line.indexOf("OK") != -1) {
                stepStartTime = millis();
                gsmSerial.println("AT+CREG?");
                initStep = INIT_CHECK_CREG;
            }
            break;
        case INIT_CHECK_CREG:
            if (line.indexOf("+CREG: 0,1") != -1) {
                stepStartTime = millis();
                gsmSerial.println("AT+CMGF=1");
                initStep = INIT_CMGF;
            }
            break;
        case INIT_CMGF:
            if (line.indexOf("OK") != -1) {
                stepStartTime = millis();
                gsmSerial.println("AT+CNMI=2,2,0,0,0");
                initStep = INIT_CNMI;
            }
            break;
        case INIT_CNMI:
            if (line.indexOf("OK") != -1) {
                stepStartTime = millis();
                gsmSerial.println("AT+CLIP=1");
                initStep = INIT_CLIP;
            }
            break;
        case INIT_CLIP:
            if (line.indexOf("OK") != -1) {
                initStep = INIT_DONE;
                Serial.println(">>> GSM готов к работе!");
            }
            break;
    }
}

String getNextLine() {
    int index = buffer.indexOf("\r\n");
    if (index == -1) return "";
    String line = buffer.substring(0, index);
    buffer.remove(0, index + 2);
    return line;
}

void processSMS(String text) {
    Serial.println("--- Пришло SMS ---");
    Serial.printf("От: %s, Текст: %s\n", lastSmsFrom.c_str(), text.c_str());
    lastSmsContent = text;
    newSmsReceived = true;  // ← сигнал что есть новая SMS для обработки
}

bool gsm_handle() {
  yield(); 
   while (gsmSerial.available()) {
        char c = gsmSerial.read();
        buffer += c;  // ← всегда читаем в буфер, не выбрасываем
    }

    if (isCalling) {
    if (buffer.indexOf("NO CARRIER") != -1 || 
        buffer.indexOf("BUSY") != -1) {
        Serial.println("[GSM] Звонок завершён");
        isCalling = false;
        buffer = "";
    } else if (buffer.indexOf("RING") != -1) {  // ← добавьте
        Serial.println("[GSM] Входящий звонок — сбрасываем и уходим в тишину");
        gsmSerial.println("ATH");
        muteUntilAll = millis() + 3600000UL;
        isCalling = false;
        buffer = "";
    } else if (buffer.length() > 256) {
        buffer = "";
    }
    return false;
}

  // ← Максимум 5 строк за одну итерацию loop()
    int linesProcessed = 0;
    while (buffer.indexOf("\r\n") != -1 && linesProcessed < 5) {
        linesProcessed++;
        String line = getNextLine();
        line.trim();
        if (line.length() == 0) continue;

        Serial.printf("[GSM RAW] %s\n", line.c_str());

        if (initStep != INIT_DONE) {
            handleGsmInitLine(line);
        }

        if (line.indexOf("RING") != -1) {
            ringCount++;
            if (ringCount >= 2) {
              ESP.wdtFeed();  // ← добавьте
              delay(200);     // ← добавьте
              gsmSerial.println("ATH");
              muteUntilAll = millis() + 3600000UL;
              ringCount = 0;
            }
        } else if (line.indexOf("NO CARRIER") != -1) {
            ringCount = 0;
        }

        switch (gsm_state) {
            case IDLE:
                if (line.startsWith("+CMT:")) {  
                    // Парсим: +CMT: "+79181656914",,"24/01/01,12:00:00+12"
                    int start = line.indexOf('"') + 1;
                    int end = line.indexOf('"', start);
                    if (start > 0 && end > start) {
                        lastSmsFrom = line.substring(start, end);
                    }
                    gsm_state = SMS_READING;
                }
                break;
            // case SMS_READING:
            //     if (line.equals("OK")) {
            //         processSMS(collectedText);
            //         collectedText = "";
            //         gsm_state = IDLE;
            //     } else {
            //         collectedText += line + "\n";
            //     }
            //     break;

            case SMS_READING:
                processSMS(line);
                gsm_state = IDLE;
                break;
        }

        yield(); // ← дать ESP обработать фоновые задачи между строками
    }
  return false;
}

void gsm_sendSms(String number, String text) {
    Serial.printf("[GSM_SMS] Отправка на %s: %s\n", number.c_str(), text.c_str());
    gsm_clearBuffer();
    gsmSerial.print("AT+CMGS=\"");
    gsmSerial.print(number);
    gsmSerial.println("\"");
    delay(500);
    ESP.wdtFeed();
    gsmSerial.print(text);
    gsmSerial.write(26); // Ctrl+Z
    ESP.wdtFeed();
}

void gsm_call(String number) {
    Serial.printf("[GSM_CALL] Звоним на: %s\n", number.c_str());
    gsm_clearBuffer();  // ← очищаем буфер перед звонком
    delay(500);           // ← добавьте
    ESP.wdtFeed();        // ← добавьте
    gsmSerial.print("ATD");
    ESP.wdtFeed();        // ← добавьте
    gsmSerial.print(number);
    ESP.wdtFeed();        // ← добавьте
    gsmSerial.println(";");
    ESP.wdtFeed();        // ← добавьте
    isCalling = true;
}

void gsm_clearBuffer() {
    buffer = "";
    while (gsmSerial.available()) gsmSerial.read();
}

