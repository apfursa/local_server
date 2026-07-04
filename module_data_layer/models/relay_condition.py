"""
Модель для хранения условий управления реле.
Одна строка = одно условие (базовое или на период времени).
Путь: D:\Moy_Server\module_data_layer\models\relay_condition.py
"""

from module_data_layer.core.db_config import db


class RelayCondition(db.Model):
    __tablename__ = 'relay_conditions'

    id        = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Ссылка на реле (составной внешний ключ)
    modul_id  = db.Column(db.Integer, nullable=False, index=True)
    relay_pin = db.Column(db.String(5), nullable=False, index=True)

    # Датчик — источник данных для условия
    sensor_id = db.Column(db.Integer, nullable=False)
    data_type = db.Column(db.String(20), nullable=False)

    # Условие сравнения: ">", "<", "=", ">=", "<=", "!="
    operator  = db.Column(db.String(2), nullable=False, default='>')

    # Пороговое значение
    value     = db.Column(db.Float, nullable=False, default=0.0)

    # Результат при выполнении условия: 0 = выкл, 1 = вкл
    result    = db.Column(db.Integer, nullable=False, default=1)

    # Временной диапазон (NULL = базовое условие, без периода)
    time_start = db.Column(db.String(5), nullable=True)  # "08:00"
    time_end   = db.Column(db.String(5), nullable=True)  # "20:00"

    # Принудительное состояние реле для периода (без условий)
    # NULL = управляется условиями, 0 = выкл, 1 = вкл
    schedule_result = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        period = f" [{self.time_start}-{self.time_end}]" if self.time_start else " [база]"
        return (f"<RelayCondition modul={self.modul_id} pin={self.relay_pin}"
                f" sensor={self.sensor_id}/{self.data_type}"
                f" {self.operator}{self.value} → {'вкл' if self.result else 'выкл'}{period}>")
