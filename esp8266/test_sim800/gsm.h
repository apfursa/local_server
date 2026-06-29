#ifndef GSM_H
#define GSM_H

#include <Arduino.h>

// Определяем перечисление ОДИН РАЗ здесь
enum GsmInitStep { 
    INIT_IDLE, 
    INIT_CHECK_AT,
    INIT_WAIT_AT, 
    INIT_CHECK_CREG, 
    INIT_CMGF, 
    INIT_CNMI, 
    INIT_CLIP, 
    INIT_DONE 
};

// Объявляем переменные как extern
extern GsmInitStep initStep;
extern int ringCount;
extern unsigned long muteUntilAll;
extern String lastSmsContent;
extern bool isCalling;

// Прототипы функций
void gsm_begin(long baud);
void handleGsmInit();
bool gsm_handle();
void gsm_call(String number);
void gsm_clearBuffer();

#endif