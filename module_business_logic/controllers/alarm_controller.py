# from flask import Blueprint, jsonify
# from datetime import datetime
# from module_data_layer.core.db_config import db
# from module_data_layer.models.setting import Setting
#
# # Префикс /api задается глобально в run.py, здесь пути пишем СРАЗУ от корня.
# alarm_bp = Blueprint('alarm', __name__)
#
# @alarm_bp.route('/call_check', methods=['GET'])
# def check_for_alarms():
#     now = datetime.now()
#     # Получаем все настройки, где заданы пороги
#     sensors = db.session.query(Setting).filter(Setting.min != None, Setting.max != None).all()
#
#     for s in sensors:
#         # ПРОВЕРКА (логика зависит от того, где у тебя лежит текущее значение датчика)
#         # Если is_in_alarm() у тебя метод модели, убедись, что он видит текущее s.value
#         if s.is_in_alarm() and (s.mute_until is None or now > s.mute_until):
#             return jsonify({"phone": "79991234567", "reason": s.name})
#
#     return jsonify({"phone": "", "reason": ""})


from flask import Blueprint, Response
from datetime import datetime
from module_data_layer.core.db_config import db
from module_data_layer.models.setting import Setting
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.schedule import DeviceSchedule
from module_data_layer.models.system_setting import SystemSetting

alarm_bp = Blueprint('alarm', __name__)


# @alarm_bp.route('/call_check', methods=['GET'])
# def check_for_alarms():
#     now = datetime.now()
#     current_time_str = now.strftime("%H:%M")  # Получаем время в формате "14:30"
#
#     # 1. Запрашиваем только активные настройки датчиков
#     sensors_settings = db.session.query(Setting).filter(Setting.is_deleted == 0).all()
#
#     for s in sensors_settings:
#         # Проверяем режим "Не звонить до"
#         if s.mute_until and now < s.mute_until:
#             continue
#
#         # 2. Вытаскиваем САМОЕ СВЕЖЕЕ измерение для этого датчика и этого типа данных
#         last_meas = db.session.query(Measurement).filter_by(
#             sensor_id=s.sensor_id,
#             data_type=s.data_type
#         ).order_by(Measurement.timestamp.desc()).first()
#
#         if not last_meas:
#             continue  # Если по датчику еще не было измерений, пропускаем
#
#         # Проверяем, на связи ли датчик (если оффлайн более 5 минут, звонить по порогам нет смысла)
#         is_online = (now - last_meas.timestamp).total_seconds() < 300.0
#         if not is_online:
#             continue
#
#         val = float(last_meas.value)
#
#         # 3. ЛОГИКА ОПРЕДЕЛЕНИЯ ПОРОГОВ (Базовые vs Расписание)
#         # Ищем, есть ли активный период в расписании на текущую минуту
#         active_schedule = db.session.query(DeviceSchedule).filter(
#             DeviceSchedule.sensor_id == s.sensor_id,
#             DeviceSchedule.data_type == s.data_type,
#             DeviceSchedule.time_start <= current_time_str,
#             DeviceSchedule.time_end >= current_time_str
#         ).first()
#
#         if active_schedule:
#             final_min = active_schedule.param_min
#             final_max = active_schedule.param_max
#         else:
#             final_min = s.min
#             final_max = s.max
#
#         # 4. ПРОВЕРКА НА АВАРИЮ
#         is_alarm = False
#         if final_min is not None and val < final_min:
#             is_alarm = True
#         if final_max is not None and val > final_max:
#             is_alarm = True
#
#         # 5. ЕСЛИ СРАБОТАЛО — НЕЕМЕДЛЕННО ОТДАЕМ НОМЕР ДЛЯ SIM800L
#         if is_alarm:
#             # Отдаем "голый" текст, как и просила ESP8266
#             return Response("+79181656914", mimetype='text/plain')
#
#     # Если всё спокойно или все аварийные датчики "замучены" кнопкой — отдаем пустоту
#     return Response("", mimetype='text/plain')

from flask import jsonify

@alarm_bp.route('/call_check', methods=['GET'])
def check_for_alarms():
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    # Сначала всегда достаем актуальный номер администратора из настроек

    # Достаем актуальный номер администратора из глобальной таблицы
    admin_setting = db.session.query(SystemSetting).filter_by(key='admin_phone').first()

    # Если номера вообще нет в базе (база пустая), отдаем пустую строку, чтобы звонилка знала, что слать некуда
    admin_phone = admin_setting.value.strip() if admin_setting else ""

    # По умолчанию считаем, что аварии нет
    is_alarm = False

    sensors_settings = db.session.query(Setting).filter(Setting.is_deleted == 0).all()

    for s in sensors_settings:
        if s.mute_until and now < s.mute_until:
            continue

        last_meas = db.session.query(Measurement).filter_by(
            sensor_id=s.sensor_id,
            data_type=s.data_type
        ).order_by(Measurement.timestamp.desc()).first()

        if not last_meas:
            continue

        is_online = (now - last_meas.timestamp).total_seconds() < 300.0
        if not is_online:
            continue

        val = float(last_meas.value)

        active_schedule = db.session.query(DeviceSchedule).filter(
            DeviceSchedule.sensor_id == s.sensor_id,
            DeviceSchedule.data_type == s.data_type,
            DeviceSchedule.time_start <= current_time_str,
            DeviceSchedule.time_end >= current_time_str
        ).first()

        if active_schedule:
            final_min = active_schedule.param_min
            final_max = active_schedule.param_max
        else:
            final_min = s.min
            final_max = s.max

        if final_min is not None and val < final_min:
            is_alarm = True
        if final_max is not None and val > final_max:
            is_alarm = True

        if is_alarm:
            break # Если нашли хотя бы одну аварию, дальше можно не искать

    # Отдаем структурированный JSON-ответ, который ESP легко распарсит
    return jsonify({
        "phone": admin_phone,
        "alarm": 1 if is_alarm else 0
    })


# =====================================================================
# НОВАЯ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ СМС-КОМАНД ОТ ЗВОНИЛКИ
# Полный путь для ESP8266 будет: http://192.168.1.205/api/alarm/sms_command
# =====================================================================
import codecs
from flask import request


@alarm_bp.route('/sms_command', methods=['GET'])
def handle_sms_command():
    # Получаем сырой текст из запроса (text=...)
    raw_text = request.args.get('text', '').strip()

    if not raw_text:
        return Response("Empty command", mimetype='text/plain')

    # 1. ДЕКОДИРОВАНИЕ: Если текст пришел на русском (в формате UCS2 / HEX)
    try:
        # Проверяем, состоит ли строка только из HEX-символов (0-9, A-F)
        if len(raw_text) > 4 and all(c in '0123456789ABCDEFabcdef' for c in raw_text):
            sms_text = codecs.decode(raw_text, 'hex').decode('utf-16-be')
        else:
            sms_text = raw_text
    except Exception:
        sms_text = raw_text  # Если не получилось декодировать, оставляем как есть

    # 2. ПРИВЕДЕНИЕ К ОДНОМУ РЕГИСТРУ (чтобы STATUS и status работали одинаково)
    cmd = sms_text.upper().strip()
    print(f"[БЭКЕНД] Принята СМС команда: {cmd}")

    # # 3. ЛОГИКАОТВЕТОВ: Проверяем, что именно нам прислали
    # if cmd == "STATUS" or cmd == "ПРИВЕТ":
    #     # Этот текст звонилка перехватит и отправит тебе обратно на телефон
    #     return Response("System OK. All segments clear.", mimetype='text/plain')
    #
    # elif cmd == "REBOOT":
    #     return Response("Reboot command accepted.", mimetype='text/plain')
    #
    # else:
    #     return Response(f"Unknown command: {cmd}", mimetype='text/plain')

    # 3. ЛОГИКА ОТВЕТОВ: Отдаем текст СТРОГО латиницей, чтобы модем не слал @@@
    if cmd == "STATUS" or cmd == "ПРИВЕТ" or cmd == "ТАК":
        # Вместо "Система ОК" пишем латиницей
        return Response("System OK. Vse datchiki v norme.", mimetype='text/plain')

    elif cmd == "REBOOT":
        return Response("System rebooting...", mimetype='text/plain')

    else:
        # Если команда неизвестна, возвращаем её английский транслит
        # Чтобы не упали в ошибку, если cmd содержит русские буквы,
        # выводим фиксированный ответ или очищаем от кириллицы
        return Response(f"Unknown command received", mimetype='text/plain')