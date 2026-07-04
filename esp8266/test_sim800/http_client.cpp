#include "http_client.h"
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ESP8266WiFi.h>
#include "config.h"
#include "gsm.h"

HTTPState httpState = HTTP_IDLE;
String httpResponse = "";
static String pendingUrl = "";
static String pendingBody = "";
static bool isPost = false;

void startPostRequest(String path, String body) {
    yield();
    if (WiFi.status() != WL_CONNECTED) return;
    
    pendingUrl = "http://" + serverHost + path;
    pendingBody = body;
    isPost = true;
    httpState = HTTP_WAITING;
}

void startGetRequest(String path, String params) {
    yield();
    if (WiFi.status() != WL_CONNECTED) return;
    
    pendingUrl = "http://" + serverHost + path + (params.length() > 0 ? "?" + params : "");
    isPost = false;
    httpState = HTTP_WAITING;
}

void handleHttp() {
    yield();
    if (httpState != HTTP_WAITING) return;

    WiFiClient client;
    HTTPClient http;
    
    http.begin(client, pendingUrl);
    http.setTimeout(HTTP_REQUEST_TIMEOUT);
    
    int code;
    if (isPost) {
        http.addHeader("Content-Type", "application/json");
        code = http.POST(pendingBody);
    } else {
        code = http.GET();
    }
    
    if (code > 0) {
        httpResponse = http.getString();
        httpState = HTTP_DONE;
    } else {
        httpState = HTTP_ERROR;
    }
    http.end();
}