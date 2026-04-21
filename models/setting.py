from core.db_config import db          # Подключаем настройки базы данных
from datetime import datetime          # Подключаем работу со временем

class Setting(db.Model):
    __tablename__ = 'settings'         # Имя таблицы в SQLite

    # СОСТАВНОЙ КЛЮЧ: теперь настройки привязаны к паре (ID модуля + Тип данных)
    # Это позволяет хранить разные пороги для температуры и влажности одного модуля
    sensor_id = db.Column(db.Integer, db.ForeignKey('devices.id'), primary_key=True)
    data_type = db.Column(db.String(20), primary_key=True, default='temp')

    name = db.Column(db.String(100), nullable=True)
    # Категория отображения (numeric, leak, door, motion)
    ui_type = db.Column(db.String(20), default='numeric')

    # Те самые лаконичные названия для порогов
    min = db.Column(db.Float, default=18.0)
    max = db.Column(db.Float, default=28.0)
    
    # "Не звонить до..." — время, до которого SIM800 будет молчать (для звонилки)
    mute_until = db.Column(db.DateTime, nullable=True)
    
    # "Очистить историю до..." — дата для автоматической очистки старых записей
    clear_before = db.Column(db.DateTime, nullable=True)
    
    # Метка последнего изменения (автоматически обновляется при сохранении)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Флаг удаления (0 - активна, 1 - удалена)
    is_deleted = db.Column(db.Integer, default=0)

    def set_bounds(self, min_val, max_val):
        """Метод для изменения порогов с проверкой логики"""
        # Если минимум больше максимума — это ошибка, возвращаем отказ
        if min_val >= max_val:
            return False, "Минимум не может быть больше или равен максимуму"
        
        self.min = min_val             # Присваиваем новые значения
        self.max = max_val
        db.session.commit()            # Сохраняем в файл базы данных
        return True, "Пороги сохранены"
