
#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

extern String serverHost;
extern const int serverPort;
extern const char *nameAP;
extern unsigned long wifiDisconnectStartTime;
extern const unsigned long MAX_WIFI_DISCONNECT_TIME;
extern unsigned long lastWifiLogTime;
extern int serverErrorCounter;
extern const int MAX_SERVER_ERRORS;
extern const int powerPin;
extern unsigned long powerLossStartTime;
extern const unsigned long MAX_POWER_LOSS_TIME;
extern unsigned long lastPowerLogTime;
extern bool powerAlarmTriggered;
extern int ringCounter;
extern String currentAdminPhone;
extern bool isServerFound;
extern bool isCalling;
extern unsigned long callStartTime;
extern String httpResponse;


const int HTTP_REQUEST_TIMEOUT = 3000; // Таймаут в миллисекундах

#endif