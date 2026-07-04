"""
Модель для хранения реле и их настроек.
Путь: D:\Moy_Server\module_data_layer\models\relay.py
"""

from module_data_layer.core.db_config import db


class Relay(db.Model):
    __tablename__ = 'relay'

    # Составной первичный ключ: ID модуля + пин реле
    modul_id  = db.Column(db.Integer, primary_key=True)
    relay_pin = db.Column(db.String(5), primary_key=True)  # "D1", "D2" и т.д.

    # Метаданные для отображения
    name      = db.Column(db.String(100), nullable=True)
    ui_type   = db.Column(db.String(20), default='relay', nullable=False)

    # Локация и группа (как у датчиков)
    location_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    group_id    = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    location    = db.relationship('Category', foreign_keys=[location_id])
    group       = db.relationship('Category', foreign_keys=[group_id])

    # Контроль связи
    offline_timeout = db.Column(db.Integer, default=5, nullable=False)

    # Режим управления: "force" = принудительно, "conditions" = по условиям
    mode  = db.Column(db.String(20), default='force', nullable=False)

    # Текущее состояние: 0 = выкл, 1 = вкл
    state = db.Column(db.Integer, default=0, nullable=False)

    # Порядок отображения и мягкое удаление
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_deleted = db.Column(db.Integer, default=0, nullable=False)

    # Время последнего обращения модуля
    last_seen = db.Column(db.DateTime, nullable=True)

    # Связь с условиями
    conditions = db.relationship(
        'RelayCondition',
        foreign_keys='[RelayCondition.modul_id, RelayCondition.relay_pin]',
        primaryjoin='and_(Relay.modul_id == RelayCondition.modul_id, '
                    'Relay.relay_pin == RelayCondition.relay_pin)',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Relay modul={self.modul_id} pin={self.relay_pin} state={self.state}>"
