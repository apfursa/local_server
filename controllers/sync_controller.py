from flask import Blueprint, jsonify
from models.measurement import Measurement
from core.db_config import db

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/api/sync/get-unsynced')
def get_unsynced():
    """Выдает список замеров, которые еще не ушли в облако"""
    # Как и в Yii2: Measurement::find()->where(['is_synced' => 0])->all()
    tasks = Measurement.query.filter_by(is_synced=0).limit(50).all()
    
    result = []
    for t in tasks:
        result.append({
            'id': t.id,
            'sensor_id': t.sensor_id,
            'value': t.value,
            'timestamp': t.timestamp.isoformat()
        })
    return jsonify(result)