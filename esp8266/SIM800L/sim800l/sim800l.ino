#include <SoftwareSerial.h>

SoftwareSerial simSerial(D1, D2);

const String PHONE = "+79181656914";  // ← ваш номер
const String MESSAGE = "Тестовое сообщение от ESP8266";

void setup() {
    delay(2000);
    Serial.begin(115200);
    simSerial.begin(9600);
    Serial.println("Старт");
    
    delay(3000); // ждём готовности модема
    
    // Режим текстовых SMS
    simSerial.println("AT+CMGF=1");
    delay(1000);
    
    // Указываем номер получателя
    simSerial.print("AT+CMGS=\"");
    simSerial.print(PHONE);
    simSerial.println("\"");
    delay(1000);
    
    // Текст сообщения + Ctrl+Z для отправки 
    simSerial.print(MESSAGE);
    simSerial.write(26); // Ctrl+Z
    delay(5000); // ждём отправки
    
    Serial.println("SMS отправлено");
}

void loop() {
    while (simSerial.available()) {
        Serial.print((char)simSerial.read());
    }
    while (Serial.available()) {
        simSerial.print((char)Serial.read());
    }
}