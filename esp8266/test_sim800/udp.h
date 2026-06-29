
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
      serverHost = response.substring(10);
      serverHost.trim();
      isServerFound = true;
      Serial.println("[UDP] Сервер успешно найден!");
    }
    yield(); 
  }
}


// #include <WiFiUdp.h>
// #include <Arduino.h>
// #include "config.h"

// WiFiUDP udp;

// // void findServerViaUDP() {
// //     static unsigned long lastSendTime = 0;
// //     static unsigned long lastCheckTime = 0; // Таймер для parsePacket
// //     static int attempts = 0;

// //     if (attempts >= 10) {
// //         return; 
// //     }

// //     // 1. Отправляем пакет только раз в 1 секунду
// //     if (millis() - lastSendTime >= 1000) {
// //         lastSendTime = millis();
// //         attempts++;
        
// //         Serial.printf("[UDP] Попытка %d/10...\n", attempts);
        
// //         udp.beginPacket("255.255.255.255", 8888);
// //         udp.print("DISCOVER_SERVER");
// //         udp.endPacket();
        
// //         if (attempts >= 10) {
// //             Serial.println("[UDP] Сервер не найден. Работаю в автономном режиме.");
// //         }
// //     }

// //     // 2. Проверяем входящий ответ НЕ чаще чем раз в 100 миллисекунд!
// //     // Это разгрузит процессор и спасет Wi-Fi стек от зависания
// //     if (millis() - lastCheckTime < 100) {
// //         return; 
// //     }
// //     lastCheckTime = millis();

// //     int packetSize = udp.parsePacket();
// //     if (packetSize > 0) {
// //         // Делаем буфер чуть больше с запасом и сразу зануляем его
// //         char buf[64]; 
// //         memset(buf, 0, sizeof(buf)); 

// //         // Читаем максимум 63 байта, оставляя последний байт под '\0' гарантированно
// //         int len = udp.read(buf, sizeof(buf) - 1); 
        
// //         if (len > 0) {
// //             buf[len] = '\0'; // Безопасное закрытие строки
// //             String response = String(buf);
// //             response.trim();

// //             if (response.startsWith("SERVER_IP:")) {
// //                 serverHost = response.substring(10);
// //                 serverHost.trim(); // Очищаем от возможных пробелов и \r
// //                 isServerFound = true;
                
// //                 Serial.print("[UDP] Сервер найден! IP: ");
// //                 Serial.println(serverHost);
                
// //                 // КРИТИЧЕСКИ ВАЖНО: Сбрасываем WDT и даем плате 
// //                 // завершить текущий loop перед отправкой HTTP запроса!
// //                 yield(); 
// //             }
// //         }
// //     }
// // }

// void findServerViaUDP() {
//   udp.begin(8888);
//   Serial.println("[UDP] Ищем сервер...");
  
//   int attempts = 0;
//   // Попробуем найти сервер 10 раз (это 10 секунд ожидания)
//   while (!isServerFound && attempts < 10) {
//     udp.beginPacket("255.255.255.255", 8888);
//     udp.print("DISCOVER_SERVER");
//     udp.endPacket();

//     int packetSize = udp.parsePacket();
//     if (packetSize) {
//       char buf[32];
//       udp.read(buf, 32);
//       String response = String(buf);
      
//       if (response.startsWith("SERVER_IP:")) {
//         serverHost = response.substring(10);
//         isServerFound = true;
//         // Сделайте так:
//         Serial.print("[UDP] Сервер найден! IP: ");
//         Serial.println(serverHost);
//       }
//     }
    
//     if (!isServerFound) {
//       attempts++;
//       Serial.printf("[UDP] Попытка %d/10...\n", attempts);
//       delay(1000);
//     }
//   }
//   udp.stop();
  
//   if (!isServerFound) {
//     Serial.println("[UDP] Сервер не найден. Работаю в автономном режиме.");
//   }
// }

// void initUDP() {
//   udp.begin(8888); 
//   Serial.println("[UDP] Порт 8888 открыт");
// }

