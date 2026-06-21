"""
Контроллер визуального слоя. Отдает статические HTML-страницы.
Серверный рендеринг (Jinja2) полностью отключен.
"""

import os
from flask import Blueprint, send_from_directory

# 1. Вычисляем железный абсолютный путь к папке, где физически лежит этот файл контроллера:
# D:\Moy_Server\module_presentation\controllers
_controllers_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Поднимаемся ровно на один уровень выше, в корень модуля презентации:
# D:\Moy_Server\module_presentation
_presentation_dir = os.path.dirname(_controllers_dir)

# 3. Формируем гарантированные абсолютные пути к шаблонам и статике.
# Решает проблему путей как при запуске тестов, так и при работе сервера
_template_dir = os.path.abspath(os.path.join(_presentation_dir, 'web', 'templates'))
_static_dir = os.path.abspath(os.path.join(_presentation_dir, 'web', 'static'))

views_bp = Blueprint(
    'views',
    __name__,
    template_folder=_template_dir,
    static_folder=_static_dir,
    static_url_path='/static'  # Явно перехватывает запросы к /static/...
)

def _render_static_html(filename):
    """Вспомогательная функция для безопасного поиска и отправки HTML-файлов."""
    # Используем заранее вычисленный и проверенный абсолютный путь к шаблонам
    return send_from_directory(_template_dir, filename)

@views_bp.route('/', methods=['GET'])
def index_page():
    """Главная страница мониторинга умного дома."""
    return _render_static_html('index.html')

@views_bp.route('/settings/<int:sensor_id>', methods=['GET'])
def settings_page(sensor_id):
    """
    Страница управления аварийными порогами для конкретного датчика.
    Принимает ID датчика прямо из пути URL-адреса.
    """
    return _render_static_html('settings.html')

@views_bp.route('/categories')
def show_categories():
    return _render_static_html('categories.html')