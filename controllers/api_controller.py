from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models.device import Device
from models.measurement import Measurement
from models.setting import Setting
from core.db_config import db

# Создаем Blueprint для группировки путей нашего API
api_bp = Blueprint('api', __name__)


@api_bp.route('/api/latest')
def get_latest_data():
    # 1. Получаем список всех зарегистрированных устройств
    modules = Device.query.all()
    data_for_frontend = []
    current_time = datetime.now()

    for modul in modules:
        # 2. Выясняем, какие ТИПЫ данных присылало это устройство
        distinct_types = db.session.query(Measurement.data_type).filter_by(sensor_id=modul.id).distinct().all()

        for (sensor_type,) in distinct_types:
            # 3. Находим САМУЮ ПОСЛЕДНЮЮ запись для этого датчика и типа данных
            last_entry = Measurement.query.filter_by(sensor_id=modul.id, data_type=sensor_type).order_by(
                Measurement.id.desc()).first()

            if last_entry:
                # 4. Ищем настройки (пороги, локацию, группу) для конкретного сенсора
                sett = Setting.query.filter_by(sensor_id=modul.id, data_type=sensor_type).first()

                # Определяем имя
                display_name = sett.name if (sett and sett.name) else (modul.name or f"Датчик {modul.id}")

                # 5. Считаем "возраст" данных (минуты) и статус онлайн (если нет данных > 5 мин — offline)
                diff_minutes = (current_time - last_entry.timestamp).total_seconds() / 60
                is_online = diff_minutes < 5

                # 6. Достаем пороги, локацию и группу (ставим дефолты, если настроек еще нет в БД)
                min_limit = sett.min if (sett and sett.min is not None) else -99.0
                max_limit = sett.max if (sett and sett.max is not None) else 99.0
                loc = sett.location if (sett and sett.location) else "Улица"
                grp = sett.group if (sett and sett.group) else "Климат"

                # 7. Формируем уникальный UID для фронтенда (пара модуль_тип, например "39_temp")
                sensor_uid = f"{modul.id}_{sensor_type}"

                # 8. Собираем чистый JSON без зашитых цветов
                data_for_frontend.append({
                    "uid": sensor_uid,
                    "sensor_id": modul.id,
                    "type": sensor_type,
                    "meta": {
                        "name": display_name,
                        "unit": "%" if sensor_type == "hum" else "°C",  # Авто-подстановка юнитов, если пустые
                        "ui_type": sett.ui_type if sett else 'numeric',
                        "location": loc,
                        "group": grp
                    },
                    "data": {
                        "value": last_entry.value,
                        "timestamp": int(last_entry.timestamp.timestamp()),  # Передаем timestamp Unix
                        "time_str": last_entry.timestamp.strftime('%H:%M'),
                        "is_online": is_online
                    },
                    "thresholds": {
                        "min": min_limit,
                        "max": max_limit
                    }
                })

    return jsonify(data_for_frontend)


@api_bp.route('/api/history/<int:sensor_id>')
def sensor_history(sensor_id):
    sensor_type = request.args.get('type', default='temp')

    try:
        hours = int(request.args.get('hours', default=24))
    except ValueError:
        hours = 24

    start_time = datetime.now() - timedelta(hours=hours)

    history = Measurement.query.filter(
        Measurement.sensor_id == sensor_id,
        Measurement.data_type == sensor_type,
        Measurement.timestamp >= start_time
    ).order_by(Measurement.timestamp.asc()).all()

    sett = Setting.query.filter_by(sensor_id=sensor_id, data_type=sensor_type).first()
    db_min = sett.min if (sett and sett.min is not None) else -50
    db_max = sett.max if (sett and sett.max is not None) else 50

    return jsonify({
        "labels": [m.timestamp.strftime('%H:%M') for m in history],
        "values": [m.value for m in history],
        "limits": {"min": db_min, "max": db_max}
    })


# --- НОВЫЕ РОУТЫ ДЛЯ УПРАВЛЕНИЯ ВНЕШНИМ ВИДОМ И ИНТЕРФЕЙСОМ ---

# Переменная в памяти для хранения текущего конфига отображения.
# В будущем, если захочешь, сможешь перенести это в таблицу настроек системы в БД.
CURRENT_UI_CONFIG = {
    "current_view": "cards",  # По умолчанию показываем карточки ('cards' или 'table')
    "group_by": "none"  # Как группировать по умолчанию ('none', 'location', 'group')
}


@api_bp.route('/api/ui/config', methods=['GET', 'POST'])
def handle_ui_config():
    """Эндпоинт для сохранения и получения настроек интерфейса"""
    global CURRENT_UI_CONFIG
    if request.method == 'POST':
        # Принимаем JSON от фронтенда с новыми настройками вида
        req_data = request.get_json() or {}
        if "current_view" in req_data:
            CURRENT_UI_CONFIG["current_view"] = req_data["current_view"]
        if "group_by" in req_data:
            CURRENT_UI_CONFIG["group_by"] = req_data["group_by"]
        return jsonify({"status": "success", "config": CURRENT_UI_CONFIG})

    # Если GET — просто отдаем текущие настройки
    return jsonify(CURRENT_UI_CONFIG)