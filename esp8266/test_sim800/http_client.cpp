#include "http_client.h"
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ESP8266WiFi.h>
#include "config.h"
#include "gsm.h"

HTTPState httpState = HTTP_IDLE;
String httpResponse = "";
static String pendingUrl = "";

void startGetRequest(String path, String params) {
    yield();
    if (WiFi.status() != WL_CONNECTED) return;
    
    pendingUrl = "http://" + serverHost + path + (params.length() > 0 ? "?" + params : "");
    httpState = HTTP_WAITING;
}

void handleHttp() {
    yield();
    if (httpState != HTTP_WAITING) return;

    WiFiClient client;
    HTTPClient http;
    
    http.begin(client, pendingUrl);
    http.setTimeout(HTTP_REQUEST_TIMEOUT);
    
    int code = http.GET();
    if (code > 0) {
        httpResponse = http.getString();
        httpState = HTTP_DONE;
    } else {
        httpState = HTTP_ERROR;
    }
    http.end();
}