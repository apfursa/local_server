import os
from flask import Flask
from config import Config

# База данных и миграции из слоя данных
from module_data_layer.core.db_config import db, migrate


def create_app():
    """Фабрика приложения, собранная по твоей реальной модульной структуре"""
    # Презентация: шаблоны и статика
    app = Flask(__name__,
                template_folder='module_presentation/web/templates',
                static_folder='module_presentation/web/static')

    app.config.from_object(Config)

    # Инициализация БД
    db.init_app(app)
    migrate.init_app(app, db)

    # ИМПОРТ КОНТРОЛЛЕРОВ СТРОГО ПО ТВОИМ ПАПКАМ:
    # 1. views_controller живет в презентации
    from module_presentation.controllers.views_controller import views_bp
    # 2. api_controller, settings_controller и alarm_controller живут в бизнес-логике
    from module_business_logic.controllers.api_controller import api_bp
    from module_business_logic.controllers.settings_controller import settings_bp
    from module_business_logic.controllers.alarm_controller import alarm_bp
    # 3. sync_controller живет в модуле синхронизации
    from module_sync.controllers.sync_controller import sync_bp
    from module_business_logic.controllers.category_controller import category_bp

    # Регистрация блупринтов с явным указанием их префиксов (URL-путей)
    app.register_blueprint(views_bp)  # Статика (/)
    app.register_blueprint(api_bp, url_prefix='/api')  # Главный REST API (/api/...)
    app.register_blueprint(settings_bp, url_prefix='/api/settings')  # Контроллер настроек (/settings/...)
    app.register_blueprint(sync_bp, url_prefix='/sync')  # Синхронизация (/sync/...)
    app.register_blueprint(alarm_bp, url_prefix='/api/alarm')
    app.register_blueprint(category_bp, url_prefix='/api/categories')

    # Подгружаем модели для работы миграций
    with app.app_context():
        import module_data_layer.models

    return app


app = create_app()


def setup_database(app):
    """Автоматическое создание таблиц при чистом старте"""
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI').replace('sqlite:///', '')
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            print("--- ВНИМАНИЕ: База данных не обнаружена. Создаю таблицы... ---")
            db.create_all()
            print("--- База данных успешно инициализирована! ---")
        else:
            print("--- База данных обнаружена, таблицы готовы. ---")


setup_database(app)

if __name__ == '__main__':
    # Фоновые процессы из их родных модулей
    from module_ingestion.background.mqtt import start_mqtt
    from module_sync.background.sync import start_sync

    start_mqtt(app)
    start_sync()

    print("Фоновые процессы запущены.")
    print("Сервер стартует на http://localhost:80")

    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)