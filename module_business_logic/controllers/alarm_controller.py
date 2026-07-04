from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.setting import Setting
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.schedule import DeviceSchedule
from module_data_layer.models.system_setting import SystemSetting


def decode_sms_text(raw_text: str) -> str:
    """Декодирует UCS2 hex-строку в обычный текст если нужно."""
    try:
        if len(raw_text) > 4 and all(c in '0123456789ABCDEFabcdef' for c in raw_text):
            return bytes.fromhex(raw_text).decode('utf-16-be')
    except Exception:
        pass
    return raw_text


alarm_bp = Blueprint('alarm', __name__)


def get_all_alarms():
    """
    Возвращает список ВСЕХ датчиков, находящихся сейчас в состоянии тревоги
    (за вычетом замьюченных через mute_until).
    """
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    sensors_settings = db.session.query(Setting).filter(Setting.is_deleted == 0).all()
    alarms = []

    for s in sensors_settings:
        if s.mute_until and now < s.mute_until:
            continue

        last_meas = db.session.query(Measurement).filter_by(
            sensor_id=s.sensor_id,
            data_type=s.data_type
        ).order_by(Measurement.timestamp.desc()).first()

        if not last_meas:
            continue

        timeout_minutes = s.offline_timeout if s.offline_timeout is not None else 5
        timeout_seconds = timeout_minutes * 60.0
        is_online = (now - last_meas.timestamp).total_seconds() < timeout_seconds

        is_alarm = False
        val = float(last_meas.value)

        if not is_online:
            is_alarm = True
        else:
            active_schedule = db.session.query(DeviceSchedule).filter(
                DeviceSchedule.sensor_id == s.sensor_id,
                DeviceSchedule.data_type == s.data_type,
                DeviceSchedule.time_start <= current_time_str,
                DeviceSchedule.time_end >= current_time_str
            ).first()

            if active_schedule:
                final_min = active_schedule.alarm_min if active_schedule.alarm_min is not None else s.alarm_min
                final_max = active_schedule.alarm_max if active_schedule.alarm_max is not None else s.alarm_max
            else:
                final_min = s.alarm_min
                final_max = s.alarm_max

            if final_min is not None and val < final_min:
                is_alarm = True
            if final_max is not None and val > final_max:
                is_alarm = True

        if is_alarm:
            alarms.append({
                "sensor_id": s.sensor_id,
                "data_type": s.data_type,
                "sort_order": s.sort_order,
                "name": s.name,
                "value": val if is_online else None,
                "online": is_online
            })

    alarms.sort(key=lambda a: (a["sort_order"] is None, a["sort_order"]))
    return alarms


def get_sensor_status_str(sort_order: int) -> str:
    """
    Формирует строку статуса датчика для отправки через SMS.
    Формат:
      S1 OK VAL:21.4 MIN:-25.0 MAX:-10.0
      S1 OK VAL:21.4 MIN:-25.0 MAX:-10.0 RMIN:35.0 RMAX:50.0
      S1 OK VAL:3.5 MIN:-3.0 MAX:5.0 08:00-20:00
      S1 ALARM VAL:21.4 MIN:-25.0 MAX:-10.0 MUTE:01.07 13:52
      S1 OFFLINE MUTE:01.07 13:52
    """
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    target = db.session.query(Setting).filter_by(
        sort_order=sort_order, is_deleted=0
    ).first()

    if not target:
        return "ERROR:SENSOR_NOT_FOUND"

    # Последнее измерение
    last_meas = db.session.query(Measurement).filter_by(
        sensor_id=target.sensor_id,
        data_type=target.data_type
    ).order_by(Measurement.timestamp.desc()).first()

    if not last_meas:
        return f"S{sort_order} NO_DATA"

    # Онлайн?
    timeout_seconds = (target.offline_timeout if target.offline_timeout is not None else 5) * 60.0
    is_online = (now - last_meas.timestamp).total_seconds() < timeout_seconds
    val = float(last_meas.value)

    # Mute строка
    mute_str = ""
    if target.mute_until and now < target.mute_until:
        mute_str = f" MUTE:{target.mute_until.strftime('%d.%m %H:%M')}"

    # Офлайн
    if not is_online:
        return f"S{sort_order} OFFLINE{mute_str}"

    # Активное расписание
    active_schedule = db.session.query(DeviceSchedule).filter(
        DeviceSchedule.sensor_id == target.sensor_id,
        DeviceSchedule.data_type == target.data_type,
        DeviceSchedule.time_start <= current_time_str,
        DeviceSchedule.time_end >= current_time_str
    ).first()

    if active_schedule:
        final_min = active_schedule.alarm_min if active_schedule.alarm_min is not None else target.alarm_min
        final_max = active_schedule.alarm_max if active_schedule.alarm_max is not None else target.alarm_max
        # Для реле — только из расписания, без fallback на базовые
        final_rmin = active_schedule.relay_min  # ← убрали fallback
        final_rmax = active_schedule.relay_max  # ← убрали fallback
        schedule_str = f" {active_schedule.time_start}-{active_schedule.time_end}"
    else:
        final_min = target.alarm_min
        final_max = target.alarm_max
        final_rmin = target.relay_min
        final_rmax = target.relay_max
        schedule_str = ""

    # Аварийный статус
    is_alarm = False
    if final_min is not None and val < final_min:
        is_alarm = True
    if final_max is not None and val > final_max:
        is_alarm = True

    status_str = "ALARM" if is_alarm else "OK"

    # Собираем строку уставок
    parts = []
    if final_min is not None:
        parts.append(f"MIN:{final_min}")
    if final_max is not None:
        parts.append(f"MAX:{final_max}")
    if final_rmin is not None:
        parts.append(f"RMIN:{final_rmin}")
    if final_rmax is not None:
        parts.append(f"RMAX:{final_rmax}")

    thresholds_str = " ".join(parts)
    if thresholds_str:
        thresholds_str = " " + thresholds_str

    return f"S{sort_order} {status_str} VAL:{val}{thresholds_str}{schedule_str}{mute_str}"


@alarm_bp.route('/call_check', methods=['GET'])
def check_for_alarms():
    """
    Эндпоинт для звонилки (ESP8266).
    Возвращает номер админа и sort_order ПЕРВОГО датчика в тревоге (или 0, если тревог нет).
    """
    admin_setting = db.session.query(SystemSetting).filter_by(key='admin_phone').first()
    admin_phone = admin_setting.value.strip() if admin_setting else ""

    alarms = get_all_alarms()
    alarm_status = alarms[0]['sort_order'] if alarms else 0

    return jsonify({
        "phone": admin_phone,
        "alarm": alarm_status
    })


# =====================================================================
# ОБРАБОТКА СМС-КОМАНД ОТ ЗВОНИЛКИ
# Полный путь для ESP8266: POST http://<server>/api/alarm/sms_command
# Тело запроса: {"text": "STATUS"}
# Ответ: {"reply": "..."}
# =====================================================================
@alarm_bp.route('/sms_command', methods=['POST'])
def handle_sms_command():
    data = request.get_json(silent=True)
    if not data or 'text' not in data:
        return jsonify({"reply": "ERROR:NO_TEXT"}), 400

    cmd = decode_sms_text(data['text'].strip()).upper()
    print(f"[БЭКЕНД] Принята СМС команда: {cmd}")
    parts = cmd.split(':')

    # ---------------------------------------------------------------
    # STATUS — статус всех датчиков в тревоге
    # ---------------------------------------------------------------
    if cmd == "STATUS":
        alarms = get_all_alarms()
        if not alarms:
            return jsonify({"reply": "STATUS:OK ALARM:0"})
        alarm_list = " ".join([f"S{a['sort_order']}" for a in alarms])
        return jsonify({"reply": f"STATUS:ALARM {alarm_list}"})

    # ---------------------------------------------------------------
    # STATUS:1 — подробный статус конкретного датчика
    # ---------------------------------------------------------------
    if len(parts) == 2 and parts[0] == "STATUS" and parts[1].isdigit():
        reply = get_sensor_status_str(int(parts[1]))
        return jsonify({"reply": reply})

    # ---------------------------------------------------------------
    # RELAY:1:ON / RELAY:1:OFF — управление реле
    # ---------------------------------------------------------------
    if len(parts) == 3 and parts[0] == "RELAY" and parts[1].isdigit() and parts[2] in ("ON", "OFF"):
        relay_id = int(parts[1])
        state = parts[2]
        # TODO: здесь должен быть вызов вашей реальной логики управления реле
        return jsonify({"reply": f"RELAY:{relay_id}:{state}:OK"})

    # ---------------------------------------------------------------
    # MUTE:60 — замьютить ВСЕ датчики на N минут
    # ---------------------------------------------------------------
    if len(parts) == 2 and parts[0] == "MUTE" and parts[1].isdigit():
        minutes = int(parts[1])
        sensors_settings = db.session.query(Setting).filter(Setting.is_deleted == 0).all()
        for s in sensors_settings:
            s.mute_until = datetime.now() + timedelta(minutes=minutes)
        db.session.commit()
        return jsonify({"reply": f"MUTE:OK:{minutes}min"})

    # ---------------------------------------------------------------
    # MUTE:1:60 — замьютить конкретный датчик на N минут
    # ---------------------------------------------------------------
    if len(parts) == 3 and parts[0] == "MUTE" and parts[1].isdigit() and parts[2].isdigit():
        sensor_id = int(parts[1])
        minutes = int(parts[2])
        target = db.session.query(Setting).filter_by(sort_order=sensor_id, is_deleted=0).first()
        if not target:
            return jsonify({"reply": "ERROR:SENSOR_NOT_FOUND"})
        target.mute_until = datetime.now() + timedelta(minutes=minutes)
        db.session.commit()
        return jsonify({"reply": f"MUTE:{sensor_id}:OK:{minutes}min"})

    # ---------------------------------------------------------------
    # REBOOT
    # ---------------------------------------------------------------
    if cmd == "REBOOT":
        return jsonify({"reply": "System rebooting..."})

    return jsonify({"reply": "ERROR:UNKNOWN_CMD"})
