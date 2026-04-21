import paho.mqtt.client as mqtt 
import json 
import time 
import random 

# 1. НАСТРОЙКИ
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
SENSOR_ID_1 = 39 
SENSOR_ID_2 = 40 

client = mqtt.Client()

def generate_and_send():
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        print(f"Запуск эмуляции для модулей {SENSOR_ID_1} и {SENSOR_ID_2}...")

        # Настройки числовых датчиков
        CONFIG = {
            "temp1": {"min": 70.0, "max": 80.0, "step": 0.5},
            "temp2": {"min": 20.0, "max": 25.0, "step": 0.2},
            "hum":   {"min": 40.0, "max": 80.0, "step": 1.0},
            "volt":  {"min": 4.0,  "max": 5.0,  "step": 0.05}
        }

        current_values = {k: v["min"] for k, v in CONFIG.items()}
        directions = {k: 1 for k in CONFIG}

        def update_val(key):
            cfg = CONFIG[key]
            change = cfg["step"] * directions[key]
            current_values[key] = round(current_values[key] + change, 2)
            if current_values[key] >= cfg["max"]: directions[key] = -1
            elif current_values[key] <= cfg["min"]: directions[key] = 1
            return current_values[key]

        while True:
            for sensor_id in [SENSOR_ID_1, SENSOR_ID_2]:
                # ЛОГИКА БИНАРНОГО ДАТЧИКА (Протечка)
                # random.random() дает число от 0 до 1. 
                # Если оно меньше 0.2 (20% шанс) — шлем 1.0 (протечка)
                leak_status = 1.0 if random.random() < 0.2 else 0.0

                payload = {
                    "temp1": update_val("temp1"),
                    "temp2": update_val("temp2"),
                    "hum":   update_val("hum"),
                    "volt":  update_val("volt"),
                    "leak":  leak_status  # НОВЫЙ ДАТЧИК
                }

                topic = f"sensors/{sensor_id}"
                client.publish(topic, json.dumps(payload))
                
                status_text = "!!! ПРОТЕЧКА !!!" if leak_status > 0.5 else "Сухо"
                print(f" [OK] {topic}: {payload} ({status_text})")

            # Сделаем паузу поменьше для тестов, например 10 секунд, 
            # чтобы быстрее увидеть смену иконок
            time.sleep(60)

    except KeyboardInterrupt:
        print("\nЭмуляция остановлена.")
        client.disconnect()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    generate_and_send()