"""
Модель динамических временных периодов (уставок) для датчиков.
"""

from datetime import datetime
from module_data_layer.core.db_config import db


class DeviceSchedule(db.Model):
    __tablename__ = 'device_schedules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sensor_id = db.Column(db.Integer, nullable=False, index=True)
    data_type = db.Column(db.String(20), nullable=False, index=True)
    time_start = db.Column(db.String(5), nullable=False)
    time_end = db.Column(db.String(5), nullable=False)

    # 4 новые уставки вместо старых param_min/max
    alarm_min = db.Column(db.Float, nullable=True)
    relay_min = db.Column(db.Float, nullable=True)
    relay_max = db.Column(db.Float, nullable=True)
    alarm_max = db.Column(db.Float, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=True)

    def __repr__(self):
        return f"<DeviceSchedule ID={self.id}, Sensor={self.sensor_id} ({self.data_type})>"

    @classmethod
    def save_schedules_for_sensor(cls, s_id: int, d_type: str, periods_list: list):
        try:
            cls.query.filter_by(sensor_id=s_id, data_type=d_type).delete()
            for period in periods_list:
                new_period = cls(
                    sensor_id=s_id,
                    data_type=d_type,
                    time_start=period['time_start'],
                    time_end=period['time_end'],
                    # Раскладываем новые поля из пришедшего списка
                    alarm_min=float(period['alarm_min']) if period.get('alarm_min') is not None else None,
                    relay_min=float(period['relay_min']) if period.get('relay_min') is not None else None,
                    relay_max=float(period['relay_max']) if period.get('relay_max') is not None else None,
                    alarm_max=float(period['alarm_max']) if period.get('alarm_max') is not None else None
                )
                db.session.add(new_period)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e