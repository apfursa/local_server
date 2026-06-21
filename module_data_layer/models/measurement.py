from datetime import datetime
from module_data_layer.core.db_config import db

class Measurement(db.Model):
    __tablename__ = 'measurements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    data_type = db.Column(db.String(20), nullable=False) # Сюда запишется и 'temp1', и 'abc', и всё что угодно
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Флаг синхронизации с облаком: 0 - не отправлено, 1 - успешно отправлено
    is_synced = db.Column(db.Integer, default=0, index=True, nullable=False)

    def __repr__(self):
        return f"<Measurement ID={self.id}, Sensor={self.sensor_id}, {self.data_type}={self.value}>"

    @classmethod
    def add_record(cls, s_id: int, val: float, d_type: str):
        """
        Добавляет новую запись физического измерения в лог.

        :param s_id: ID устройства
        :param val: Физическое значение параметра (float)
        :param d_type: Системное имя типа данных (строка)
        """
        record = cls(
            sensor_id=s_id,
            value=float(val),
            data_type=d_type,         # Молча сохраняем пришедший тип (например, 'temp2' или 'volt')
            timestamp=datetime.now(),
            is_synced=0
        )
        db.session.add(record)
        db.session.commit()
        return record
