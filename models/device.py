from core.db_config import db          # Импортируем объект базы данных из настроек
from datetime import datetime          # Импортируем работу со временем

class Device(db.Model):                # Создаем модель (таблицу) "Устройства"
    __tablename__ = 'devices'          # Явное имя таблицы в базе данных SQL

    # Столбец ID: используем ID самого модуля ESP8266 (ID от ESP8266 (например, 36), не автоинкремент!)
    id = db.Column(db.Integer, primary_key=True) 
    # Столбец для понятного имени (например, "Кухня"), может быть пустым
    name = db.Column(db.String(100), nullable=True)
    # Время первого появления или последнего обновления (по умолчанию - сейчас)
    last_seen = db.Column(db.DateTime, default=datetime.now)
    # Время изменения настроек (автоматически обновляется при любом edit записи)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Функция для смены имени устройства (бизнес-логика). Переименование с валидацией
    def update_name(self, new_name):
        # Простая проверка: если имя пустое или короче 2 символов — отказ
        if not new_name or len(new_name) < 2:
            return False, "Имя слишком короткое"
        
        self.name = new_name           # Присваиваем новое имя
        db.session.commit()            # Сохраняем изменение в файл базы данных
        return True, "Имя обновлено"   # Возвращаем успех

    @staticmethod
    def register_sensor(s_id):
        """Проверяет наличие модуля в базе, если его нет — создает и обновляет время его активности"""
        # Ищем устройство в таблице по его уникальному ID
        device = Device.query.get(s_id)
        
        if not device:                 # Если такого ID еще нет в базе:
            # Создаем новую запись с дефолтным именем "Датчик №..."
            device = Device(id=s_id, name=f"Датчик {s_id}")
            db.session.add(device)     # Ставим в очередь на добавление
        
        device.last_seen = datetime.now() # Обновляем время "последнего визита" при каждом MQTT-сообщении
        
        db.session.commit()            # Фиксируем изменения (новое устройство или новое время)
        return device                  # Возвращаем объект устройства для дальнейшей работы