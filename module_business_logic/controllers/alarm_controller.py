import codecs
from datetime import datetime
from flask import Blueprint, Response, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.setting import Setting
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.schedule import DeviceSchedule
from module_data_layer.models.system_setting import SystemSetting

alarm_bp = Blueprint('alarm', __name__)


@alarm_bp.route('/call_check', methods=['GET'])
def check_for_alarms():
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    # Достаем актуальный номер администратора
    admin_setting = db.session.query(SystemSetting).filter_by(key='admin_phone').first()
    admin_phone = admin_setting.value.strip() if admin_setting else ""

    # Запрашиваем настройки всех активных датчиков
    sensors_settings = db.session.query(Setting).filter(Setting.is_deleted == 0).all()

    alarm_status = 0

    for s in sensors_settings:
        is_alarm = False

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

        if not is_online:
            is_alarm = True

        if not is_alarm:
            val = float(last_meas.value)

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
            alarm_status = s.sort_order
            break

    return jsonify({
        "phone": admin_phone,
        "alarm": alarm_status
    })


# =====================================================================
# НОВАЯ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ СМС-КОМАНД ОТ ЗВОНИЛКИ
# Полный путь для ESP8266 будет: http://192.168.1.205/api/alarm/sms_command
# =====================================================================
from datetime import datetime, timedelta  # Убедись, что timedelta добавлен

from datetime import datetime, timedelta  # Убедись, что timedelta добавлен


@alarm_bp.route('/sms_command', methods=['GET'])
def handle_sms_command():
    raw_text = request.args.get('text', '').strip()

    if not raw_text:
        return Response("Empty command", mimetype='text/plain')

    # Декодирование
    try:
        if len(raw_text) > 4 and all(c in '0123456789ABCDEFabcdef' for c in raw_text):
            sms_text = codecs.decode(raw_text, 'hex').decode('utf-16-be')
        else:
            sms_text = raw_text
    except Exception:
        sms_text = raw_text

    cmd = sms_text.upper().strip()
    print(f"[БЭКЕНД] Принята СМС команда: {cmd}")

    # Обработка команды "НОМЕР_СТРОКИ ЧАСЫ" (например, "1 2")
    parts = cmd.split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        sensor_sort_order = int(parts[0])
        hours_to_mute = int(parts[1])

        target_sensor = db.session.query(Setting).filter_by(sort_order=sensor_sort_order).first()

        if target_sensor:
            target_sensor.mute_until = datetime.now() + timedelta(hours=hours_to_mute)
            db.session.commit()
            return Response(f"OK. Datchik {sensor_sort_order} zamuthen na {hours_to_mute} chas.", mimetype='text/plain')
        else:
            return Response("Error: Datchik ne nayden.", mimetype='text/plain')

    # Команда REBOOT
    if cmd == "REBOOT":
        return Response("System rebooting...", mimetype='text/plain')

    return Response("Unknown command", mimetype='text/plain')