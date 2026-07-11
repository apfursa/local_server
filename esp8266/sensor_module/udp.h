
#include <WiFiUdp.h>
#include <Arduino.h>
#include "config.h"

WiFiUDP udp;

void get_server_IP() {
  static unsigned long lastSendTime = 0; // время последней отправки
  static int attempts = 0;  // попытки

    if (attempts == 10) { // Однократное сообщение
        Serial.println("[UDP] Лимит попыток исчерпан");
        attempts = 0;
        return; 
    }

    // Шлем широковещательный запрос каждую секунду
    if (millis() - lastSendTime > 1000) {
        attempts++;
        Serial.printf("[UDP] Отправка широковещательного запроса  ... (попытка %d)\n", attempts);
        udp.beginPacket("255.255.255.255", 8888);
        udp.print("DISCOVER_SERVER");
        udp.endPacket();
        lastSendTime = millis();
        yield(); 
    }

  // Проверяем ответ
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    yield(); 
    char buf[64];
    memset(buf, 0, sizeof(buf));
    udp.read(buf, sizeof(buf) - 1);
    
    String response = String(buf);
    response.trim();
    
    Serial.print("[UDP] Получен ответ: ");
    Serial.println(response);

    if (response.startsWith("SERVER_IP:")) {
      serverIP = response.substring(10);
      serverIP.trim();
      isServerFound = true;
      Serial.println("[UDP] Сервер успешно найден!");
    }
    yield(); 
  }
}