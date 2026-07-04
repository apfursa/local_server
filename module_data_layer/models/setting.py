"""
Модель пользовательских настроек, локаций и аварийных порогов для каждого параметра датчика.
Использует составной первичный ключ (sensor_id + data_type).
"""

from datetime import datetime
from module_data_layer.core.db_config import db


class Setting(db.Model):
    __tablename__ = 'settings'

    sensor_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), primary_key=True)
    data_type = db.Column(db.String(20), primary_key=True)

    # Пользовательские метаданные для отображения на фронтенде
    name = db.Column(db.String(100), nullable=True)
    ui_type = db.Column(db.String(20), default='numeric', nullable=False)
    # location = db.Column(db.String(50), default='Улица', nullable=False)
    # group = db.Column(db.String(50), default='Климат', nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    # Добавляем "отношения", чтобы легко обращаться к объекту: sensor.location.name
    location = db.relationship('Category', foreign_keys=[location_id])
    group = db.relationship('Category', foreign_keys=[group_id])

    # Аварийные границы безопасной работы
    # min = db.Column(db.Float, default=18.0, nullable=False)
    # max = db.Column(db.Float, default=28.0, nullable=False)

    # min = db.Column(db.Float, nullable=True)
    # max = db.Column(db.Float, nullable=True)

    # Аварийные границы (для сервера) и рабочие уставки реле (для модуля)
    alarm_min = db.Column(db.Float, nullable=True)
    relay_min = db.Column(db.Float, nullable=True)
    relay_max = db.Column(db.Float, nullable=True)
    alarm_max = db.Column(db.Float, nullable=True)
    offline_timeout = db.Column(db.Integer, default=5, nullable=False)

    mute_until = db.Column(db.DateTime, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    # Мягкое удаление из интерфейса (0 - активен, 1 - скрыт)
    is_deleted = db.Column(db.Integer, default=0, nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=True)

    def __repr__(self):
        return f"<Setting Sensor={self.sensor_id}, Type='{self.data_type}', Location='{self.location}'>"

    def is_in_alarm(self):
        """Проверяет, находится ли текущее значение датчика в состоянии ГЛОБАЛЬНОЙ аварии."""
        if self.current_value is None:
            return False

        # Проверяем нижнюю аварийную границу (если она задана)
        if self.alarm_min is not None and self.current_value < self.alarm_min:
            return True

        # Проверяем верхнюю аварийную границу (если она задана)
        if self.alarm_max is not None and self.current_value > self.alarm_max:
            return True

        return False