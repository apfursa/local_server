"""
Локальный автоматический тест для проверки целостности слоя БД,
корректности типов данных и ActiveRecord методов моделей.
"""

import unittest
from flask import Flask
from module_data_layer.core.db_config import db
from module_data_layer.models.device import Device
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.setting import Setting


class TestDatabaseLayer(unittest.TestCase):
    def setUp(self):
        """Создание изолированного контекста Flask и чистой БД в оперативной памяти"""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Очистка ресурсов после выполнения теста"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_device_auto_registration(self):
        """Проверка автоматического создания устройства и обновления last_seen"""
        with self.app.app_context():
            # Проверяем создание "с нуля"
            device = Device.register_sensor(39)
            self.assertIsNotNone(device)
            self.assertEqual(device.name, "Модуль 39")

            # Используем явный запрос через сессию вместо устаревшего стиля .query
            device_count = db.session.query(Device).count()
            self.assertEqual(device_count, 1)

            # Повторный вызов должен обновить существующее, а не плодить дубликаты
            Device.register_sensor(39)
            device_count_after = db.session.query(Device).count()
            self.assertEqual(device_count_after, 1)

    def test_measurement_logging_and_validation(self):
        """Проверка записи физических величин и валидации системных типов"""
        with self.app.app_context():
            # Сначала регистрируем устройство (внешний ключ)
            Device.register_sensor(39)

            # Пишем корректное значение
            meas = Measurement.add_record(s_id=39, val=24.5, d_type='temp')
            self.assertIsNotNone(meas)
            self.assertEqual(meas.value, 24.5)
            self.assertEqual(meas.is_synced, 0)

            # Проверяем защиту от записи некорректного типа данных
            with self.assertRaises(ValueError):
                # Типа 'high_voltage' нет в системном контракте, должен быть отказ
                Measurement.add_record(s_id=39, val=220.0, d_type='high_voltage')

    def test_settings_composite_primary_key(self):
        """Проверка корректной работы составного первичного ключа в настройках"""
        with self.app.app_context():
            Device.register_sensor(39)

            # Создаем настройки для температуры на датчике 39
            set_temp = Setting(sensor_id=39, data_type='temp', name='Погреб Т', min=5.0, max=15.0)
            # Создаем настройки для влажности на ТОМ ЖЕ датчике 39
            set_hum = Setting(sensor_id=39, data_type='hum', name='Погреб В', min=40.0, max=80.0)

            db.session.add(set_temp)
            db.session.add(set_hum)
            db.session.commit()

            # ИСПРАВЛЕНО: Явный запрос через db.session.query, который делает код чистым для PyCharm
            configs = db.session.query(Setting).filter_by(sensor_id=39).all()
            self.assertEqual(len(configs), 2)


if __name__ == '__main__':
    unittest.main()