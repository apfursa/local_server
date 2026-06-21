from datetime import datetime

# Единый справочник иконок
UI_ICONS = {
    'leak': {0: '✅ Чисто', 1: '🚨 ПРОТЕЧКА!'},
    'door': {0: '🟢 Закрыто', 1: '🚪 ОТКРЫТО'},
    'motion': {0: '⚪ Спокойно', 1: '🏃 ДВИЖЕНИЕ'},
    'smoke': {0: '✅ Чисто', 1: '🔥 ДЫМ!'},
    'gas': {0: '✅ Норма', 1: '☣️ ГАЗ!'},
    'power': {0: '🔋 Батарея', 1: '🔌 Сеть 220В'},
    'pump': {0: '💤 Спит', 1: '💦 ПОЛИВ'},
    'gate': {0: '🔒 Закрыто', 1: '🔓 Открыто'},
    'light': {0: '🌑 Выкл', 1: '💡 Включен'},
    'fan': {0: '⚪ Выкл', 1: '🌀 Обдув'}
}


# def process_sensor_data(last_meas, setting, mode_label, final_min, final_max, schedules_list=None):
#     """Преобразует данные датчика в формат, готовый для HTML-шаблонов."""
#     val = float(last_meas.value)
#     # Датчик онлайн, если замер был менее 5 минут назад
#     is_online = (datetime.now() - last_meas.timestamp).total_seconds() < 300.0
#
#     # СРАЗУ ОПРЕДЕЛЯЕМ СТАТУС ГЛУШЕНИЯ (чтобы использовать ниже)
#     is_muted = bool(setting and setting.mute_until and setting.mute_until > datetime.now())
#
#     # 1. Определение CSS-класса статуса
#     if not is_online:
#         status_class = 'status-black'
#     elif final_min is None or final_max is None:
#         status_class = 'status-gray'
#     elif val > final_max:
#         status_class = 'status-high'
#     elif val < final_min:
#         status_class = 'status-low'
#     else:
#         status_class = 'status-ok'
#
#     # 2. Определение отображаемого значения (иконка или число)
#     ui_type = setting.ui_type if setting else 'numeric'
#     display_value = UI_ICONS[ui_type].get(int(val), str(val)) if ui_type in UI_ICONS else str(val)
#
#     # 3. Формирование объекта для фронтенда
#     return {
#         "uid": f"{last_meas.sensor_id}_{last_meas.data_type}",
#         "sensor_id": last_meas.sensor_id,
#         "type": last_meas.data_type,
#         "name": setting.name if (setting and setting.name) else f"Датчик {last_meas.data_type}",
#         "group": setting.group.name if (setting and setting.group) else "Без группы",
#         "group_id": setting.group_id if (setting and setting.group_id) else 0,  # <-- ДОБАВИТЬ ID
#         "location": setting.location.name if (setting and setting.location) else "Без группы",
#         "location_id": setting.location_id if (setting and setting.location_id) else 0,  # <-- ДОБАВИТЬ ID
#         "display_value": display_value,
#         "status_class": status_class,
#         "offline_class": '' if is_online else 'offline_class',
#         "mode_label": 'график' if mode_label == 'schedule' else ('база' if final_min is not None else 'нет'),
#         # "mute_icon": '📵' if (setting and setting.mute_until and setting.mute_until > datetime.now()) else '',
#         # "mute_until": setting.mute_until.strftime("%d.%m %H:%M") if is_muted else '',
#         "mute_icon": '📵' if is_muted else '',
#         "mute_until": setting.mute_until.strftime("%d.%m %H:%M") if is_muted else '',
#         "time_str": last_meas.timestamp.strftime("%H:%M"),
#         "min": final_min if final_min is not None else '-',
#         "max": final_max if final_max is not None else '-',
#         "schedules": schedules_list or []
#     }

def process_sensor_data(last_meas, setting, mode_label, alarm_min, relay_min, relay_max, alarm_max,
                        schedules_list=None):
    """Преобразует данные датчика в формат, готовый для HTML-шаблонов."""
    val = float(last_meas.value)
    # Датчик онлайн, если замер был менее 5 минут назад
    is_online = (datetime.now() - last_meas.timestamp).total_seconds() < 300.0

    # Статус глушения аварий
    is_muted = bool(setting and setting.mute_until and setting.mute_until > datetime.now())

    # 1. Определение CSS-класса статуса (смотрим только на КРИТИЧЕСКУЮ АВАРИЮ)
    if not is_online:
        status_class = 'status-black'
    elif alarm_min is None or alarm_max is None:
        status_class = 'status-gray'
    elif val > alarm_max:
        status_class = 'status-high'
    elif val < alarm_min:
        status_class = 'status-low'
    else:
        status_class = 'status-ok'

    # 2. Определение отображаемого значения (иконка или число)
    ui_type = setting.ui_type if setting else 'numeric'
    display_value = UI_ICONS[ui_type].get(int(val), str(val)) if ui_type in UI_ICONS else str(val)

    # 3. Формирование объекта для фронтенда (отдаем все 4 порога)
    return {
        "uid": f"{last_meas.sensor_id}_{last_meas.data_type}",
        "sensor_id": last_meas.sensor_id,
        "type": last_meas.data_type,
        "name": setting.name if (setting and setting.name) else f"Датчик {last_meas.data_type}",
        "group": setting.group.name if (setting and setting.group) else "Без группы",
        "group_id": setting.group_id if (setting and setting.group_id) else 0,
        "location": setting.location.name if (setting and setting.location) else "Без группы",
        "location_id": setting.location_id if (setting and setting.location_id) else 0,
        "display_value": display_value,
        "status_class": status_class,
        "offline_class": '' if is_online else 'offline_class',
        "mode_label": 'график' if mode_label == 'schedule' else ('база' if alarm_min is not None else 'нет'),
        "mute_icon": '📵' if is_muted else '',
        "mute_until": setting.mute_until.strftime("%d.%m %H:%M") if is_muted else '',
        "time_str": last_meas.timestamp.strftime("%H:%M"),

        # Отдаем на фронтенд все четыре порога
        "alarm_min": alarm_min if alarm_min is not None else '-',
        "relay_min": relay_min if relay_min is not None else '-',
        "relay_max": relay_max if relay_max is not None else '-',
        "alarm_max": alarm_max if alarm_max is not None else '-',

        "schedules": schedules_list or []
    }