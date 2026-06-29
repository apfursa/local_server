#include "wifi_manager.h"
#include <ESP8266WiFi.h>  // Чтобы работать с самим Wi-Fi модулем
#include <WiFiManager.h>  // Чтобы использовать удобный интерфейс настройки
#include "config.h"

void setupWiFi() {
  WiFiManager wm;
  // Автоматически создает точку доступа "Zvonilka" 
  // если не может подключиться к сохраненному Wi-Fi
  wm.setConfigPortalTimeout(120); 
  if (!wm.autoConnect(nameAP)) {
    Serial.println("Не удалось подключиться, перезагрузка...");
    delay(3000);
    ESP.restart();
  }
  Serial.println("Wi-Fi Успешно подключен!");
}  