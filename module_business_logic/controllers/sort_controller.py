"""
Контроллер для управления порядком отображения датчиков (сортировка на главном экране).
Отвечает за отдачу HTML-страницы и REST API для перезаписи поля sort_order в базе данных.
"""

from flask import Blueprint, jsonify, request, render_template
from module_data_layer.core.db_config import db
from module_data_layer.models.setting import Setting

# Инициализируем Blueprint для модуля сортировки
sort_bp = Blueprint('sort', __name__)


@sort_bp.route('/', methods=['GET'])
def sort_page():
    """Отдает HTML-страницу сортировки датчиков (доступна по /sort)."""
    return render_template('sort.html')


@sort_bp.route('/save', methods=['POST'])
def save_sort_order():
    """Принимает упорядоченный список датчиков и сохраняет их индексы в поле sort_order."""
    try:
        req_data = request.get_json()
        if not isinstance(req_data, list):
            return jsonify({"status": "error", "message": "Ожидался массив данных"}), 400

        # В цикле обновляем порядок на основе индекса элемента в пришедшем массиве
        for index, item in enumerate(req_data):
            sensor_id = item.get('sensor_id')
            d_type = item.get('type')

            if sensor_id is None or not d_type:
                continue

            # Ищем существующую запись настроек для этой пары датчик + тип
            setting = db.session.query(Setting).filter_by(sensor_id=sensor_id, data_type=d_type).first()

            # Если записи в базе еще нет (датчик работал по дефолтам), создаем строку
            if not setting:
                setting = Setting(sensor_id=sensor_id, data_type=d_type)
                db.session.add(setting)

            # Присваиваем новый порядковый индекс (0, 1, 2...)
            setting.sort_order = index

        db.session.commit()
        return jsonify({"status": "success", "message": "Порядок датчиков успешно сохранен"}), 200

    except Exception as err:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Внутренняя ошибка сервера: {str(err)}"}), 500