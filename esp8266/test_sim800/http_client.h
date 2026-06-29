#ifndef HTTP_CLIENT_H
#define HTTP_CLIENT_H

#include <Arduino.h>
#include "config.h"

enum HTTPState { HTTP_IDLE, HTTP_SENDING, HTTP_WAITING, HTTP_DONE, HTTP_ERROR };
extern HTTPState httpState;

void startGetRequest(String path, String params = ""); // Только запускает
void handleHttp(); // Опрашивает состояние

// Объявляем структуру здесь, чтобы она была видна всему проекту
// struct HttpResponse {
//     String content;
//     bool success;
// };

// Эта функция (для отправки данных постом на сервер) принимает WiFiClient как аргумент
// Это делает её независимой от того, как именно мы подключились
// Возвращает ответ структуру (смотри выше)
// HttpResponse sendPostRequestToServer(String path, String data);
// HttpResponse sendGetRequestToServer(String path, String params = "");
bool sendPostRequestToServer(String path, String data);
bool sendGetRequestToServer(String path, String params = "");

#endif