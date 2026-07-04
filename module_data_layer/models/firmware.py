"""
Модель для хранения истории прошивок устройств.
Путь: D:\Moy_Server\module_data_layer\models\firmware.py

Каждая загруженная прошивка — отдельная запись.
Активная прошивка помечается is_active=1.
Для отката достаточно переключить is_active на нужную запись.
"""

from datetime import datetime
from module_data_layer.core.db_config import db


class Firmware(db.Model):
    __tablename__ = 'firmware'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ID устройства (совпадает с sensor_id в таблице devices)
    sensor_id = db.Column(db.Integer, nullable=False, index=True)

    # Версия прошивки
    version = db.Column(db.Integer, nullable=False)

    # Имя файла прошивки (например: sensor39_v4.bin)
    filename = db.Column(db.String(100), nullable=False)

    # Дата загрузки прошивки на сервер
    uploaded_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Необязательное описание изменений
    description = db.Column(db.String(255), nullable=True)

    # Активная прошивка для этого устройства (1 = активная, 0 = архив)
    is_active = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        active = " [ACTIVE]" if self.is_active else ""
        return f"<Firmware sensor_id={self.sensor_id} v{self.version}{active}>"
