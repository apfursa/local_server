"""
Сквозной интеграционный тест всего проекта (E2E).
Проверяет цепочку: Запись в БД -> Бизнес-логика API -> Выдача корректного JSON,
а также доступность статических файлов фронтенда.
"""

import os
import unittest
import json
import re
from datetime import datetime

# Импортируем нашу боевую фабрику
from run import create_app
# База данных и модели из модуля данных строго по твоей структуре
from module_data_layer.core.db_config import db
from module_data_layer.models.device import Device
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.setting import Setting


class FullSystemIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        """Создаем чистое изолированное окружение перед тестом."""
        self.app = create_app()

        # КРИТИЧНО ДЛЯ FLASK 3.x: Принудительно меняем конфиг ДО создания таблиц
        self.app.config.update({
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True
        })

        self.client = self.app.test_client()

        # Создаем чистые таблицы в оперативной памяти компьютера
        with self.app.app_context():
            db.create_all()
            self._fill_test_data()

    def tearDown(self):
        """Очищаем память после теста."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _fill_test_data(self):
        """Заполняем базу данных согласно структуре твоих моделей."""
        Device.register_sensor(1)

        t_set = Setting(
            sensor_id=1,
            data_type="temp",
            min=18.0,
            max=26.0,
            location="Квартира 1",
            group="Жилые",
            name="Датчик температуры"
        )
        db.session.add(t_set)
        Measurement.add_record(s_id=1, val=22.4, d_type='temp')
        db.session.commit()

    def test_dashboard_data_flow(self):
        """Проверяем сквозной проход данных: от замера в БД до выдачи в API /api/latest."""
        response = self.client.get("/api/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        json_data = json.loads(response.data.decode("utf-8"))
        self.assertTrue(len(json_data) > 0)

        sensor_item = next((item for item in json_data if item["uid"] == "1_temp"), None)
        self.assertIsNotNone(sensor_item)
        self.assertEqual(sensor_item["sensor_id"], 1)
        self.assertEqual(sensor_item["type"], "temp")
        self.assertEqual(sensor_item["data"]["value"], 22.4)

    def test_static_assets_availability(self):
        """Проверяем, что главная страница успешно отдает подключенную статику (JS/CSS)."""
        # 1. Загружаем главную страницу
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200, "Главная страница не доступна")

        html_content = response.data.decode("utf-8")

        # 2. Извлекаем регулярным выражением все пути к локальной статике (/static/...)
        static_paths = re.findall(r'href="(/static/[^"]+)"|src="(/static/[^"]+)"', html_content)
        # Очищаем список от пустых совпадений групп регулярки
        paths_to_check = [path[0] if path[0] else path[1] for path in static_paths]

        self.assertTrue(len(paths_to_check) > 0, "На главной странице не найдено подключенных локальных файлов статики")

        # 3. Эмулируем запрос к каждому файлу статики и проверяем, что нет 404 ошибок
        for path in paths_to_check:
            asset_response = self.client.get(path)
            self.assertEqual(
                asset_response.status_code,
                200,
                f"Критическая ошибка: статический файл {path} вернул статус {asset_response.status_code} вместо 200 OK!"
            )


if __name__ == "__main__":
    unittest.main()