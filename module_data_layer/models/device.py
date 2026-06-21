"""
Модель физического устройства (микроконтроллера ESP8266).
"""

from datetime import datetime
from module_data_layer.core.db_config import db


class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с таблицей замеров (для каскадного удаления, если потребуется)
    measurements = db.relationship('Measurement', backref='device', lazy=True, cascade="all, delete-orphan")
    # Связь с таблицей индивидуальных настроек параметров
    settings = db.relationship('Setting', backref='device', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device ID={self.id}, Name='{self.name}'>"

    @classmethod
    def register_sensor(cls, s_id: int):
        """
        Регистрирует устройство в системе при первом обращении
        или обновляет метку времени активности, если устройство уже существует.
        """
        # Современный, безопасный для SQLAlchemy 2.0 синтаксис получения по PK
        device = db.session.get(cls, s_id)

        if not device:
            # Если устройство появилось впервые, даем ему дефолтное системное имя
            device = cls(id=s_id, name=f"Модуль {s_id}", last_seen=datetime.utcnow())
            db.session.add(device)
        else:
            # Если устройство уже есть, обновляем время последней активности
            device.last_seen = datetime.utcnow()

        db.session.commit()
        return device
