// #include "GSM.h"
// #include <SoftwareSerial.h>

// // Эти переменные ВИДНЫ ТОЛЬКО ВНУТРИ ЭТОГО ФАЙЛА
// static SoftwareSerial gsmSerial(14, 12);
// static String buffer = ""; 
// static int step = 0; // Состояние нашего автомата

// // А эти переменные ВИДНЫ ВСЕМ (через extern в .h)
// bool gsm_ringDetected = false;
// String gsm_lastCaller = "";

// void gsm_begin(long baud) {
//     gsmSerial.begin(baud);
// }

// void gsm_handle() {
//     // Читаем данные из модема
//     while (gsmSerial.available()) {
//         char c = (char)gsmSerial.read();
//         buffer += c;
//     }
    
//     // НАШ АВТОМАТ (switch внутри функции)
//     switch(step) {
//         case 0: // Ждем
//             if (buffer.indexOf("RING") != -1) {
//                 gsm_ringDetected = true;
//                 buffer = "";
//             }
//             break;
            
//         case 1: // Например, логика обработки звонка
//             // ...
//             break;
//     }
// }

// void gsm_call(String number) {
//     gsmSerial.print("ATD");
//     gsmSerial.print(number);
//     gsmSerial.println(";");
// }