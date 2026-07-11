"""
Фоновый сервис для приема данных от контроллеров ESP8266 по протоколу MQTT.
Использует библиотеку paho-mqtt и интегрирует данные в общую СУБД.

[ИЗМЕНЕНО] Полностью возвращена старая логика всеядной шины данных.
Сервер не проверяет типы и метрики на соответствие спецификациям, а молча пишет в базу всё, что прислало железо.
"""

import json
import logging
import threading
import paho.mqtt.client as mqtt

# Настройка логирования для фонового процесса
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def mqtt_on_message(app, msg):
    """
    Внутренний обработчик входящих MQTT-пакетов.
    Обеспечивает модульную структуру и прозрачную запись любых параметров.
    """
    try:
        # Шаг 1: Парсинг топика (ожидается формат "sensors/<id>").
        topic_parts = msg.topic.split('/')
        if len(topic_parts) != 2 or topic_parts[0] != 'sensors':
            return  # Игнорируем топики, не подпадающие под наш стандарт

        sensor_id = int(topic_parts[1])

        # Шаг 2: Декодирование и парсинг полезной нагрузки (JSON)
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)

        # Шаг 3: Импорт моделей из твоей новой модульной структуры (Data Layer)
        # ДОБАВЛЕНО: пути импортов обновлены под модули, как требовалось по задаче
        from module_data_layer.models.device import Device
        from module_data_layer.models.measurement import Measurement

        # Шаг 4: Безопасная запись в БД внутри контекста приложения
        with app.app_context():
            # Регистрируем/обновляем устройство в базе данных
            Device.register_sensor(sensor_id)

            # Перебираем все физические ключи в пакете
            for key, value in data.items():
                if key == 'time':
                    continue  # Игнорируем техническое поле времени

                # ВЕРНУЛИ СТАРУЮ ЛОГИКУ: Полностью убрана жесткая валидация по типам.
                # Больше нет никаких проверок "См. спецификацию". Любой ключ (temp1, abc, xyz) улетает в базу.
                try:
                    # Записываем значение в базу данных под своим именем (key становится d_type)
                    Measurement.add_record(sensor_id, float(value), d_type=key)

                    # ВЕРНУЛИ СТАРЫЙ ВЫВОД: Простая и информативная строка лога о сохранении данных
                    logging.info(f"[MQTT] Сохранено: Датчик {sensor_id} -> {key}: {value}")

                except Exception as e:
                    # Сюда попадем только если упала сама база данных или пришел не float (например, пустая строка)
                    logging.error(f"[MQTT] Ошибка записи параметра '{key}' от датчика {sensor_id}: {e}")

    except Exception as err:  
        logging.error(f"[MQTT] Критическая ошибка при обработке пакета: {err}", exc_info=True)


def _mqtt_worker(app):
    """
    Внутренний рабочий поток MQTT-клиента.
    ДОБАВЛЕНО: Безопасный запуск, совместимый как с Paho-MQTT v1.x, так и с новой v2.x.
    """
    try:
        # Пытаемся инициализировать клиент под новые версии Paho (требующие callback_api_version)
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        # Если библиотека старая, инициализируем классическим способом из твоего старого файла
        client = mqtt.Client()

    # Передаем контекст Flask-приложения внутрь обработчика сообщений
    client.on_message = lambda cl, userdata, msg: mqtt_on_message(app, msg)

    try:
        logging.info("[MQTT] Фоновая служба пытается подключиться к брокеру 127.0.0.1:1883...")
        client.connect("127.0.0.1", 1883, 60)

        # ВЕРНУЛИ СТАРУЮ ЛОГИКУ: Подписываемся на глобальный топик всех датчиков
        client.subscribe("sensors/#")

        # Запускаем бесконечный внутренний цикл
        client.loop_forever()
    except Exception as err:
        logging.critical(f"[MQTT] Сбой фонового потока брокера: {err}. Остановка службы.")


def start_mqtt(app):
    """
    Главная точка интеграции для модульного сервера.
    ДОБАВЛЕНО: Запускает фоновый поток-демон, который работает параллельно с Flask-сервером и не блокирует сайт.
    """
    mqtt_thread = threading.Thread(target=_mqtt_worker, args=(app,), daemon=True)
    mqtt_thread.start()
    logging.info("[MQTT] Фоновый поток успешно инициализирован и запущен.")