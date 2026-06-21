"""
Контроллер для обработки конфигурационных настроек датчиков.
Управляет индивидуальными кастомными именами, локациями и аварийными порогами UI.
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.setting import Setting
from module_data_layer.models.schedule import DeviceSchedule
from module_data_layer.models.category import Category
from flask import Response
from module_data_layer.models.system_setting import SystemSetting

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/<int:sensor_id>', methods=['GET'])
def get_sensor_settings(sensor_id):
    if request.method == 'GET':
        try:
            d_type = request.args.get('type', 'temp')
            setting = db.session.query(Setting).filter_by(sensor_id=sensor_id, data_type=d_type).first()

            if setting:
                return jsonify({
                    "name": setting.name,
                    "alarm_min": setting.alarm_min if setting.alarm_min is not None else "",
                    "relay_min": setting.relay_min if setting.relay_min is not None else "",
                    "relay_max": setting.relay_max if setting.relay_max is not None else "",
                    "alarm_max": setting.alarm_max if setting.alarm_max is not None else "",
                    "location": setting.location.name if setting.location else "",
                    "group": setting.group.name if setting.group else "",
                    "ui_type": setting.ui_type,
                    "mute_until": setting.mute_until.isoformat() if setting.mute_until else ""
                }), 200
            else:
                # Если настроек еще нет, отдаем дефолты под новую структуру
                return jsonify({
                    "name": "",
                    "alarm_min": "",
                    "relay_min": "",
                    "relay_max": "",
                    "alarm_max": "",
                    "location": "Дом",
                    "group": "Климат",
                    "ui_type": "numeric"
                }), 200
        except Exception as err:
            return jsonify({"status": "error", "message": str(err)}), 500


@settings_bp.route('/<int:sensor_id>', methods=['POST'])
def save_sensor_settings(sensor_id):
    """Принимает конфигурацию параметров датчика от конкретной ячейки интерфейса."""
    try:
        req_data = request.get_json() or {}
        d_type = req_data.get('type')
        if not d_type:
            return jsonify({"status": "error", "message": "Параметр 'type' обязателен"}), 400

        setting = db.session.query(Setting).filter_by(sensor_id=sensor_id, data_type=d_type).first()

        if not setting:
            setting = Setting(sensor_id=sensor_id, data_type=d_type)
            db.session.add(setting)

        if 'name' in req_data: setting.name = str(req_data['name'])
        if 'ui_type' in req_data: setting.ui_type = str(req_data['ui_type'])

        if 'location' in req_data:
            loc_name = req_data['location']
            cat = Category.query.filter_by(name=loc_name, type='location').first()
            setting.location_id = cat.id if cat else None

        if 'group' in req_data:
            group_name = req_data['group']
            cat = Category.query.filter_by(name=group_name, type='group').first()
            setting.group_id = cat.id if cat else None

        # Чтение и валидация 4-х основных порогов датчика
        for field in ['alarm_min', 'relay_min', 'relay_max', 'alarm_max']:
            if field in req_data:
                val = req_data[field]
                parsed_val = float(val) if (val is not None and str(val).strip() != "") else None
                setattr(setting, field, parsed_val)

        # Обработка динамического расписания уставок
        if 'schedules' in req_data:
            periods_list = req_data['schedules']
            # Ожидается массив: [{"time_start": "08:00", "time_end": "20:00", "alarm_min": 15, "relay_min": 18, "relay_max": 25, "alarm_max": 28}]
            if isinstance(periods_list, list):
                for period in periods_list:
                    try:
                        datetime.strptime(period['time_start'], '%H:%M')
                        datetime.strptime(period['time_end'], '%H:%M')
                    except (ValueError, KeyError):
                        return jsonify({"status": "error",
                                        "message": "Некорректный формат времени в расписании. Используйте HH:MM"}), 400

                    if period['time_start'] >= period['time_end']:
                        return jsonify({"status": "error",
                                        "message": "Время начала периода должно быть меньше времени окончания"}), 400

                # Вызываем метод модели для перезаписи расписания (мы обновили его на Шаге 2)
                DeviceSchedule.save_schedules_for_sensor(
                    s_id=sensor_id,
                    d_type=d_type,
                    periods_list=periods_list
                )

        if 'mute_until' in req_data:
            mute_val = req_data['mute_until']
            if mute_val and str(mute_val).strip() != "":
                setting.mute_until = datetime.fromisoformat(mute_val)
            else:
                setting.mute_until = None

        db.session.commit()
        return jsonify({"status": "success", "message": "Настройки успешно сохранены"}), 200

    except ValueError as val_err:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Некорректный формат чисел: {str(val_err)}"}), 400
    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Внутренняя ошибка сервера: {str(err)}"}), 500


@settings_bp.route('/admin_phone', methods=['GET'])
def get_admin_phone():
    """Получение номера телефона для фронтенда из глобальных настроек"""
    try:
        setting = db.session.query(SystemSetting).filter_by(key='admin_phone').first()
        if setting:
            return jsonify({"value": setting.value}), 200
        return jsonify({"value": ""}), 200  # Если номера еще нет в базе
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@settings_bp.route('/admin_phone', methods=['POST'])
def save_admin_phone():
    """Сохранение или обновление номера телефона в глобальных настройках"""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({"status": "error", "message": "Неверные данные"}), 400

        new_phone = data['value'].strip()

        # Ищем существующую запись в новой таблице
        setting = db.session.query(SystemSetting).filter_by(key='admin_phone').first()

        if setting:
            setting.value = new_phone
        else:
            setting = SystemSetting(
                key='admin_phone',
                name='Номер администратора',
                value=new_phone,
                data_type='string',
                description='Номер для СМС-управления и дозвона при аварии'
            )
            db.session.add(setting)

        db.session.commit()
        return jsonify({"status": "success", "message": "Номер успешно сохранен"}), 200
    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500

@settings_bp.route('/save_sort_order', methods=['POST'])
def save_sort_order():
    """Принимает упорядоченный список датчиков и сохраняет их индексы в поле sort_order."""
    try:
        req_data = request.get_json()
        if not isinstance(req_data, list):
            return jsonify({"status": "error", "message": "Ожидался массив данных"}), 400

        # В цикле обновляем порядок на основе индекса элемента в массиве
        for index, item in enumerate(req_data):
            sensor_id = item.get('sensor_id')
            d_type = item.get('type')

            if sensor_id is None or not d_type:
                continue

            # Ищем существующую запись
            setting = db.session.query(Setting).filter_by(sensor_id=sensor_id, data_type=d_type).first()

            # Если записи нет (датчик работал по дефолтам), создаем её
            if not setting:
                setting = Setting(sensor_id=sensor_id, data_type=d_type)
                db.session.add(setting)

            # Присваиваем порядковый номер (начиная с 0 или 1, index в enumerate как раз идет по порядку)
            setting.sort_order = index

        db.session.commit()
        return jsonify({"status": "success", "message": "Порядок датчиков успешно сохранен"}), 200

    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Внутренняя ошибка сервера: {str(err)}"}), 500