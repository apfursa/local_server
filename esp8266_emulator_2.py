# Импортируем библиотеку для работы с MQTT. 
# Если её нет, установи через: pip install paho-mqtt
import paho.mqtt.client as mqtt 

# Библиотека для превращения словаря Python в строку JSON
import json 

# Библиотека для пауз (таймеров)
import time 

# Библиотека для генерации случайных чисел (чтобы данные в таблице "жили")
import random 

# 1. НАСТРОЙКИ
MQTT_BROKER = "127.0.0.1"  # Адрес твоего локального Mosquitto
MQTT_PORT = 1883           # Стандартный порт
SENSOR_ID_1 = 39             # ID модуля, который мы тестируем
SENSOR_ID_2 = 40             # ID модуля, который мы тестируем

# Создаем объект "клиента" (виртуальное устройство)
client = mqtt.Client()

def generate_and_send():
    try:
        # Подключаемся к брокеру
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        print(f"Начинаю эмуляцию данных для модуля {SENSOR_ID_1}...")
        print("Нажми Ctrl+C, чтобы остановить.")

        # Настройки диапазонов (мин, макс, шаг изменения)
        CONFIG = {
            "temp1": {"min": 70.0, "max": 80.0, "step": 0.5},
            "temp2": {"min": 20.0, "max": 25.0, "step": 0.2},
            "hum":   {"min": 40.0, "max": 80.0, "step": 1.0},
            "volt":  {"min": 4.0,  "max": 5.0,  "step": 0.05}
        }

        # Текущие значения (стартуем с минимума)
        current_values = {k: v["min"] for k, v in CONFIG.items()}
        # Направления (1 - растет, -1 - падает)
        directions = {k: 1 for k in CONFIG}

        def update_val(key):
            """Логика изменения значения: туда-обратно"""
            cfg = CONFIG[key]
            # Добавляем шаг с небольшим рандомом, чтобы не было слишком "роботизировано"
            change = cfg["step"] * directions[key]
            current_values[key] = round(current_values[key] + change, 2)

            # Проверяем границы
            if current_values[key] >= cfg["max"]:
                directions[key] = -1
            elif current_values[key] <= cfg["min"]:
                directions[key] = 1
            
            return current_values[key]

        print("Запуск эмуляции: данные растут до максимума и падают до минимума...")

        # Запускаем бесконечный цикл, чтобы ты мог спокойно верстать фронтенд
        while True:
            # # Создаем словарь с данными, имитируя несколько датчиков на одной ESP
            # payload = {
            #     "temp1": round(random.uniform(60.0, 85.0), 1), # Имитируем горячий котел
            #     "temp2": round(random.uniform(21.0, 24.0), 1), # Имитируем комнатную температуру
            #     "hum":   round(random.uniform(40.0, 55.0), 1), # Влажность
            #     "volt":  round(random.uniform(3.8, 4.2), 2)    # Напряжение аккумулятора
            # }

            # # Формируем топик в формате, который ждет твой background/mqtt.py
            # topic = f"sensors/{SENSOR_ID}"

            # # Превращаем словарь в JSON-строку
            # json_data = json.dumps(payload)

            # # Публикуем (отправляем) данные в брокер
            # client.publish(topic, json_data)

            # print(f" [OK] Отправлено в {topic}: {json_data}")

            # # Ждем 5 секунд перед следующей отправкой, чтобы не спамить в консоль
            # time.sleep(5)

            # Формируем данные для двух датчиков
            # (второй датчик будет чуть-чуть отличаться из-за повторного вызова update)
            for sensor_id in [SENSOR_ID_1, SENSOR_ID_2]:
                payload = {
                    "temp1": update_val("temp1"),
                    "temp2": update_val("temp2"),
                    "hum":   update_val("hum"),
                    "volt":  update_val("volt")
                }

                topic = f"sensors/{sensor_id}"
                client.publish(topic, json.dumps(payload))
                print(f" [OK] {topic}: {payload}")

            # Пауза между итерациями
            time.sleep(60)

            

    except KeyboardInterrupt:
        # Если нажал Ctrl+C — корректно отключаемся
        print("\nЭмуляция остановлена пользователем.")
        client.disconnect()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    generate_and_send()