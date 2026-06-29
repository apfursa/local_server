"""
Контроллер бизнес-логики и REST API.
Отвечает за сборку актуального состояния датчиков, отдачу истории для графиков и UI конфигурации.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from sqlalchemy import func, select
from module_data_layer.core.db_config import db
from module_data_layer.models.device import Device
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.setting import Setting
from module_data_layer.models.schedule import DeviceSchedule
from module_business_logic.processors.sensor_processor import process_sensor_data


# Инициализируем Blueprint модуля API.
# Префикс /api задается глобально в run.py, здесь пути пишем СРАЗУ от корня.
api_bp = Blueprint('api', __name__)

# Справочник единиц измерения по типам данных согласно общему ТЗ
UNIT_MAPPING = {
    'temp': '°C',
    'hum': '%',
    'leak': '',
    'smoke': '',
    'gas': '',
    'power': 'Вт',
    'pump': '',
    'gate': '',
    'light': '',
    'fan': ''
}

# Переменная в памяти для хранения текущего конфига отображения (Таблица/Карточки, группировка)
CURRENT_UI_CONFIG = {
    "current_view": "cards",
    "group_by": "none"
}

# @api_bp.route('/latest', methods=['GET'])
# def get_latest_state():
#     """Возвращает актуальное состояние всех датчиков в системе с учетом расписаний."""
#     response_data = []
#
#     try:
#         # Шаг 1: Находим последние замеры для каждой комбинации датчика и типа
#         subquery = db.session.query(
#             func.max(Measurement.id).label('max_id')
#         ).group_by(
#             Measurement.sensor_id,
#             Measurement.data_type
#         ).subquery()
#
#         # Шаг 2: Извлекаем замеры
#         latest_measurements = db.session.query(Measurement).filter(
#             Measurement.id.in_(select(subquery.c.max_id))
#         ).all()
#
#         # Шаг 3: Собираем карту устройств и настроек
#         devices_map = {d.id: d for d in db.session.query(Device).all()}
#         all_settings = db.session.query(Setting).all()
#         settings_map = {(s.sensor_id, s.data_type): s for s in all_settings}
#
#         # Текущее время сервера в строковом формате "ЧЧ:ММ:СС" для точного сравнения с базой
#         current_time_str = datetime.now().strftime("%H:%M:%S")
#
#         # Шаг 4: Формируем контракт
#         for last_meas in latest_measurements:
#             sensor_id = last_meas.sensor_id
#             d_type = last_meas.data_type
#             setting = settings_map.get((sensor_id, d_type))
#
#             # Метаданные датчика
#             name = setting.name if (setting and setting.name) else f"Датчик {d_type} ({sensor_id})"
#             ui_type = setting.ui_type if setting else 'numeric'
#             location = setting.location.name if (setting and setting.location) else 'Дом'
#             group = setting.group.name if (setting and setting.group) else 'Климат'
#
#             # Базовые пороги из таблицы настроек (если их нет в БД — оставляем None)
#             base_min = setting.min if (setting and setting.min is not None) else None
#             base_max = setting.max if (setting and setting.max is not None) else None
#
#             # Расчет статуса связи (онлайн, если ответ был меньше 5 минут назад)
#             time_delta = datetime.now() - last_meas.timestamp
#             is_online = time_delta.total_seconds() < 300.0
#
#             # Получаем все временные периоды расписания для этой комбинации
#             schedules = db.session.query(DeviceSchedule).filter_by(
#                 sensor_id=sensor_id,
#                 data_type=d_type
#             ).all()
#
#             schedules_list = []
#             active_schedule_thresholds = None
#             active_schedule_time = ""  # <-- ДОБАВЛЯЕМ ПЕРЕМЕННУЮ ДЛЯ ХРАНЕНИЯ ВРЕМЕНИ
#
#             for s in schedules:
#                 # Наполняем архивный список для графиков/истории
#                 schedules_list.append({
#                     "id": s.id,
#                     "time_start": s.time_start,
#                     "time_end": s.time_end,
#                     "min": float(s.param_min) if s.param_min is not None else None,
#                     "max": float(s.param_max) if s.param_max is not None else None
#                 })
#
#                 # Проверяем, попадает ли текущее время сервера внутрь этого интервала
#                 # Текстовое сравнение строк "14:00:00" >= "08:00:00" в Python работает отлично
#                 if s.time_start <= current_time_str <= s.time_end:
#                     active_schedule_thresholds = {
#                         "min": float(s.param_min) if s.param_min is not None else None,
#                         "max": float(s.param_max) if s.param_max is not None else None
#                     }
#                     # Запоминаем интервал (обрезаем секунды для компактности: "14:00:00" -> "14:00")
#                     t_start = s.time_start[:5]
#                     t_end = s.time_end[:5]
#                     active_schedule_time = f"({t_start} - {t_end})"  # Получится строка вида "(08:00..20:00)"
#
#             # Определение итоговых порогов и режима работы для фронтенда
#             if active_schedule_thresholds:
#                 # Если нашли точку в расписании — применяем её пороги
#                 final_min = active_schedule_thresholds["min"]
#                 final_max = active_schedule_thresholds["max"]
#                 mode_label = "schedule"
#             else:
#                 # Расписания нет или сейчас "дыра" между интервалами — берем базу
#                 final_min = base_min
#                 final_max = base_max
#                 mode_label = "base"
#
#             sensor_payload = process_sensor_data(last_meas, setting, mode_label, final_min, final_max, schedules_list)
#             # Собираем локацию и группу через слеш (берём именно .name)
#             loc = setting.location.name if (setting and setting.location) else ""
#             grp = setting.group.name if (setting and setting.group) else ""
#
#             if loc and grp:
#                 meta_label = f"{loc} / {grp}"
#             elif loc or grp:
#                 meta_label = loc if loc else grp
#             else:
#                 meta_label = ""  # Если ничего не задано, будет пусто
#
#             sensor_payload["meta_label"] = meta_label
#             sensor_payload["schedule_time"] = active_schedule_time if mode_label == "schedule" else ""
#             response_data.append(sensor_payload)
#
#             # Финальный шаг: сортируем response_data на основе sort_order из настроек.
#             # Если для датчика нет настроек в базе, даем ему большой индекс (например, 999), чтобы он улетел в конец списка.
#             response_data.sort(key=lambda x: settings_map.get((x['sensor_id'], x['type'])).sort_order
#             if settings_map.get((x['sensor_id'], x['type'])) else 999)
#
#         return jsonify(response_data), 200
#
#     except Exception as err:
#         return jsonify({"status": "error", "message": f"Внутренняя ошибка API: {str(err)}"}), 500

@api_bp.route('/latest', methods=['GET'])
def get_latest_state():
    """Возвращает актуальное состояние всех датчиков в системе с учетом расписаний."""
    response_data = []

    try:
        # Шаг 1: Находим последние замеры для каждой комбинации датчика и типа
        subquery = db.session.query(
            func.max(Measurement.id).label('max_id')
        ).group_by(
            Measurement.sensor_id,
            Measurement.data_type
        ).subquery()

        # Шаг 2: Извлекаем замеры
        latest_measurements = db.session.query(Measurement).filter(
            Measurement.id.in_(select(subquery.c.max_id))
        ).all()

        # Шаг 3: Собираем карту устройств и настроек
        devices_map = {d.id: d for d in db.session.query(Device).all()}
        all_settings = db.session.query(Setting).all()
        settings_map = {(s.sensor_id, s.data_type): s for s in all_settings}

        # Текущее время сервера в строковом формате "ЧЧ:ММ:СС" для точного сравнения с базой
        current_time_str = datetime.now().strftime("%H:%M:%S")

        # Шаг 4: Формируем контракт
        for last_meas in latest_measurements:
            sensor_id = last_meas.sensor_id
            d_type = last_meas.data_type
            setting = settings_map.get((sensor_id, d_type))

            # Базовые пороги из таблицы настроек settings
            base_alarm_min = setting.alarm_min if (setting and setting.alarm_min is not None) else None
            base_relay_min = setting.relay_min if (setting and setting.relay_min is not None) else None
            base_relay_max = setting.relay_max if (setting and setting.relay_max is not None) else None
            base_alarm_max = setting.alarm_max if (setting and setting.alarm_max is not None) else None

            # Получаем все временные периоды расписания для этой комбинации
            schedules = db.session.query(DeviceSchedule).filter_by(
                sensor_id=sensor_id,
                data_type=d_type
            ).all()

            schedules_list = []
            active_schedule_thresholds = None
            active_schedule_time = ""

            for s in schedules:
                # Наполняем архивный список для фронтенда с новыми ключами
                schedules_list.append({
                    "id": s.id,
                    "time_start": s.time_start,
                    "time_end": s.time_end,
                    "alarm_min": float(s.alarm_min) if s.alarm_min is not None else None,
                    "relay_min": float(s.relay_min) if s.relay_min is not None else None,
                    "relay_max": float(s.relay_max) if s.relay_max is not None else None,
                    "alarm_max": float(s.alarm_max) if s.alarm_max is not None else None
                })

                # Проверяем, попадает ли текущее время сервера внутрь этого интервала
                if s.time_start <= current_time_str <= s.time_end:
                    active_schedule_thresholds = {
                        "alarm_min": float(s.alarm_min) if s.alarm_min is not None else None,
                        "relay_min": float(s.relay_min) if s.relay_min is not None else None,
                        "relay_max": float(s.relay_max) if s.relay_max is not None else None,
                        "alarm_max": float(s.alarm_max) if s.alarm_max is not None else None
                    }
                    # Запоминаем интервал (обрезаем секунды: "14:00:00" -> "14:00")
                    t_start = s.time_start[:5]
                    t_end = s.time_end[:5]
                    active_schedule_time = f"({t_start} - {t_end})"

            # Определение итоговых порогов и режима работы для фронтенда
            if active_schedule_thresholds:
                f_alarm_min = active_schedule_thresholds["alarm_min"]
                f_relay_min = active_schedule_thresholds["relay_min"]
                f_relay_max = active_schedule_thresholds["relay_max"]
                f_alarm_max = active_schedule_thresholds["alarm_max"]
                mode_label = "schedule"
            else:
                f_alarm_min = base_alarm_min
                f_relay_min = base_relay_min
                f_relay_max = base_relay_max
                f_alarm_max = base_alarm_max
                mode_label = "base"

            # Извлекаем кастомный таймаут контроля связи (если нет, то 5)
            custom_timeout = setting.offline_timeout if (setting and setting.offline_timeout) else 5

            # Передаем все 4 новые уставки в обновленный процессор данных
            sensor_payload = process_sensor_data(
                last_meas, setting, mode_label,
                f_alarm_min, f_relay_min, f_relay_max, f_alarm_max,
                schedules_list,
                offline_timeout=custom_timeout
            )

            # Собираем локацию и группу через слеш
            loc = setting.location.name if (setting and setting.location) else ""
            grp = setting.group.name if (setting and setting.group) else ""

            if loc and grp:
                meta_label = f"{loc} / {grp}"
            elif loc or grp:
                meta_label = loc if loc else grp
            else:
                meta_label = ""

            sensor_payload["meta_label"] = meta_label
            sensor_payload["schedule_time"] = active_schedule_time if mode_label == "schedule" else ""
            response_data.append(sensor_payload)

        # Финальный шаг: сортируем собранный response_data на основе sort_order из настроек.
        # Вынесено за пределы цикла `for` для правильной и быстрой работы.
        response_data.sort(key=lambda x: settings_map.get((x['sensor_id'], x['type'])).sort_order
                           if settings_map.get((x['sensor_id'], x['type'])) else 999)

        return jsonify(response_data), 200

    except Exception as err:
        return jsonify({"status": "error", "message": f"Внутренняя ошибка API: {str(err)}"}), 500


@api_bp.route('/history/<int:sensor_id>', methods=['GET'])
def sensor_history(sensor_id):
    """Возвращает историю замеров конкретного датчика для отрисовки графиков Chart.js."""
    sensor_type = request.args.get('type', default='temp')

    try:
        hours = int(request.args.get('hours', default=24))
    except ValueError:
        hours = 24

    start_time = datetime.now() - timedelta(hours=hours)

    try:
        # Переписано на стандарты SQLAlchemy 2.0 query
        history = db.session.query(Measurement).filter(
            Measurement.sensor_id == sensor_id,
            Measurement.data_type == sensor_type,
            Measurement.timestamp >= start_time
        ).order_by(Measurement.timestamp.asc()).all()

        sett = db.session.query(Setting).filter_by(sensor_id=sensor_id, data_type=sensor_type).first()

        # ЗАЩИТА: Используем критические аварийные пороги для лимитов графика, если они заданы
        db_min = sett.alarm_min if (sett and sett.alarm_min is not None) else -50.0
        db_max = sett.alarm_max if (sett and sett.alarm_max is not None) else 50.0

        return jsonify({
            "labels": [m.timestamp.strftime('%H:%M') for m in history],
            "values": [m.value for m in history],
            "limits": {"min": db_min, "max": db_max}
        }), 200
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@api_bp.route('/ui/config', methods=['GET', 'POST'])
def handle_ui_config():
    """Эндпоинт для сохранения глобального режима отображения (карточки/таблица) фронтенда."""
    global CURRENT_UI_CONFIG
    try:
        if request.method == 'POST':
            req_data = request.get_json() or {}
            if "current_view" in req_data:
                CURRENT_UI_CONFIG["current_view"] = str(req_data["current_view"])
            if "group_by" in req_data:
                CURRENT_UI_CONFIG["group_by"] = str(req_data["group_by"])
            return jsonify({"status": "success", "config": CURRENT_UI_CONFIG}), 200

        return jsonify(CURRENT_UI_CONFIG), 200
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500

@api_bp.route('/schedules/<int:sensor_id>', methods=['GET'])
def get_sensor_schedules(sensor_id):
    """Возвращает все интервалы расписания для конкретного датчика и типа данных."""
    d_type = request.args.get('type')
    if not d_type:
        return jsonify({"status": "error", "message": "Параметр 'type' обязателен"}), 400

    try:
        schedules = db.session.query(DeviceSchedule).filter_by(
            sensor_id=sensor_id,
            data_type=d_type
        ).all()

        # СТАЛО: отдаем все 4 порога для корректного рендеринга в jQuery
        result = [{
            "id": s.id,
            "time_start": s.time_start,
            "time_end": s.time_end,
            "alarm_min": s.alarm_min,
            "relay_min": s.relay_min,
            "relay_max": s.relay_max,
            "alarm_max": s.alarm_max
        } for s in schedules]

        return jsonify(result), 200
        return jsonify(result), 200
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@api_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule_interval(schedule_id):
    """Удаляет конкретный временной интервал по его ID."""
    try:
        schedule = db.session.query(DeviceSchedule).get(schedule_id)
        if not schedule:
            return jsonify({"status": "error", "message": "Интервал не найден"}), 404

        db.session.delete(schedule)
        db.session.commit()
        return jsonify({"status": "success", "message": "Интервал успешно удален"}), 200
    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500