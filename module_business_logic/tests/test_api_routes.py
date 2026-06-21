"""
Обновленный локальный тест для проверки роутов API и контроллера настроек settings_controller.
"""

import unittest
import json
from flask import Flask
from module_data_layer.core.db_config import db
from module_data_layer.models.device import Device
from module_data_layer.models.setting import Setting
from module_business_logic.controllers.api_controller import api_bp
from module_business_logic.controllers.settings_controller import settings_bp


class TestBusinessLogicAPI(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)

        # Регистрируем ОБА контроллера в тестовом окружении
        self.app.register_blueprint(api_bp, url_prefix='/api')
        self.app.register_blueprint(settings_bp, url_prefix='/api')

        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            Device.register_sensor(39)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_save_settings_flow(self):
        """Проверка успешного сохранения кастомных порогов через settings_controller"""
        payload = {
            "type": "temp",
            "name": "Теплый пол",
            "location": "Кухня",
            "group": "Отопление",
            "min": 20.0,
            "max": 30.0
        }

        # Делаем POST запрос на сохранение настроек для датчика 39
        response = self.client.post('/api/settings/39',
                                    data=json.dumps(payload),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data)
        self.assertEqual(res_json['status'], 'success')

        # Проверяем, появились ли данные физически в тестовой БД
        with self.app.app_context():
            # ИСПРАВЛЕНО: Запрос через db.session.query вместо .query
            setting = db.session.query(Setting).filter_by(sensor_id=39, data_type='temp').first()
            self.assertIsNotNone(setting)
            self.assertEqual(setting.name, "Теплый пол")
            self.assertEqual(setting.max, 30.0)


if __name__ == '__main__':
    unittest.main()