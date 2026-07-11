"""
Контроллер для управления реле.
Путь: D:\Moy_Server\module_business_logic\controllers\relay_controller.py

Эндпоинты:
  POST /api/relay/check                        — ESP спрашивает состояние
  GET  /api/relay/<modul_id>/<relay_pin>       — получить настройки реле
  POST /api/relay/<modul_id>/<relay_pin>       — сохранить настройки
  POST /api/relay/<modul_id>/<relay_pin>/force — принудительно вкл/выкл
  GET  /api/relay/list                         — список всех реле
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.relay import Relay
from module_data_layer.models.relay_condition import RelayCondition
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.category import Category

relay_bp = Blueprint('relay', __name__)


def evaluate_conditions(relay: Relay) -> int:
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")

    all_conditions = db.session.query(RelayCondition).filter_by(
        modul_id=relay.modul_id,
        relay_pin=relay.relay_pin
    ).all()

    if not all_conditions:
        return relay.state

    # Ищем активный период
    period_conditions = [
        c for c in all_conditions
        if c.time_start and c.time_end
        and c.time_start <= current_time_str <= c.time_end
    ]
    base_conditions = [c for c in all_conditions if not c.time_start]
    active_conditions = period_conditions if period_conditions else base_conditions

    if not active_conditions:
        # return relay.state
        return 0

    # Проверяем есть ли принудительное состояние периода (schedule_result)
    # Берём из первого условия периода
    schedule_result = active_conditions[0].schedule_result

    # Если задан schedule_result и нет условий по датчикам — просто возвращаем его
    sensor_conditions = [c for c in active_conditions if c.sensor_id]
    if schedule_result is not None and not sensor_conditions:
        return schedule_result

    # Если есть условия по датчикам — проверяем их
    new_state = schedule_result if schedule_result is not None else relay.state

    for condition in sensor_conditions:
        last_meas = db.session.query(Measurement).filter_by(
            sensor_id=condition.sensor_id,
            data_type=condition.data_type
        ).order_by(Measurement.timestamp.desc()).first()

        if not last_meas:
            continue

        val = float(last_meas.value)
        threshold = float(condition.value)

        matched = False
        if condition.operator == '>'  and val >  threshold: matched = True
        if condition.operator == '<'  and val <  threshold: matched = True
        if condition.operator == '>=' and val >= threshold: matched = True
        if condition.operator == '<=' and val <= threshold: matched = True
        if condition.operator == '='  and val == threshold: matched = True
        if condition.operator == '!=' and val != threshold: matched = True

        if matched:
            new_state = condition.result

    return new_state


# ---------------------------------------------------------------
# POST /api/relay/check
# ESP передаёт своё состояние и получает новое
# Тело: {"modul_id": 65, "relay_pin": "D1", "state": 0}
# Ответ: {"state": 1, "mode": "conditions"}
# ---------------------------------------------------------------
@relay_bp.route('/check', methods=['POST'])
def relay_check():
    data = request.get_json(silent=True)
    if not data or 'modul_id' not in data or 'relay_pin' not in data:
        return jsonify({"error": "modul_id and relay_pin required"}), 400

    modul_id  = int(data['modul_id'])
    relay_pin = str(data['relay_pin'])
    esp_state = int(data.get('state', 0))

    relay = db.session.query(Relay).filter_by(
        modul_id=modul_id, relay_pin=relay_pin
    ).first()

    # Если реле ещё нет в БД — создаём с дефолтными настройками
    if not relay:
        relay = Relay(modul_id=modul_id, relay_pin=relay_pin, state=esp_state)
        db.session.add(relay)
        db.session.flush()
        alarm = False  # новое реле — аварии нет
    else:
        alarm = (esp_state != relay.state)

    # Обновляем время последнего обращения
    relay.last_seen = datetime.now()

    # Определяем новое состояние
    if relay.mode == 'force':
        new_state = relay.state  # принудительный режим — возвращаем что в БД
    else:
        new_state = evaluate_conditions(relay)  # режим условий
        relay.state = new_state  # обновляем состояние в БД

    db.session.commit()

    print(f"[RELAY] modul={modul_id} pin={relay_pin} "
          f"esp={esp_state} → new={new_state} mode={relay.mode} alarm={alarm}")

    return jsonify({
        "state": new_state,
        "mode": relay.mode,
        "alarm": alarm
    })


# ---------------------------------------------------------------
# GET /api/relay/<modul_id>/<relay_pin>
# Получить настройки реле для страницы настроек
# ---------------------------------------------------------------
@relay_bp.route('/<int:modul_id>/<relay_pin>', methods=['GET'])
def get_relay_settings(modul_id, relay_pin):
    relay = db.session.query(Relay).filter_by(
        modul_id=modul_id, relay_pin=relay_pin
    ).first()

    if not relay:
        return jsonify({
            "name": "",
            "ui_type": "relay",
            "location": "",
            "group": "",
            "offline_timeout": 5,
            "mode": "force",
            "state": 0,
            "conditions": []
        }), 200

    # Получаем условия
    conditions = db.session.query(RelayCondition).filter_by(
        modul_id=modul_id, relay_pin=relay_pin
    ).all()

    conditions_data = [{
        "id": c.id,
        "sensor_id": c.sensor_id,
        "data_type": c.data_type,
        "operator": c.operator,
        "value": c.value,
        "result": c.result,
        "time_start": c.time_start or "",
        "time_end": c.time_end or "",
        "schedule_result": c.schedule_result
    } for c in conditions]

    return jsonify({
        "name": relay.name or "",
        "ui_type": relay.ui_type,
        "location": relay.location.name if relay.location else "",
        "group": relay.group.name if relay.group else "",
        "offline_timeout": relay.offline_timeout,
        "mode": relay.mode,
        "state": relay.state,
        "conditions": conditions_data
    }), 200


# ---------------------------------------------------------------
# POST /api/relay/<modul_id>/<relay_pin>
# Сохранить настройки реле
# ---------------------------------------------------------------
@relay_bp.route('/<int:modul_id>/<relay_pin>', methods=['POST'])
def save_relay_settings(modul_id, relay_pin):
    try:
        data = request.get_json() or {}


        relay = db.session.query(Relay).filter_by(
            modul_id=modul_id, relay_pin=relay_pin
        ).first()

        if not relay:
            relay = Relay(modul_id=modul_id, relay_pin=relay_pin)
            db.session.add(relay)

        if 'name' in data:
            relay.name = str(data['name'])
        if 'ui_type' in data:
            relay.ui_type = str(data['ui_type'])
        if 'offline_timeout' in data:
            relay.offline_timeout = int(data['offline_timeout']) or 5
        if 'mode' in data:
            relay.mode = str(data['mode'])

        if 'state' in data and data.get('mode') == 'force':
            relay.state = int(data['state'])

        if 'location' in data:
            cat = Category.query.filter_by(name=data['location'], type='location').first()
            relay.location_id = cat.id if cat else None

        if 'group' in data:
            cat = Category.query.filter_by(name=data['group'], type='group').first()
            relay.group_id = cat.id if cat else None

        # Сохраняем условия — полная перезапись
        if 'conditions' in data:
            db.session.query(RelayCondition).filter_by(
                modul_id=modul_id, relay_pin=relay_pin
            ).delete()
            print('data!!: ')
            print(data)

            for c in data['conditions']:
                condition = RelayCondition(
                    modul_id=modul_id,
                    relay_pin=relay_pin,
                    sensor_id=int(c['sensor_id']) if c.get('sensor_id') is not None else None,
                    data_type=str(c['data_type']) if c.get('data_type') is not None else None,
                    operator=str(c['operator']) if c.get('operator') is not None else None,
                    value=float(c['value']) if c.get('value') is not None else None,
                    result=int(c['result']) if c.get('result') is not None else None,
                    time_start=c.get('time_start') or None,
                    time_end=c.get('time_end') or None,
                    schedule_result=int(c['schedule_result']) if c.get('schedule_result') is not None else None
                )
                db.session.add(condition)

        db.session.commit()
        if relay.mode == 'conditions':
            new_state = evaluate_conditions(relay)
            relay.state = new_state
            db.session.commit()
        return jsonify({"status": "success"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------
# POST /api/relay/<modul_id>/<relay_pin>/force
# Принудительно переключить состояние реле
# Тело: {"state": 1}
# ---------------------------------------------------------------
@relay_bp.route('/<int:modul_id>/<relay_pin>/force', methods=['POST'])
def force_relay(modul_id, relay_pin):
    data = request.get_json(silent=True)
    if not data or 'state' not in data:
        return jsonify({"error": "state required"}), 400

    relay = db.session.query(Relay).filter_by(
        modul_id=modul_id, relay_pin=relay_pin
    ).first()

    if not relay:
        return jsonify({"error": "Relay not found"}), 404

    relay.state = int(data['state'])
    relay.mode = 'force'
    db.session.commit()

    return jsonify({"status": "ok", "state": relay.state}), 200


# ---------------------------------------------------------------
# GET /api/relay/list
# Список всех реле для главной страницы
# ---------------------------------------------------------------
@relay_bp.route('/list', methods=['GET'])
def list_relays():
    now = datetime.now()
    relays = db.session.query(Relay).filter_by(is_deleted=0).order_by(
        Relay.sort_order
    ).all()

    result = []
    for r in relays:
        # Определяем статус онлайн/офлайн
        is_online = False
        if r.last_seen:
            timeout_sec = r.offline_timeout * 60
            is_online = (now - r.last_seen).total_seconds() < timeout_sec

        # Цвет карточки
        if not is_online:
            status_class = 'status-black'   # офлайн
        elif r.mode == 'force':
            status_class = 'status-blue'    # принудительное управление
        else:
            status_class = 'status-ok'      # нормально

        result.append({
            "modul_id": r.modul_id,
            "relay_pin": r.relay_pin,
            "name": r.name or f"Реле {r.modul_id}/{r.relay_pin}",
            "state": r.state,
            "mode": r.mode,
            "status_class": status_class,
            "location": r.location.name if r.location else "",
            "group": r.group.name if r.group else "",
            "last_seen": r.last_seen.strftime('%H:%M') if r.last_seen else "",
            "sort_order": r.sort_order
        })

    return jsonify(result)
