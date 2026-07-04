"""
Контроллер синхронизации.
POST /sync/push — локальный сервер пушит данные на удалённый
GET /sync/pull — локальный сервер тянет изменения с удалённого
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.measurement import Measurement
from module_data_layer.models.device import Device
from module_data_layer.models.setting import Setting
from module_data_layer.models.schedule import DeviceSchedule
from module_data_layer.models.category import Category
from module_data_layer.models.system_setting import SystemSetting

sync_bp = Blueprint('sync', __name__)


def _format_dt(dt):
    """Конвертирует datetime в строку 'YYYY-MM-DD HH:MM:SS'."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _parse_dt(s):
    """Парсит строку 'YYYY-MM-DD HH:MM:SS' в datetime."""
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


@sync_bp.route('/push', methods=['POST'])
def push():
    """
    Принимает данные от локального сервера и применяет к SQLite.
    Сравнивает updated_at для конфликтов.
    """
    try:
        data = request.get_json() or {}
        result = {
            'measurements': 0, 'devices': 0, 'settings': 0,
            'schedules': 0, 'categories': 0, 'system_settings': 0,
        }

        # Measurements
        for m in data.get('measurements', []):
            exists = Measurement.query.filter_by(
                sensor_id=m['sensor_id'], data_type=m['data_type'], timestamp=m['timestamp']
            ).first()
            if not exists:
                record = Measurement(
                    sensor_id=m['sensor_id'], value=float(m['value']),
                    data_type=m['data_type'], timestamp=m['timestamp'], is_synced=1,
                )
                db.session.add(record)
                result['measurements'] += 1

        # Devices
        for d in data.get('devices', []):
            Device.register_sensor(d['id'])
            result['devices'] += 1

        # Settings
        for s in data.get('settings', []):
            remote_time = _parse_dt(s.get('updated_at'))
            existing = Setting.query.filter_by(
                sensor_id=s['sensor_id'], data_type=s['data_type']
            ).first()

            if not existing or (remote_time and (not existing.updated_at or remote_time > existing.updated_at)):
                model = existing or Setting(sensor_id=s['sensor_id'], data_type=s['data_type'])
                model.name = s.get('name')
                model.ui_type = s.get('ui_type', 'numeric')
                model.location_id = s.get('location_id')
                model.group_id = s.get('group_id')
                model.alarm_min = s.get('alarm_min')
                model.relay_min = s.get('relay_min')
                model.relay_max = s.get('relay_max')
                model.alarm_max = s.get('alarm_max')
                model.offline_timeout = s.get('offline_timeout', 5)
                model.mute_until = _parse_dt(s.get('mute_until'))
                model.sort_order = s.get('sort_order', 0)
                model.is_deleted = s.get('is_deleted', 0)
                if remote_time:
                    model.updated_at = remote_time
                if not existing:
                    db.session.add(model)
                result['settings'] += 1

        # Schedules
        for sc in data.get('schedules', []):
            remote_time = _parse_dt(sc.get('updated_at'))
            existing = DeviceSchedule.query.get(sc['id']) if sc.get('id') else None

            if not existing or (remote_time and (not existing.updated_at or remote_time > existing.updated_at)):
                model = existing or DeviceSchedule(id=sc['id'])
                model.sensor_id = sc['sensor_id']
                model.data_type = sc['data_type']
                model.time_start = sc['time_start']
                model.time_end = sc['time_end']
                model.alarm_min = sc.get('alarm_min')
                model.relay_min = sc.get('relay_min')
                model.relay_max = sc.get('relay_max')
                model.alarm_max = sc.get('alarm_max')
                if remote_time:
                    model.updated_at = remote_time
                if not existing:
                    db.session.add(model)
                result['schedules'] += 1

        # Categories
        for c in data.get('categories', []):
            remote_time = _parse_dt(c.get('updated_at'))
            existing = Category.query.get(c['id']) if c.get('id') else None

            if not existing or (remote_time and (not existing.updated_at or remote_time > existing.updated_at)):
                model = existing or Category(id=c['id'])
                model.name = c['name']
                model.type = c['type']
                if remote_time:
                    model.updated_at = remote_time
                if not existing:
                    db.session.add(model)
                result['categories'] += 1

        # System settings
        for ss in data.get('system_settings', []):
            remote_time = _parse_dt(ss.get('updated_at'))
            existing = SystemSetting.query.get(ss['key']) if ss.get('key') else None

            if not existing or (remote_time and (not existing.updated_at or remote_time > existing.updated_at)):
                model = existing or SystemSetting(key=ss['key'])
                model.value = ss['value']
                model.data_type = ss.get('data_type', 'string')
                model.name = ss.get('name')
                model.description = ss.get('description')
                if remote_time:
                    model.updated_at = remote_time
                if not existing:
                    db.session.add(model)
                result['system_settings'] += 1

        db.session.commit()
        return jsonify({'status': 'ok', 'synced': result}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@sync_bp.route('/pull', methods=['GET'])
def pull():
    """
    Возвращает все данные, изменённые после указанного времени.
    GET /sync/pull?since=2026-07-03 12:00:00
    """
    try:
        since = request.args.get('since', '1970-01-01 00:00:00')
        since_dt = _parse_dt(since)
        response = {}

        # Settings
        if since_dt:
            items = Setting.query.filter(Setting.updated_at > since_dt).all()
        else:
            items = Setting.query.all()
        if items:
            response['settings'] = [{
                'sensor_id': s.sensor_id, 'data_type': s.data_type, 'name': s.name,
                'ui_type': s.ui_type, 'location_id': s.location_id, 'group_id': s.group_id,
                'alarm_min': s.alarm_min, 'relay_min': s.relay_min, 'relay_max': s.relay_max,
                'alarm_max': s.alarm_max, 'offline_timeout': s.offline_timeout,
                'mute_until': _format_dt(s.mute_until),
                'sort_order': s.sort_order, 'is_deleted': s.is_deleted,
                'updated_at': _format_dt(s.updated_at),
            } for s in items]

        # Schedules
        if since_dt:
            items = DeviceSchedule.query.filter(DeviceSchedule.updated_at > since_dt).all()
        else:
            items = DeviceSchedule.query.all()
        if items:
            response['schedules'] = [{
                'id': sc.id, 'sensor_id': sc.sensor_id, 'data_type': sc.data_type,
                'time_start': sc.time_start, 'time_end': sc.time_end,
                'alarm_min': sc.alarm_min, 'relay_min': sc.relay_min,
                'relay_max': sc.relay_max, 'alarm_max': sc.alarm_max,
                'updated_at': _format_dt(sc.updated_at),
            } for sc in items]

        # Categories
        if since_dt:
            items = Category.query.filter(Category.updated_at > since_dt).all()
        else:
            items = Category.query.all()
        if items:
            response['categories'] = [{
                'id': c.id, 'name': c.name, 'type': c.type,
                'updated_at': _format_dt(c.updated_at),
            } for c in items]

        # System settings
        if since_dt:
            items = SystemSetting.query.filter(SystemSetting.updated_at > since_dt).all()
        else:
            items = SystemSetting.query.all()
        if items:
            response['system_settings'] = [{
                'key': ss.key, 'value': ss.value, 'data_type': ss.data_type,
                'name': ss.name, 'description': ss.description,
                'updated_at': _format_dt(ss.updated_at),
            } for ss in items]

        return jsonify(response), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@sync_bp.route('/get-unsynced', methods=['GET'])
def get_unsynced_records():
    """Совместимость: отдаёт несинхронизированные measurements."""
    try:
        records = Measurement.query.filter_by(is_synced=0).limit(50).all()
        payload = [{
            "id": int(r.id), "sensor_id": int(r.sensor_id), "value": float(r.value),
            "type": str(r.data_type), "timestamp": r.timestamp.isoformat(),
        } for r in records]
        return jsonify(payload), 200
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@sync_bp.route('/confirm', methods=['POST'])
def confirm_sync_records():
    """Совместимость: подтверждает синхронизацию measurements по ID."""
    try:
        req_data = request.get_json() or {}
        record_ids = req_data.get('ids', [])
        if not record_ids:
            return jsonify({"status": "error", "message": "Массив 'ids' пуст"}), 400
        Measurement.query.filter(Measurement.id.in_(record_ids)).update(
            {Measurement.is_synced: 1}, synchronize_session=False
        )
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500
