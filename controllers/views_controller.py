from flask import Blueprint, render_template

# Создаем Blueprint (называем его 'views')
views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    # Ищет файл в папочке web/templates/
    return render_template('index.html')

@views_bp.route('/settings/<int:sensor_id>')
def settings_page(sensor_id):
    """Теперь это просто маршрут к файлу. Проверка существования ID ложится на API."""
    return render_template('settings.html')