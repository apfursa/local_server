import paho.mqtt.client as mqtt                # Подключаем библиотеку для работы по протоколу MQTT
from models.device import Device               # Импортируем модель "Устройство" для регистрации датчиков
from models.measurement import Measurement     # Импортируем модель "Замер" для записи данных
import json                                    # Подключаем работу с форматом JSON (пригодится для сложных данных)

# Настройки твоего MQTT-брокера (программы, которая ловит сигналы от ESP8266)
MQTT_BROKER = "127.0.0.1"                      # Адрес сервера (локальный хост, где запущен Mosquitto)
# MQTT_BROKER = "localhost"                    # Или IP твоего брокера
MQTT_PORT = 1883                               # Стандартный порт для MQTT без шифрования
MQTT_TOPIC = "sensors/#"                       # Шаблон темы: решетка означает "слушать всё, что начинается на sensors/"

# Функция, которая срабатывает ПРИ ПОДКЛЮЧЕНИИ к брокеру
def on_connect(client, userdata, flags, rc):
    if rc == 0:                                         # Если код ответа (rc) равен 0, значит подключение успешно
        print("MQTT успешно подключен к брокеру")       # Выводим отчет в консоль сервера
        client.subscribe(MQTT_TOPIC)                    # Подписываемся на нашу тему, чтобы начать получать данные
    else:                                               # Если код не 0, значит что-то пошло не так
        print(f"Ошибка подключения к MQTT, код: {rc}")  # Выводим код ошибки (например, неверный пароль)

# Функция, которая срабатывает ПРИ ПОЛУЧЕНИИ каждого сообщения
def on_message(client, userdata, msg):
    # Импортируем наше приложение Flask прямо здесь
    # Это нужно, чтобы база данных знала, куда записывать данные, и не было "цикличной ошибки"
    from run import app 
    
    # Разбиваем адрес темы по слэшу. Тема "sensors/39" станет списком: ['sensors', '39']
    parts = msg.topic.split('/')
    
    # Проверяем структуру: 1. Начинается с sensors, 2. Всего 2 части.
    if len(parts) == 2 and parts[0] == 'sensors':
        # Блок "попробуй выполнить": если внутри будет ошибка, программа не вылетит
        try:                     
            sensor_id = int(parts[1])    # Берем вторую часть (ID датчика - это ID ESP8266) и превращаем в целое число

            # Распаковываем JSON: {"light": 500, "temp": 24.0}
            payload = json.loads(msg.payload.decode().strip())
        
            # Входим в "контекст приложения" Flask, чтобы база данных разрешила запись
            with app.app_context():
                # 1. Проверяем, есть ли такой датчик в базе. Если нет — создаем его.
                Device.register_sensor(sensor_id)
                
                # 2. Перебираем все ключи в JSON (temp, light и т.д.)
                for key, value in payload.items():
                    # Пропускаем "time", если ESP его шлет, так как сервер ставит свое время
                    if key == "time":
                        continue
                    
                    # Записываем каждое значение под своим типом
                    Measurement.add_record(sensor_id, float(value), d_type=key)
                    print(f"[background/mqtt:on_message] Модуль {sensor_id} прислал {key}: {value}")
            
        except Exception as e:   # Если случилась любая другая ошибка (например, база данных занята)
            print(f"[background/mqtt:on_message] Критическая ошибка: {e}")


# Главная функция, которая запускает весь этот механизм
def start_mqtt():
    # Создаем "клиента" — это как бы виртуальный приемник
    client = mqtt.Client()
    
    # Привязываем наши функции выше к событиям этого приемника
    client.on_connect = on_connect             # Когда подключится — выполни on_connect
    client.on_message = on_message             # Когда придет письмо — выполни on_message
    
    try:
        # Пытаемся соединиться с брокером (Mosquitto)
        # 60 — это время в секундах, через которое клиент проверяет, не оборвалась ли связь
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # ЗАПУСК ФОНОВОГО ПОТОКА. 
        # Это создает отдельный "моторчик", который крутится сам по себе и не мешает сайту работать.
        client.loop_start() 
        
        print("Поток MQTT запущен...") # Сообщаем, что всё окей
        
    except Exception as e:       # Если, например, Mosquitto не запущен, сработает этот блок
        print(f"Не удалось запустить MQTT: {e}")