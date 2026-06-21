"""
Контроллер локальной синхронизации.
Предоставляет изолированные эндпоинты для выборки и подтверждения отправки данных в облако.
"""

from flask import Blueprint, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.measurement import Measurement

sync_bp = Blueprint('sync', __name__)


@sync_bp.route('/sync/get-unsynced', methods=['GET'])
def get_unsynced_records():
    """
    Выбирает из локальной БД пачку несинхронизированных замеров (лимит 50 штук за раз).
    Преобразует дату в строгий международный стандарт ISO 8601.
    """
    try:
        # Извлекаем первые 50 записей, где флаг равен 0
        records = Measurement.query.filter_by(is_synced=0).limit(50).all()

        payload = []
        for r in records:
            payload.append({
                "id": int(r.id),
                "sensor_id": int(r.sensor_id),
                "value": float(r.value),
                "type": str(r.data_type),
                "timestamp": r.timestamp.isoformat()  # Формат: "2026-06-13T12:42:00"
            })

        return jsonify(payload), 200
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@sync_bp.route('/sync/confirm', methods=['POST'])
def confirm_sync_records():
    """
    Принимает массив ID записей, которые удачно долетели до интернет-сервера,
    и массово переключает их флаг is_synced в состояние 1.
    """
    try:
        req_data = request.get_json() or {}
        record_ids = req_data.get('ids', [])

        if not record_ids:
            return jsonify({"status": "error", "message": "Массив 'ids' пуст или отсутствует"}), 400

        # Апдейтим строки в базе одним быстрым запросом
        Measurement.query.filter(Measurement.id.in_(record_ids)).update(
            {Measurement.is_synced: 1},
            synchronize_session=False
        )

        db.session.commit()
        return jsonify({"status": "success", "message": "Синхронизация подтверждена"}), 200
    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(err)}), 500