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

/*
void handleGsmInit() {
    if (initStep == INIT_DONE) return;

    yield();

    // Таймаут — сброс и выход, switch выполнится в СЛЕДУЮЩЕЙ итерации
    if (millis() - stepStartTime > 5000) {

        Serial.printf("[GSM] Таймаут на шаге %d, повтор...\n", initStep); 
        Serial.println("Таймаут шага, повтор с начала...");
        initStep = INIT_CHECK_AT;
        stepStartTime = millis();
        buffer = "";
        return; // ← КРИТИЧНО: выходим, не падаем в switch
    }

    Serial.printf("[GSM] Текущий шаг: %d\n", initStep);

    switch (initStep) {
        case INIT_CHECK_AT:
            gsmSerial.println("AT");
            stepStartTime = millis(); // ← сбрасываем таймер при каждой отправке
            initStep = INIT_WAIT_AT;  // ← ждём ответ в отдельном состоянии
            break;

        case INIT_WAIT_AT:
            if (buffer.indexOf("OK") != -1) {
                buffer = "";
                stepStartTime = millis();
                gsmSerial.println("AT+CREG?");
                initStep = INIT_CHECK_CREG;
            }
            break;

        case INIT_CHECK_CREG:
            if (buffer.indexOf("+CREG: 0,1") != -1) {
                buffer = "";
                stepStartTime = millis();
                gsmSerial.println("AT+CMGF=1");
                initStep = INIT_CMGF;
            }
            break;

        case INIT_CMGF:
            if (buffer.indexOf("OK") != -1) {
                buffer = "";
                stepStartTime = millis();
                gsmSerial.println("AT+CNMI=2,2,0,0,0");
                initStep = INIT_CNMI;
            }
            break;

        case INIT_CNMI:
            if (buffer.indexOf("OK") != -1) {
                buffer = "";
                stepStartTime = millis();
                gsmSerial.println("AT+CLIP=1");
                initStep = INIT_CLIP;
            }
            break;

        case INIT_CLIP:
            if (buffer.indexOf("OK") != -1) {
                initStep = INIT_DONE;
                Serial.println(">>> GSM готов к работе!");
            }
            break;
    }
}
*/

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
    lastSmsContent = text;
}

/*
bool gsm_handle() {
    while (gsmSerial.available()) {
        buffer += (char)gsmSerial.read();
    }

    while (buffer.indexOf("\r\n") != -1) {
        String line = getNextLine();
        line.trim();
        if (line.length() == 0) continue;

        Serial.printf("[GSM RAW] %s\n", line.c_str());  // временно для отладки

        // ← Сначала GSM инициализация проверяет строку
        if (initStep != INIT_DONE) {
            handleGsmInitLine(line);
        }

        // Обработка звонка
        if (line.indexOf("RING") != -1) {
            ringCount++;
            if (ringCount >= 2) {
                gsmSerial.println("ATH");
                muteUntilAll = millis() + 3600000UL;
                ringCount = 0;
            }
        } else if (line.indexOf("NO CARRIER") != -1) {
            ringCount = 0;
        }

        // Автомат SMS
        switch (gsm_state) {
            case IDLE:
                if (line.startsWith("+CMGR:")) gsm_state = SMS_READING;
                break;
            case SMS_READING:
                if (line.equals("OK")) {
                    processSMS(collectedText);
                    collectedText = "";
                    gsm_state = IDLE;
                } else {
                    collectedText += line + "\n";
                }
                break;
        }
    }
    return false;
}
*/

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

  // // 2. Отправка команд инициализации (не зависит от входящих строк)
  // if (initStep == INIT_CHECK_AT) {
  //     Serial.println("[GSM] Отправляем AT...");
  //     gsmSerial.println("AT");
  //     stepStartTime = millis();
  //     initStep = INIT_WAIT_AT;
  // }

  // // 3. Таймаут
  // if (initStep != INIT_DONE && initStep != INIT_IDLE) {
  //     if (millis() - stepStartTime > 5000) {
  //         Serial.printf("[GSM] Таймаут на шаге %d, повтор...\n", initStep);
  //         initStep = INIT_CHECK_AT;
  //         stepStartTime = millis();
  //         buffer = "";
  //     }
  // }

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
                if (line.startsWith("+CMGR:")) gsm_state = SMS_READING;
                break;
            case SMS_READING:
                if (line.equals("OK")) {
                    processSMS(collectedText);
                    collectedText = "";
                    gsm_state = IDLE;
                } else {
                    collectedText += line + "\n";
                }
                break;
        }

        yield(); // ← дать ESP обработать фоновые задачи между строками
    }
  return false;
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

