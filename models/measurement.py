from core.db_config import db
from datetime import datetime

class Measurement(db.Model):
    __tablename__ = 'measurements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    # сюда запишем 'temp', 'light', 'hum' и т.д.
    data_type = db.Column(db.String(20), nullable=False, index=True) 
    timestamp = db.Column(db.DateTime, default=datetime.now)
    # 0 - только на локальном сервере, 1 - уже отправлено на удаленный сервер
    is_synced = db.Column(db.Integer, default=0, index=True)

    @staticmethod
    def add_record(s_id, val, d_type):
        new_record = Measurement(sensor_id=s_id, value=val, data_type=d_type)
        db.session.add(new_record)
        db.session.commit()
        return new_record