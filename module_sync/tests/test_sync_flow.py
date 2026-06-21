"""
Локальный автоматический тест для проверки буферизации и фиксации флагов синхронизации.
"""

import unittest
import json
from flask import Flask
from module_data_layer.core.db_config import db
from module_data_layer.models.device import Device
from module_data_layer.models.measurement import Measurement
from module_sync.controllers.sync_controller import sync_bp


class TestSyncFlowLogic(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)
        self.app.register_blueprint(sync_bp, url_prefix='/api')
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            Device.register_sensor(10)

            # Создаем одну запись "грязную" (0), и одну уже "синхронизированную" (1)
            Measurement.add_record(s_id=10, val=45.2, d_type='hum')

            synced_meas = Measurement(sensor_id=10, value=22.1, data_type='temp', is_synced=1)
            db.session.add(synced_meas)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_unsynced_only(self):
        """Проверка, что роут get-unsynced вытаскивает ТОЛЬКО записи со значением флага 0"""
        response = self.client.get('/api/sync/get-unsynced')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data), 1)  # Вторая запись (is_synced=1) должна быть проигнорирована
        self.assertEqual(data[0]['value'], 45.2)

    def test_confirm_sync_switches_flag(self):
        """Проверка, что после подтверждения по ID, флаг в БД переключается в 1"""
        # Сначала узнаем ID нашей несинхронизированной записи
        with self.app.app_context():
            meas = Measurement.query.filter_by(is_synced=0).first()
            target_id = meas.id

        # Отправляем POST запрос на подтверждение этого ID.
        # Используем аргумент json= вместо ручного json.dumps и contentType,
        # чтобы избежать ошибок с регистром символов во Werkzeug/Flask.
        payload = {"ids": [target_id]}
        response = self.client.post('/api/sync/confirm', json=payload)
        self.assertEqual(response.status_code, 200)

        # Проверяем, что в базе больше нет несинхронизированных строк
        with self.app.app_context():
            unsynced_count = Measurement.query.filter_by(is_synced=0).count()
            self.assertEqual(unsynced_count, 0)


if __name__ == '__main__':
    unittest.main()