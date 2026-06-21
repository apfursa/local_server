"""
Тест слоя представления (module_presentation).

Проверяет, что views_controller отдаёт статичные HTML-файлы БЕЗ Jinja2,
что главный экран содержит контейнер #ui-container и шаблоны разметки в
тегах <script type="text/template">, и что локальная копия jQuery и
index.js отдаются как статика.
"""

import os
import unittest
from flask import Flask, send_from_directory
from module_presentation.controllers.views_controller import views_bp


def make_app():
    # Находим корень модуля презентации
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    module_root = os.path.abspath(os.path.join(tests_dir, ".."))
    static_dir = os.path.abspath(os.path.join(module_root, "web", "static"))

    # Инициализируем тестовое приложение Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.root_path = module_root

    # Регистрируем наш блупринт страниц
    app.register_blueprint(views_bp)

    # Железобетонный перехват статики для тестов, чтобы обойти баги путей Windows во Flask
    @app.route('/static/js/<path:filename>')
    def serve_test_js(filename):
        return send_from_directory(os.path.join(static_dir, 'js'), filename)

    @app.route('/static/css/<path:filename>')
    def serve_test_css(filename):
        return send_from_directory(os.path.join(static_dir, 'css'), filename)

    return app


class ViewsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = make_app().test_client()

    def test_index_served_as_plain_html(self):
        """Проверка отдачи главной страницы и отсутствия Jinja2"""
        with self.client.get("/") as resp:
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.content_type)
            body = resp.data.decode("utf-8")

        # Динамический контейнер для рендеринга на стороне браузера
        self.assertIn('id="ui-container"', body)
        # Шаблоны разметки лежат в script type="text/template"
        self.assertIn('type="text/template"', body)
        # Маркеры самописного шаблонизатора [%переменная%]
        self.assertIn("[%", body)
        # Jinja2 не используется — никаких {{ }} в выдаче
        self.assertNotIn("{{", body)

    def test_settings_served_as_plain_html(self):
        """Проверка роута настроек с передачей ID датчика в пути"""
        with self.client.get("/settings/39") as resp:
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.content_type)

    def test_local_jquery_served(self):
        """Проверка доступности локального jQuery"""
        with self.client.get("/static/js/jquery.min.js") as resp:
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"jQuery", resp.data[:200])

    def test_index_js_served(self):
        """Проверка доступности основного скрипта логики UI"""
        with self.client.get("/static/js/index.js") as resp:
            self.assertEqual(resp.status_code, 200)

    def test_css_served(self):
        """Проверка доступности стилей оформления"""
        with self.client.get("/static/css/index.css") as resp:
            self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()