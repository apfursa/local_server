"""
Контроллер для управления номером телефона администратора (GSM-оповещения).
Отвечает за отдачу HTML-страницы и REST API для чтения/записи номера в системных настройках.
"""

from flask import Blueprint, jsonify, request, render_template
from module_data_layer.core.db_config import db
from module_data_layer.models.system_setting import SystemSetting

# Инициализируем Blueprint
phone_bp = Blueprint('phone', __name__)


@phone_bp.route('/', methods=['GET'])
def phone_page():
    """Отдает HTML-страницу настройки номера телефона (доступна по /phone)."""
    return render_template('phone.html')


@phone_bp.route('/api', methods=['GET'])
def get_phone_setting():
    """Получение номера телефона (доступно по /phone/api)."""
    try:
        setting = db.session.query(SystemSetting).filter_by(key='admin_phone').first()
        if setting:
            return jsonify({"value": setting.value}), 200
        return jsonify({"value": ""}), 200
    except Exception as err:
        return jsonify({"status": "error", "message": f"Ошибка БД: {str(err)}"}), 500


@phone_bp.route('/api', methods=['POST'])
def save_phone_setting():
    """Сохранение или обновление номера телефона (доступно по /phone/api)."""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({"status": "error", "message": "Неверный формат данных"}), 400

        new_phone = data['value'].strip()

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
        return jsonify({"status": "error", "message": f"Ошибка при сохранении: {str(err)}"}), 500