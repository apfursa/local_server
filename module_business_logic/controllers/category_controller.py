from flask import Blueprint, jsonify, request
from module_data_layer.core.db_config import db
from module_data_layer.models.category import Category

category_bp = Blueprint('category', __name__)


@category_bp.route('/', methods=['GET'])
def get_categories():
    # Получаем тип (location или group) из параметров запроса
    cat_type = request.args.get('type')
    query = Category.query
    if cat_type:
        query = query.filter_by(type=cat_type)

    categories = query.all()
    return jsonify([cat.to_dict() for cat in categories])


@category_bp.route('/', methods=['POST'])
def add_category():
    data = request.json
    if not data or 'name' not in data or 'type' not in data:
        return jsonify({"error": "Данные неполные"}), 400

    new_cat = Category(name=data['name'], type=data['type'])
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201


@category_bp.route('/', methods=['DELETE'])
def delete_category():
    data = request.json
    if not data:
        return jsonify({"error": "Данные не переданы"}), 400

    # Проверяем, пришёл ли ID от фронтенда
    cat_id = data.get('id')

    if cat_id is not None:
        # Ищем категорию в базе по первичному ключу
        category = Category.query.get(cat_id)
        if not category:
            return jsonify({"error": "Категория не найдена"}), 404

        # Удаляем и сохраняем изменения
        db.session.delete(category)
        db.session.commit()
        return jsonify({"status": "success", "message": "Категория успешно удалена"}), 200

    return jsonify({"error": "Не передан ID для удаления"}), 400