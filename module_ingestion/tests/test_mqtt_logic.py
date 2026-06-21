"""
Локальный тест для проверки корректности парсинга MQTT-топиков,
валидации входящих JSON-пакетов и вызова методов сохранения в БД.
"""

import unittest
import json
from flask import Flask
from module_data_layer.core.db_config import db
from module_data_layer.models.measurement import Measurement
from module_ingestion.background.mqtt import mqtt_on_message


class MockMqttMessage:
    """Класс-имитатор сетевого пакета библиотеки paho-mqtt."""
    def __init__(self, topic: str, payload: str):
        self.topic = topic
        self.payload = payload.encode('utf-8')


class TestMqttIngestionLogic(unittest.TestCase):
    def setUp(self):
        """Инициализация изолированной среды и чистой структуры БД в памяти."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Очистка памяти."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_valid_json_packet_parsing(self):
        """Проверка успешного парсинга и записи стандартного пакета от ESP8266."""
        raw_json = json.dumps({"temp": 21.3, "hum": 55.4, "time": 1718152430})
        mock_packet = MockMqttMessage("sensors/42", raw_json)

        # Вызываем обработчик напрямую
        mqtt_on_message(self.app, mock_packet)

        with self.app.app_context():
            # ИСПРАВЛЕНО: Запросы переписаны через чистый db.session.query
            records = db.session.query(Measurement).filter_by(sensor_id=42).all()
            self.assertEqual(len(records), 2)

            temp_record = db.session.query(Measurement).filter_by(sensor_id=42, data_type='temp').first()
            hum_record = db.session.query(Measurement).filter_by(sensor_id=42, data_type='hum').first()

            self.assertIsNotNone(temp_record)
            self.assertEqual(temp_record.value, 21.3)
            self.assertIsNotNone(hum_record)
            self.assertEqual(hum_record.value, 55.4)

    def test_invalid_topic_igoration(self):
        """Проверка того, что служба игнорирует левые топики, не ломаясь."""
        raw_json = json.dumps({"temp": 25.0})
        mock_packet = MockMqttMessage("home/kitchen/temperature", raw_json)

        mqtt_on_message(self.app, mock_packet)

        with self.app.app_context():
            # ИСПРАВЛЕНО: Запрос количества строк через сессию
            total_count = db.session.query(Measurement).count()
            self.assertEqual(total_count, 0)


if __name__ == '__main__':
    unittest.main()