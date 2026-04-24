from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models.device import Device
from models.measurement import Measurement
from models.setting import Setting
from core.db_config import db

# первый коммит

# Создаем Blueprint для группировки путей (rout) нашего API
api_bp = Blueprint('api', __name__)

@api_bp.route('/api/latest')
def get_latest_data():
    # 1. Получаем список всех зарегистрированных устройств из таблицы Device
    modules = Device.query.all()
    
    # 2. Создаем пустой список, куда будем складывать финальные данные для фронтенда
    data_for_frontend = [] 
    
    # 3. Фиксируем текущее время сервера, чтобы понять, как давно датчик присылал данные
    current_time = datetime.now()

    # Начало цикла по всем устройствам (например: ESP №39, ESP №40)
    for modul in modules:
        # 4. Выясняем, какие ТИПЫ данных присылало это конкретное устройство.
        # Запрос ищет уникальные (distinct) значения в колонке data_type (например: 'temp', 'hum')
        distinct_types = db.session.query(Measurement.data_type).filter_by(sensor_id = modul.id).distinct().all()
        
        # Вложенный цикл по типам данных (если ESP шлет и температуру, и влажность)
        # Ожидается, что каждый элемент в distinct_types является кортежем из одного элемента, 
        # запятая (sensor_type,) позволяет вытащить этот элемент и присвоить его переменной sensor_type
        for (sensor_type,) in distinct_types:
            # 5. Находим САМУЮ ПОСЛЕДНЮЮ запись для этого датчика и этого типа данных.
            # Сортируем по ID в обратном порядке (desc) и берем первую запись
            last_entry = Measurement.query.filter_by(sensor_id = modul.id, data_type = sensor_type).order_by(Measurement.id.desc()).first()
            
            # Если запись найдена (датчик хоть раз что-то прислал)
            if last_entry:
                # 6. Ищем индивидуальные настройки (пороги min/max) для этого датчика и типа данных
                sett = Setting.query.filter_by(sensor_id = modul.id, data_type = sensor_type).first()

                # Сначала берем имя из настроек датчика, если нет - из устройства, если нет - дефолт
                display_name = sett.name if (sett and sett.name) else (modul.name or f"Датчик {modul.id}")
                
                # 7. Считаем "возраст" последнего замера в минутах
                diff = (current_time - last_entry.timestamp).total_seconds() / 60
                
                # 8. Определяем границы. Если в таблице Setting ничего нет, ставим очень широкие лимиты
                min_limit = sett.min if sett else -99.0
                max_limit = sett.max if sett else 99.0

                # --- ЛОГИКА ЦВЕТА И СТАТУСА ---
                # Если данных нет больше 5 минут — красим в черный (датчик "отвалился")
                if diff >= 5: 
                    v_color = "#000000" 
                # Если значение выше нормы — красный
                elif last_entry.value > max_limit: 
                    v_color = "#dc3545" 
                # Если значение ниже нормы — синий
                elif last_entry.value < min_limit: 
                    v_color = "#007bff" 
                # Если всё в порядке — зеленый
                else: 
                    v_color = "#28a745"

                # 9. Собираем всё в один аккуратный словарь и добавляем в список
                data_for_frontend.append({
                    "id": modul.id,                                     # ID модуля (например, 39)
                    "type": sensor_type,                                 # Тип (temp или hum)
                    "name": display_name,                           # Имя из базы или номер, если не назван
                    "value": last_entry.value,                          # Само значение (число)
                    "color": v_color,                               # Цвет, который мы вычислили выше
                    "time": last_entry.timestamp.strftime('%H:%M'),      # Красивое время замера
                    "ui_type": sett.ui_type if sett else 'numeric'  # ОТПРАВЛЯЕМ ТИП
                })
    
    # 10. Превращаем список словарей в формат JSON и отправляем в браузер
    return jsonify(data_for_frontend)

@api_bp.route('/api/history/<int:sensor_id>')
def sensor_history(sensor_id):
    sensor_type = request.args.get('type', default='temp')
    
    # Получаем количество часов из запроса (по умолчанию 24)
    try:
        hours = int(request.args.get('hours', default=24))
    except ValueError:
        hours = 24

    # Вычисляем точку во времени, от которой берем данные
    start_time = datetime.now() - timedelta(hours=hours)
    
    # Запрос к базе: фильтруем по ID, типу и ВРЕМЕНИ (больше start_time)
    # Убедись, что колонка называется timestamp, иначе поправь имя
    history = Measurement.query.filter(
        Measurement.sensor_id == sensor_id,
        Measurement.data_type == sensor_type,
        Measurement.timestamp >= start_time
    ).order_by(Measurement.timestamp.asc()).all() # Сразу сортируем по возрастанию
    
    sett = Setting.query.filter_by(sensor_id=sensor_id, data_type = sensor_type).first()
    db_min = sett.min if (sett and sett.min is not None) else -50
    db_max = sett.max if (sett and sett.max is not None) else 50
    
    return jsonify({
        "labels": [m.timestamp.strftime('%H:%M') for m in history],
        "values": [m.value for m in history],
        "limits": {"min": db_min, "max": db_max}
    })