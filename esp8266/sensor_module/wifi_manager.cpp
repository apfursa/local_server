#include "wifi_manager.h"
#include <ESP8266WiFi.h>
#include <WiFiManager.h>
#include "config.h"

void setupWiFi() {
    WiFiManager wm;
    wm.setConfigPortalTimeout(120);
    if (!wm.autoConnect(nameAP)) {
        Serial.println("Не удалось подключиться, перезагрузка...");
        delay(3000);
        ESP.restart();
    }
    Serial.println("Wi-Fi Успешно подключен!");
}
